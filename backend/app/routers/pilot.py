"""Pilot — voice/chat co-pilot endpoints."""
import asyncio
import json
from typing import Annotated, AsyncIterator

import asyncpg
import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

log = structlog.get_logger("pilot.router")

from app.config import settings
from app.database import pool
from app.deps import get_db, get_user_id
from app.services import pilot, pilot_graph
from app.services.security import limiter
from app.services.stt import SttUnavailable, transcribe
from app.services.tts import TtsUnavailable, synthesize

router = APIRouter()

# Expensive AI calls (agent, TTS, STT) share the tighter budget.
# Cheap reads (greeting, history) get a looser limit so normal usage
# can't consume the AI budget by accident.
_RATE = f"{settings.pilot_rate_limit_per_minute}/minute"
_READ_RATE = "60/minute"


class PilotTurn(BaseModel):
    role: str = Field(pattern=r"^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[PilotTurn] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    tokens_in: int
    tokens_out: int


class ToolTraceItem(BaseModel):
    name: str
    args: dict
    result: dict
    latency_ms: int


class AgentResponse(BaseModel):
    reply: str
    tool_trace: list[ToolTraceItem] = Field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    steps: int = 0
    outcome: str = "ok"


class TtsRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class HistoryTurn(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    tokens_in: int
    tokens_out: int
    tool_calls: list[dict] | None = None
    created_at: str


class HistoryResponse(BaseModel):
    turns: list[HistoryTurn]


def _ensure_enabled() -> None:
    if not settings.pilot_enabled:
        raise HTTPException(status_code=503, detail="Pilot is disabled")


@router.get("/greeting")
@limiter.limit(_READ_RATE)
async def greeting(
    request: Request,
    conn: Annotated[asyncpg.Connection, Depends(get_db)],
    user_id: Annotated[int, Depends(get_user_id)],
) -> dict[str, str]:
    _ensure_enabled()
    text = await pilot.greet(conn, user_id)
    return {"text": text}


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(_RATE)
async def chat(
    request: Request,
    body: ChatRequest,
    conn: Annotated[asyncpg.Connection, Depends(get_db)],
    user_id: Annotated[int, Depends(get_user_id)],
) -> ChatResponse:
    """Legacy: kept for back-compat with the M8 client; routes through the agent."""
    _ensure_enabled()
    result = await pilot_graph.run_turn(
        conn, user_id, body.message,
        [t.model_dump() for t in body.history],
    )
    return ChatResponse(
        reply=result.reply,
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
    )


@router.post("/agent", response_model=AgentResponse)
@limiter.limit(_RATE)
async def agent_turn(
    request: Request,
    body: ChatRequest,
    conn: Annotated[asyncpg.Connection, Depends(get_db)],
    user_id: Annotated[int, Depends(get_user_id)],
) -> AgentResponse:
    """Run a single user turn through the grounded agent loop.

    Returns the assistant reply plus the trace of any tools it called to
    answer. Phase 1: read-only tools.
    """
    _ensure_enabled()
    result = await pilot_graph.run_turn(
        conn, user_id, body.message,
        [t.model_dump() for t in body.history],
    )
    return AgentResponse(
        reply=result.reply,
        tool_trace=[ToolTraceItem(**t.as_dict()) for t in result.tool_trace],
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
        steps=result.steps,
        outcome=result.outcome,
    )


@router.post("/agent/stream")
@limiter.limit(_RATE)
async def agent_stream(
    request: Request,
    body: ChatRequest,
    user_id: Annotated[int, Depends(get_user_id)],
) -> StreamingResponse:
    """Stream the agent's reply as Server-Sent Events.

    The full agent loop still runs to completion server-side (tool calls
    are atomic and ordered, so streaming each step would be misleading).
    Once the final reply is ready, it is sliced into small word-group
    chunks and yielded at ~25 chunks/second, so the user sees the
    response materialise instead of waiting for the whole turn.

    Connection lifecycle: we deliberately do NOT use ``Depends(get_db)``
    here. FastAPI tears down request-scoped dependencies the moment the
    handler returns the ``StreamingResponse`` object — but the generator
    body runs after that, so the asyncpg connection would already be
    back in the pool by the time tools try to query. Acquire one inside
    the generator so it lives for the streaming lifetime instead.

    Event types:
      - ``trace``  → ``{type: "trace", trace: [...]}`` once, before deltas
      - ``delta``  → ``{type: "delta", text: "..."}`` repeatedly
      - ``done``   → ``{type: "done", outcome: "...", reply: "...",
                        tokens_in, tokens_out, steps}`` once, last
      - ``error``  → ``{type: "error", message: "..."}`` on failure
    """
    _ensure_enabled()

    history_payload = [t.model_dump() for t in body.history]
    message = body.message

    async def event_stream() -> AsyncIterator[bytes]:
        async with pool().acquire() as conn:
            try:
                result = await pilot_graph.run_turn(
                    conn, user_id, message, history_payload,
                )
            except Exception:  # noqa: BLE001
                # The agent layer already classifies known Gemini failures
                # and returns a clean AgentTurnResult — so anything reaching
                # here is a genuine bug or an asyncpg/network glitch. Log
                # the traceback, but never leak its repr to the client.
                log.exception(
                    "pilot.router.agent_stream_failed", user_id=user_id
                )
                yield _sse({
                    "type": "error",
                    "message": (
                        "Pilot ran into an unexpected error. The team has "
                        "been notified — try again in a moment."
                    ),
                })
                return

            yield _sse({
                "type": "trace",
                "trace": [
                    {
                        "name": t.name,
                        "args": t.args,
                        "result": t.result,
                        "latency_ms": t.latency_ms,
                    }
                    for t in result.tool_trace
                ],
            })

            # Slice the reply into ~3-word chunks, preserving spaces.
            reply = result.reply or ""
            words = reply.split(" ")
            i = 0
            while i < len(words):
                chunk = " ".join(words[i : i + 3])
                if i + 3 < len(words):
                    chunk += " "
                yield _sse({"type": "delta", "text": chunk})
                i += 3
                await asyncio.sleep(0.04)

            yield _sse({
                "type": "done",
                "reply": reply,
                "outcome": result.outcome,
                "tokens_in": result.tokens_in,
                "tokens_out": result.tokens_out,
                "steps": result.steps,
            })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-store",
            "X-Accel-Buffering": "no",
        },
    )


def _sse(payload: dict) -> bytes:
    return f"data: {json.dumps(payload)}\n\n".encode("utf-8")


@router.get("/history", response_model=HistoryResponse)
@limiter.limit(_READ_RATE)
async def history(
    request: Request,
    conn: Annotated[asyncpg.Connection, Depends(get_db)],
    user_id: Annotated[int, Depends(get_user_id)],
    limit: int = Query(default=50, ge=1, le=200),
) -> HistoryResponse:
    """Recent voice_turns for the signed-in user.

    Used by the /pilot/history inspector page so the user can audit
    what Pilot actually did on their behalf. Tool calls (including args
    + result + latency) are surfaced verbatim from voice_turns.tool_calls.
    """
    _ensure_enabled()
    capped = max(1, min(int(limit or 50), 200))
    rows = await conn.fetch(
        """
        SELECT id, session_id, role, content, tokens_in, tokens_out,
               tool_calls, created_at
        FROM voice_turns
        WHERE user_id = $1 AND deleted_at IS NULL
        ORDER BY created_at DESC
        LIMIT $2
        """,
        user_id, capped,
    )
    turns: list[HistoryTurn] = []
    for r in rows:
        tc = r["tool_calls"]
        if isinstance(tc, str):
            try:
                tc = json.loads(tc)
            except json.JSONDecodeError:
                tc = None
        turns.append(
            HistoryTurn(
                id=int(r["id"]),
                session_id=int(r["session_id"]),
                role=r["role"],
                content=r["content"],
                tokens_in=int(r["tokens_in"]),
                tokens_out=int(r["tokens_out"]),
                tool_calls=tc,
                created_at=r["created_at"].isoformat(),
            )
        )
    return HistoryResponse(turns=turns)


@router.post("/stt")
@limiter.limit(_RATE)
async def stt_endpoint(
    request: Request,
    user_id: Annotated[int, Depends(get_user_id)],
    audio: UploadFile = File(...),
) -> dict[str, str]:
    _ensure_enabled()
    body = await audio.read(2 * 1024 * 1024)  # 2MB cap for 30s of webm
    if not body:
        raise HTTPException(400, "empty audio")
    try:
        text = await transcribe(body, filename=audio.filename or "speech.webm")
    except SttUnavailable as e:
        log.warning("pilot.stt_unavailable", error=str(e))
        raise HTTPException(503, "Speech recognition temporarily unavailable") from e
    return {"text": text}


@router.post("/tts")
@limiter.limit(_RATE)
async def tts_endpoint(
    request: Request,
    body: TtsRequest,
    user_id: Annotated[int, Depends(get_user_id)],
) -> Response:
    _ensure_enabled()
    try:
        audio = await synthesize(body.text)
    except TtsUnavailable as e:
        log.warning("pilot.tts_unavailable", error=str(e))
        raise HTTPException(503, "Voice synthesis temporarily unavailable") from e
    return Response(
        content=audio,
        media_type="audio/mpeg",
        headers={"Cache-Control": "no-store"},
    )
