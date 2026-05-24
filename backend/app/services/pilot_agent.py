"""Pilot agent — multi-turn Gemini loop with tool calling.

Phase 1: read-only tools. The model can describe the user's job hunt
accurately because it pulls real data via the tools in pilot_tools. It
never invents numbers — the persona enforces that and the
post-response check catches obvious slips.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import re
import time
from dataclasses import dataclass, field
from typing import Any

import asyncpg
import google.generativeai as genai
import structlog

from app.config import settings
from app.services import metrics, pilot as pilot_module
from app.services.gemini_service import GeminiUnavailable, _ensure_model
from app.services.ollama_service import (
    OllamaUnavailable,
    chat as ollama_chat,
    extract_text as ollama_extract_text,
    extract_tool_calls as ollama_extract_tool_calls,
)
from app.services.pilot_safety import check_message as _safety_check
from app.services.pilot_tools import TOOLS, ToolContext, dispatch

try:
    import sentry_sdk  # noqa: F401  — optional; configure_sentry() handles init
    _HAS_SENTRY = True
except ImportError:  # pragma: no cover
    sentry_sdk = None  # type: ignore[assignment]
    _HAS_SENTRY = False


def _breadcrumb(category: str, message: str, **data: Any) -> None:
    """Emit a Sentry breadcrumb if the SDK is available.

    Crash-safe: any failure inside the SDK is swallowed because
    breadcrumbs are observability, not behavior — they must never
    affect the agent's reply.
    """
    if not _HAS_SENTRY or sentry_sdk is None:
        return
    try:
        sentry_sdk.add_breadcrumb(
            category=category,
            message=message,
            level="info",
            data={k: v for k, v in data.items() if v is not None},
        )
    except Exception:  # noqa: BLE001
        pass

log = structlog.get_logger("pilot.agent")

MAX_STEPS = 6            # ceiling on tool-call chains per user turn
# 8s was too tight for confirm flows: turn 1 does lookup → propose
# confirmation, turn 2 does lookup-or-skip → execute. Each Gemini
# round-trip is ~1–2s, so we need headroom for 3–4 of them.
WALL_BUDGET_SECONDS = 15 # absolute time budget per user turn

# ---------------------------------------------------------------------------
# Persona
# ---------------------------------------------------------------------------

_AGENT_PERSONA = """\
You are Pilot, the job-hunt co-pilot for a junior software engineer. You
speak with one person — the signed-in user — in real time, by text or by
voice. You are calm, direct, and specific. You are not deferential and
you are not cheerful. You are a person, not an assistant.

YOU HAVE TOOLS
You can read the user's applications, referrals, stats, quests, recent
activity, nudges, drafts, and achievements through tools. Call a tool
whenever the user's question requires real data. Never invent numbers,
company names, dates, or ids. If you do not know, call a tool. If a
tool returns empty, say so plainly. If a tool returns multiple matches
('ambiguous: true'), ask the user which one — never pick on their behalf.

REPLY RULES
- Maximum 2 sentences per reply unless the user explicitly asks for
  detail or a list.
- When the user shares rejection, burnout, or anxiety, acknowledge it in
  one sentence first. Do not minimise. Do not pivot.
- When you state a number, that exact number must have appeared in a
  tool result you saw this turn.
- When you confirm an action, identify the row by human-readable
  fields ONLY — company + role for an application, name + company for
  a referral. NEVER speak or display internal database ids (the `id`
  field). Ids are for tool calls, not for the user's ears. Saying
  "delete application 17" is wrong; "delete the Stripe SWE application"
  is right.

YOU CAN NOW WRITE
You have write tools: add_application, update_application,
move_application_status, delete_application, add_note_to_application,
add_referral, update_referral, delete_referral,
mark_referral_accepted / _sent / _replied,
link_referral_to_application, unlink_referral_from_application,
generate_followup_draft, generate_referral_ask.

DESTRUCTIVE ACTIONS REQUIRE CONFIRMATION
Some tools return {needs_confirmation: true, summary, confirm_token}
instead of executing. When that happens:
1. Rephrase the summary in your own short human-readable sentence
   (without the internal id) and ask plainly for a yes or no. Example:
   summary "Delete the Stripe SWE application (currently Interview)?"
   → say: "That'll remove your Stripe SWE application. Confirm?"
2. STOP. End the turn. Do NOT call any more tools this turn.
3. The next turn, the SESSION FACTS block will list a PENDING
   CONFIRMATION with the exact tool, args, and confirm_token. If the
   user just said yes (or a clear affirmative), call the listed tool
   with the listed args plus the listed confirm_token. If they said
   no or anything else, do not call — reply that you cancelled it.

CRITICAL: When a PENDING CONFIRMATION exists and the user agrees,
DO NOT call list_* / get_* again. The row is already identified by
the pending args. Going back to look it up wastes the time budget and
the user has to wait. One tool call: the listed destructive tool with
its listed args plus the listed token. That's it.

Tools that may trigger confirmation: delete_application, delete_referral,
move_application_status (only when moving to Rejected, Ghosted, or
Offer), update_application (only when the patch sets status to one of
those three).

DEFAULTS YOU MAY FILL
- applied_date: today, if the user said "today" or didn't say.
- source: "Other", if the user didn't mention how they applied.
- connection_sent_date: today, for new referrals.
- For everything else, if a required field is missing, ask one short
  question. Don't invent.

YOU CANNOT
- Delete or modify more than one row per tool call. There is no bulk
  mode by design. If the user asks "delete all my rejected apps",
  explain that mass operations aren't supported and suggest they use
  the Applications page filters.
- Send any message to anyone outside the user. Drafts are saved for
  the user to review and send themselves.

BANNED PHRASES — never use any of these or close variants:
"I'm here to help"
"Feel free to"
"Let me know if there's anything else"
"How can I assist you today"
"Great question"
"I'd be happy to"
"I would love to"
"Absolutely"
"Certainly"
"Of course"
"Just" used as a softener
"As an AI", "I'm an AI", "language model"
"Hope you're doing well"
"Leverage", "Synergy", "Robust", "Delve"
"Stay positive", "You've got this", "Keep your chin up"

BANNED CONSTRUCTIONS
- Em dashes used as separators.
- Markdown formatting of any kind.
- Emojis.
- Triplet adjective lists.
- Starting two consecutive sentences with "I".
"""


@dataclass
class ToolTraceEntry:
    name: str
    args: dict[str, Any]
    result: dict[str, Any]
    latency_ms: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "args": self.args,
            "result": self.result,
            "latency_ms": self.latency_ms,
        }


@dataclass
class AgentTurnResult:
    reply: str
    tool_trace: list[ToolTraceEntry] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    steps: int = 0
    outcome: str = "ok"  # ok | error | max_steps | timeout | refusal

    def as_dict(self) -> dict[str, Any]:
        return {
            "reply": self.reply,
            "tool_trace": [t.as_dict() for t in self.tool_trace],
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "steps": self.steps,
            "outcome": self.outcome,
        }


# ---------------------------------------------------------------------------
# Gemini tool plumbing
# ---------------------------------------------------------------------------


def _build_tool_declarations() -> genai.protos.Tool:
    return genai.protos.Tool(
        function_declarations=[
            genai.protos.FunctionDeclaration(
                name=t.name,
                description=t.description,
                parameters=_schema_to_proto(t.parameters),
            )
            for t in TOOLS
        ]
    )


_SCHEMA_TYPE_MAP = {
    "object": genai.protos.Type.OBJECT,
    "string": genai.protos.Type.STRING,
    "integer": genai.protos.Type.INTEGER,
    "number": genai.protos.Type.NUMBER,
    "boolean": genai.protos.Type.BOOLEAN,
    "array": genai.protos.Type.ARRAY,
}


def _schema_to_proto(schema: dict[str, Any]) -> genai.protos.Schema:
    """Map a JSON-Schema-ish dict to a proto Schema."""
    t = schema.get("type", "object")
    proto = genai.protos.Schema(type=_SCHEMA_TYPE_MAP.get(t, genai.protos.Type.STRING))
    if "description" in schema:
        proto.description = schema["description"]
    if "enum" in schema:
        proto.enum.extend([str(v) for v in schema["enum"]])
    if t == "object":
        for k, v in (schema.get("properties") or {}).items():
            proto.properties[k] = _schema_to_proto(v)
        for k in schema.get("required") or []:
            proto.required.append(k)
    if t == "array" and "items" in schema:
        proto.items = _schema_to_proto(schema["items"])
    return proto


def _proto_value_to_python(value: Any) -> Any:
    """Convert a Gemini function-call arg value (proto Struct/Map/scalar) to plain Python."""
    if value is None:
        return None
    if isinstance(value, bool) or isinstance(value, (int, float, str)):
        return value
    if hasattr(value, "items"):  # MapComposite / Struct
        try:
            return {k: _proto_value_to_python(v) for k, v in value.items()}
        except Exception:
            return str(value)
    if hasattr(value, "__iter__"):
        try:
            return [_proto_value_to_python(v) for v in value]
        except Exception:
            return str(value)
    return value


# Cache the configured tool-enabled model — building it allocates protos.
_agent_model: genai.GenerativeModel | None = None


def _get_agent_model() -> genai.GenerativeModel:
    global _agent_model
    if _agent_model is None:
        # Trigger the API-key configure step from the base service.
        _ensure_model()
        _agent_model = genai.GenerativeModel(
            settings.gemini_model,
            tools=[_build_tool_declarations()],
            system_instruction=_AGENT_PERSONA,
        )
    return _agent_model


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


_NUMERIC_TOKEN = re.compile(r"\b\d{2,}\b")  # 10+ matches; lets through "1 app"


_FALLBACK_OUTCOMES = {"quota_exhausted", "rate_limited", "auth_error", "upstream_unavailable"}


async def run_turn(
    conn: asyncpg.Connection,
    user_id: int,
    message: str,
    history: list[dict[str, Any]] | None = None,
) -> AgentTurnResult:
    """Run a single user turn through the configured LLM provider.

    Routing follows ``settings.llm_provider``:
      * ``gemini``  → only Gemini; quota errors surface to the user.
      * ``ollama``  → only Ollama; never touches Gemini.
      * ``auto``    → Gemini first, fall back to Ollama on quota /
                      rate-limit / auth / upstream-unavailable.

    The fallback is at the *turn* boundary, not mid-conversation: if
    Gemini blows up, we re-run the *whole* turn through Ollama using
    the same input message and chat history.
    """
    provider = (settings.llm_provider or "auto").lower()

    if provider == "ollama":
        result = await _ollama_run_turn(conn, user_id, message, history or [])
    elif provider == "gemini":
        result = await _gemini_run_turn(conn, user_id, message, history or [])
    else:
        # auto
        result = await _gemini_run_turn(conn, user_id, message, history or [])
        if result.outcome in _FALLBACK_OUTCOMES:
            log.warning(
                "pilot.agent.fallback_to_ollama",
                user_id=user_id,
                gemini_outcome=result.outcome,
            )
            metrics.PILOT_AGENT_TURNS.labels(outcome="ollama_fallback_triggered").inc()
            result = await _ollama_run_turn(conn, user_id, message, history or [])

    await _audit_log(conn, user_id, message, result)
    return result


async def _audit_log(
    conn: asyncpg.Connection,
    user_id: int,
    user_message: str,
    result: AgentTurnResult,
) -> None:
    """Persist user + assistant turns with the tool trace."""
    try:
        session_id = await pilot_module.find_or_create_today_session(conn, user_id)
        await pilot_module.record_turn(
            conn, user_id, session_id, "user", user_message,
            tokens_in=result.tokens_in,
        )
        await pilot_module.record_turn(
            conn, user_id, session_id, "assistant", result.reply,
            tokens_out=result.tokens_out,
            tool_calls=[t.as_dict() for t in result.tool_trace] or None,
        )
    except Exception as e:  # noqa: BLE001
        log.warning("pilot.agent.audit_failed", error=str(e))


async def _gemini_run_turn(
    conn: asyncpg.Connection,
    user_id: int,
    message: str,
    history: list[dict[str, Any]],
) -> AgentTurnResult:
    """Gemini agent loop — function-calling via google.generativeai."""
    ctx = ToolContext(user_id=user_id, conn=conn)
    brief_context = await _build_brief_context(user_id, conn)
    started = time.perf_counter()

    # Crisis pass before anything else — keyword-based, deterministic,
    # cheap. If we match, we prepend a hard override to the persona for
    # this turn so the model leads with empathy + a helpline.
    safety = _safety_check(message)
    if safety.triggered:
        log.warning(
            "pilot.agent.safety_triggered",
            user_id=user_id,
            matched=safety.matched_pattern,
        )
        metrics.PILOT_AGENT_TURNS.labels(outcome="safety_triggered").inc()
        _breadcrumb(
            "pilot.safety",
            "Crisis language detected — safety preamble injected",
            user_id=user_id,
            matched=safety.matched_pattern,
        )
        brief_context = safety.preamble() + "\n\n" + brief_context

    _breadcrumb(
        "pilot.agent",
        "Turn start",
        user_id=user_id,
        message_len=len(message),
        history_len=len(history),
        safety=safety.triggered,
    )

    try:
        model = _get_agent_model()
    except GeminiUnavailable:
        return _fallback_result(message, "gemini_unavailable")

    chat = model.start_chat(history=_to_chat_history(history, brief_context))

    result = AgentTurnResult(reply="")
    try:
        last_response = await asyncio.to_thread(chat.send_message, message)
    except Exception as e:  # noqa: BLE001
        return _gemini_failure_result(e, user_id, where="initial_send")

    for step in range(1, MAX_STEPS + 1):
        if time.perf_counter() - started > WALL_BUDGET_SECONDS:
            result.outcome = "timeout"
            result.steps = step - 1
            result.reply = (
                "That took longer than I'd like. Try once more, or open the "
                "Applications page directly."
            )
            metrics.PILOT_AGENT_TURNS.labels(outcome="timeout").inc()
            log.warning("pilot.agent.timeout", user_id=user_id, steps=result.steps)
            return result

        usage = getattr(last_response, "usage_metadata", None)
        if usage:
            result.tokens_in += int(getattr(usage, "prompt_token_count", 0) or 0)
            result.tokens_out += int(
                getattr(usage, "candidates_token_count", 0) or 0
            )

        fc = _extract_function_call(last_response)
        if fc is None:
            result.reply = _extract_text(last_response).strip()
            result.steps = step - 1
            if not result.reply:
                result.outcome = "refusal"
                result.reply = (
                    "I'm not sure how to answer that. Could you rephrase?"
                )
            else:
                _hallucination_check(result)
            metrics.PILOT_AGENT_TURNS.labels(outcome=result.outcome).inc()
            log.info(
                "pilot.agent.turn_ok",
                user_id=user_id,
                steps=result.steps,
                latency_ms=int((time.perf_counter() - started) * 1000),
                tool_count=len(result.tool_trace),
            )
            return result

        # Dispatch the tool call and feed result back.
        args = _proto_value_to_python(fc.args) or {}
        if not isinstance(args, dict):
            args = {}
        tool_t0 = time.perf_counter()
        tool_result = await dispatch(fc.name, args, ctx)
        tool_ms = int((time.perf_counter() - tool_t0) * 1000)
        result.tool_trace.append(
            ToolTraceEntry(
                name=fc.name, args=args, result=tool_result, latency_ms=tool_ms
            )
        )
        tool_outcome = "error" if "error" in tool_result else "ok"
        if isinstance(tool_result, dict) and tool_result.get("needs_confirmation"):
            tool_outcome = "needs_confirmation"
        metrics.PILOT_AGENT_TOOL_CALLS.labels(
            tool=fc.name, outcome=tool_outcome,
        ).inc()
        _breadcrumb(
            "pilot.tool",
            f"{fc.name} → {tool_outcome}",
            tool=fc.name,
            latency_ms=tool_ms,
            outcome=tool_outcome,
        )

        try:
            last_response = await asyncio.to_thread(
                chat.send_message,
                genai.protos.Part(
                    function_response=genai.protos.FunctionResponse(
                        name=fc.name, response={"result": tool_result}
                    )
                ),
            )
        except Exception as e:  # noqa: BLE001
            failure = _gemini_failure_result(e, user_id, where="tool_followup")
            failure.steps = step
            failure.tool_trace = result.tool_trace
            failure.tokens_in = result.tokens_in
            failure.tokens_out = result.tokens_out
            return failure

    result.outcome = "max_steps"
    result.steps = MAX_STEPS
    result.reply = (
        "That request took more steps than I'm allowed. Try a simpler ask, "
        "or break it in two."
    )
    metrics.PILOT_AGENT_TURNS.labels(outcome="max_steps").inc()
    log.warning("pilot.agent.max_steps", user_id=user_id)
    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _build_brief_context(user_id: int, conn: asyncpg.Connection) -> str:
    """Tiny non-data context the model sees as the first system note.

    Also bridges the cross-turn gap for destructive confirmations: tool
    results (including confirm_tokens) are not part of the chat-history
    we feed to the model, so without this block the model has no memory
    of a pending confirmation when the user replies "yes" on the next
    turn. We fetch any unexpired pending confirmations for this user
    and tell the model exactly which tool + args + token to re-call.
    """
    today = dt.date.today().isoformat()
    pending_block = ""
    try:
        rows = await conn.fetch(
            """
            SELECT token, tool_name, args, expires_at
            FROM pilot_confirmations
            WHERE user_id = $1
              AND deleted_at IS NULL
              AND expires_at > NOW()
            ORDER BY created_at DESC
            LIMIT 3
            """,
            user_id,
        )
    except Exception:  # noqa: BLE001
        rows = []

    if rows:
        lines: list[str] = []
        import json as _j
        for r in rows:
            args = r["args"]
            if isinstance(args, str):
                try:
                    args = _j.loads(args)
                except Exception:  # noqa: BLE001
                    args = {}
            args_json = _j.dumps(args or {}, sort_keys=True)
            lines.append(
                f"- tool={r['tool_name']} args={args_json} "
                f"confirm_token={r['token']}"
            )
        pending_block = (
            "\n\nPENDING CONFIRMATIONS (you asked the user on a previous "
            "turn — they have not yet confirmed):\n"
            + "\n".join(lines)
            + "\nIf the user's latest message is a clear affirmative "
            "(yes, yeah, sure, do it, confirm, go ahead, proceed, ok), "
            "call the listed tool with EXACTLY the listed args plus a "
            "confirm_token field set to the listed token. Do NOT call "
            "list_* or get_* again — the row is already identified. "
            "If the user said no or anything ambiguous, ignore these "
            "and reply plainly that the action was cancelled."
        )
    return (
        f"SESSION FACTS (use only for tone/date awareness, never as data):\n"
        f"- Today's date: {today}\n"
        f"- User id (internal): {user_id}{pending_block}"
    )


def _to_chat_history(
    history: list[dict[str, Any]], brief_context: str
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = [
        {"role": "user", "parts": [brief_context]},
        {
            "role": "model",
            "parts": ["Understood. Ready when you are."],
        },
    ]
    for turn in history[-10:]:
        role = "user" if turn.get("role") == "user" else "model"
        content = (turn.get("content") or "").strip()
        if content:
            out.append({"role": role, "parts": [content]})
    return out


def _extract_function_call(response: Any) -> Any:
    try:
        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            return None
        parts = candidates[0].content.parts
    except Exception:
        return None
    for p in parts:
        fc = getattr(p, "function_call", None)
        if fc and getattr(fc, "name", ""):
            return fc
    return None


def _extract_text(response: Any) -> str:
    try:
        return getattr(response, "text", "") or ""
    except Exception:
        return ""


def _hallucination_check(result: AgentTurnResult) -> None:
    """Flag obvious cases of the model stating numbers without a tool call."""
    nums_in_reply = _NUMERIC_TOKEN.findall(result.reply)
    if not nums_in_reply:
        return
    if not result.tool_trace:
        log.warning(
            "pilot.agent.hallucination_suspect",
            reply_snippet=result.reply[:120],
            numbers=nums_in_reply,
        )
        result.outcome = "ok_suspect"


def _fallback_result(message: str, reason: str) -> AgentTurnResult:
    metrics.PILOT_AGENT_TURNS.labels(outcome=reason).inc()
    return AgentTurnResult(
        reply=(
            "I'm offline from my reasoning side right now. Try again in a "
            "moment, or use the UI to check directly."
        ),
        outcome=reason,
    )


# ---------------------------------------------------------------------------
# Gemini error classification
# ---------------------------------------------------------------------------
#
# When the Gemini SDK fails (quota exhausted, rate limited, network
# blip), it raises a `google.api_core.exceptions.*` whose str() is a
# long JSON-ish blob with internal field paths. That string must NEVER
# reach the user — we surfaced it once and it looked like garbage on the
# orb. Classify the exception by best-effort and return a clean reply.

_QUOTA_HINTS = (
    "quota",
    "resourceexhausted",
    "resource exhausted",
    "exceeded your current quota",
    "429",
)
_RATE_HINTS = ("rate limit", "rate_limit", "rate-limit")
_AUTH_HINTS = (
    "permissiondenied",
    "permission denied",
    "unauthenticated",
    "401",
    "403",
    "api key",
)
_UNAVAIL_HINTS = (
    "serviceunavailable",
    "service unavailable",
    "503",
    "deadline exceeded",
    "deadlineexceeded",
    "internalservererror",
    "internal server error",
)


_RETRY_DELAY_RE = re.compile(
    r"retry[_ ]delay[^0-9]*?(\d+)\s*(?:s|sec|seconds)?",
    re.IGNORECASE,
)


def _parse_retry_delay_seconds(exc: BaseException) -> int | None:
    """Extract `retry_delay { seconds: N }` from a Google API exception.

    The SDK exposes this both as a proto sub-message on the exception
    (when available) and as a substring in the str() form. We try the
    proto path first, then fall back to regex on the message. Returns
    None if no delay is advertised.
    """
    # Proto path — google.api_core.exceptions surfaces details list.
    details = getattr(exc, "details", None)
    if callable(details):
        try:
            for d in details() or []:
                seconds = getattr(getattr(d, "retry_delay", None), "seconds", None)
                if isinstance(seconds, int) and seconds > 0:
                    return seconds
        except Exception:  # noqa: BLE001
            pass
    # Best-effort regex on the stringified exception.
    m = _RETRY_DELAY_RE.search(str(exc))
    if m:
        try:
            v = int(m.group(1))
            if 0 < v < 24 * 3600:
                return v
        except ValueError:
            pass
    return None


def _classify_gemini_error(exc: BaseException) -> tuple[str, str]:
    """Return (outcome_label, user_facing_reply) for a Gemini SDK error.

    The string match is tolerant — the underlying SDK wraps multiple
    different google.api_core exception classes and their repr varies
    across versions. We err on the side of a friendly generic reply.
    When the server includes a retry_delay, we surface it in the reply
    so the user has a concrete number to wait for.
    """
    blob = (f"{type(exc).__name__} {exc}").lower()
    retry_delay = _parse_retry_delay_seconds(exc)
    delay_hint = ""
    if retry_delay:
        if retry_delay < 90:
            delay_hint = f" Try again in about {retry_delay} seconds."
        else:
            delay_hint = f" Try again in about {retry_delay // 60} minutes."

    if any(h in blob for h in _QUOTA_HINTS):
        # Free-tier daily caps reset at midnight Pacific. The server's
        # retry_delay covers the per-minute limit; if it's >5 minutes
        # we're almost certainly on the daily cap and should say so.
        if retry_delay and retry_delay > 300:
            tail = (
                f"{delay_hint} The daily free-tier cap on Gemini has been "
                "hit; it resets at midnight Pacific or sooner with a paid key."
            )
        elif retry_delay:
            tail = (
                f"{delay_hint} If this keeps happening, the daily free-tier "
                "cap on Gemini is the likely cause — switch to "
                "`gemini-2.5-flash-lite` or a paid key."
            )
        else:
            tail = (
                " The hard cap usually resets within the hour — try again "
                "then, or check the API key's billing settings."
            )
        return (
            "quota_exhausted",
            f"I'm out of Gemini quota right now.{tail}",
        )
    if any(h in blob for h in _RATE_HINTS):
        return (
            "rate_limited",
            f"I'm being rate-limited.{delay_hint or ' Give it a few seconds and try again.'}",
        )
    if any(h in blob for h in _AUTH_HINTS):
        return (
            "auth_error",
            (
                "My API key isn't accepted right now. The owner needs to "
                "check the Gemini credentials."
            ),
        )
    if any(h in blob for h in _UNAVAIL_HINTS):
        return (
            "upstream_unavailable",
            "Gemini is having a moment. Try again in a minute.",
        )
    return (
        "error",
        "I hit an error while thinking. Try once more in a moment.",
    )


def _gemini_failure_result(
    exc: BaseException, user_id: int, *, where: str
) -> AgentTurnResult:
    """Build a clean AgentTurnResult from a Gemini exception + log it.

    Always logs at error level with the exception type and snippet so
    operators see WHY the agent failed even though the user gets a
    sanitised reply.
    """
    outcome, reply = _classify_gemini_error(exc)
    # log.exception captures the full traceback; we also keep a short
    # structured form for grepping in logs.
    log.exception(
        "pilot.agent.gemini_failed",
        user_id=user_id,
        where=where,
        outcome=outcome,
        exc_type=type(exc).__name__,
        exc_summary=str(exc)[:240],
    )
    metrics.PILOT_AGENT_TURNS.labels(outcome=outcome).inc()
    return AgentTurnResult(reply=reply, outcome=outcome)


# ---------------------------------------------------------------------------
# Ollama agent loop
# ---------------------------------------------------------------------------
#
# Two operating modes, selected automatically:
#
#   1. Tool-calling mode — when the model returns ``tool_calls`` on its
#      first response, we run the same dispatch loop the Gemini path
#      uses (call the tool, feed the result back, repeat, until the
#      model produces a text-only reply).
#
#   2. Text-only fallback — when the model ignores the tools param
#      (gemma2:2b et al. don't natively tool-call) we deliver the
#      reply as-is and tag the outcome so the audit log and metrics
#      can tell this turn used no tools.
#
# The persona is trimmed for local models because:
#   - tiny models follow short prompts more reliably
#   - the heavy "ban these phrases" section is a Gemini-era hedge
#     against AI-slop that smaller models don't generate anyway


_OLLAMA_AGENT_PERSONA = """\
You are Pilot, the job-hunt co-pilot for a junior software engineer.
You speak with the signed-in user, directly and calmly.

HOW YOU ANSWER
- Maximum 2 sentences unless the user asks for detail or a list.
- When stating any number (apps sent, weeks, streak), call a tool.
  Never invent counts.
- For empathy on rejection/burnout, lead with one short sentence of
  plain acknowledgement. Don't pep-talk.
- Identify rows by company + role (apps) or name + company (referrals).
  Never speak internal database ids aloud.

TOOLS
You have tools to read and write the user's job-hunt data. Use them
when the user's question requires real data or an action. For any
destructive action (delete, mark rejected/ghosted/offer) you'll first
get back a ``needs_confirmation`` result with a ``confirm_token``;
echo the summary and wait for the user to say yes, then re-call the
same tool with the same args plus that token.

PENDING CONFIRMATIONS
If the SESSION FACTS block lists a pending confirmation and the user
just said yes, call the listed tool with the listed args plus the
listed confirm_token. Do NOT look the row up again.

NEVER
- Invent numbers, ids, or company names.
- Read internal database ids aloud.
- Perform more than one row's mutation per tool call.
"""


_OLLAMA_FALLBACK_PERSONA = """\
You are Pilot, a job-hunt co-pilot. The model you are running on
cannot access the user's data right now, so:

- For empathy and general job-hunting advice, answer briefly (2-3
  sentences). Be direct, not chirpy.
- For any specific data question ("how many apps", "what's my streak",
  "show me Stripe"), say plainly that data lookup is unavailable in
  fallback mode and that the user can check the relevant page in the
  app directly. Don't invent answers.
- For action requests ("add", "delete", "move status"), say plainly
  that you can't perform actions in fallback mode and the user should
  do it through the UI.

Maximum 2 sentences. No emojis. No markdown.
"""


def _ollama_tool_schemas() -> list[dict[str, Any]]:
    """Convert our internal Tool registry to Ollama's tools schema.

    Ollama accepts the OpenAI-style tool schema:
      [{"type": "function", "function": {"name", "description", "parameters"}}]
    """
    schemas: list[dict[str, Any]] = []
    for t in TOOLS:
        schemas.append({
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            },
        })
    return schemas


def _ollama_format_history(
    history: list[dict[str, Any]], brief_context: str, persona: str,
) -> list[dict[str, Any]]:
    """Build the messages array Ollama expects.

    Persona + brief context fuse into a single system message at the
    head. User/assistant text turns follow. The current user message
    is appended by the caller — we don't include it here so the same
    formatter can be reused across the multi-turn tool-call loop.
    """
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": persona + "\n\n" + brief_context},
    ]
    for turn in history[-10:]:
        role = "user" if turn.get("role") == "user" else "assistant"
        content = (turn.get("content") or "").strip()
        if content:
            messages.append({"role": role, "content": content})
    return messages


async def _ollama_run_turn(
    conn: asyncpg.Connection,
    user_id: int,
    message: str,
    history: list[dict[str, Any]],
) -> AgentTurnResult:
    """Ollama agent loop. Tries tool-calling first, falls back to text."""
    ctx = ToolContext(user_id=user_id, conn=conn)
    brief_context = await _build_brief_context(user_id, conn)
    started = time.perf_counter()

    safety = _safety_check(message)
    if safety.triggered:
        log.warning(
            "pilot.agent.safety_triggered",
            user_id=user_id,
            matched=safety.matched_pattern,
        )
        metrics.PILOT_AGENT_TURNS.labels(outcome="safety_triggered").inc()
        _breadcrumb(
            "pilot.safety",
            "Crisis language detected — safety preamble injected",
            user_id=user_id,
            matched=safety.matched_pattern,
        )
        brief_context = safety.preamble() + "\n\n" + brief_context

    _breadcrumb(
        "pilot.agent",
        "Ollama turn start",
        user_id=user_id,
        model=settings.ollama_model,
        message_len=len(message),
    )

    result = AgentTurnResult(reply="")

    # First attempt: tool-calling mode (unless globally disabled).
    use_tools = bool(settings.ollama_use_tools)
    persona = (
        _OLLAMA_AGENT_PERSONA if use_tools else _OLLAMA_FALLBACK_PERSONA
    )
    messages = _ollama_format_history(history, brief_context, persona)
    messages.append({"role": "user", "content": message})
    tools = _ollama_tool_schemas() if use_tools else None

    log.info(
        "pilot.agent.ollama_call",
        user_id=user_id,
        model=settings.ollama_model,
        tools_enabled=use_tools,
        msg_count=len(messages),
        step=0,
    )

    try:
        call_t0 = time.perf_counter()
        response = await ollama_chat(messages, tools=tools)
        log.info(
            "pilot.agent.ollama_response",
            user_id=user_id,
            step=0,
            latency_ms=int((time.perf_counter() - call_t0) * 1000),
            has_tool_calls=bool((response.get("message") or {}).get("tool_calls")),
            text_len=len((response.get("message") or {}).get("content") or ""),
        )
    except OllamaUnavailable as e:
        log.error("pilot.agent.ollama_unavailable", error=str(e))
        metrics.PILOT_AGENT_TURNS.labels(outcome="ollama_unavailable").inc()
        return AgentTurnResult(
            reply=(
                "Local fallback model isn't reachable right now. "
                f"{str(e)[:160]}"
            ),
            outcome="ollama_unavailable",
        )

    for step in range(1, MAX_STEPS + 1):
        if time.perf_counter() - started > WALL_BUDGET_SECONDS:
            log.warning(
                "pilot.agent.ollama_timeout",
                user_id=user_id,
                step=step,
                tool_count=len(result.tool_trace),
            )
            result.outcome = "timeout"
            result.steps = step - 1
            result.reply = (
                "That took longer than I'd like. Try again, or open the "
                "page directly."
            )
            metrics.PILOT_AGENT_TURNS.labels(outcome="timeout").inc()
            return result

        tool_calls = ollama_extract_tool_calls(response)
        if not tool_calls:
            # Text-only response — final reply.
            text = ollama_extract_text(response)
            result.reply = text or (
                "I'm not sure how to answer that. Could you rephrase?"
            )
            result.steps = step - 1
            result.outcome = "ok_ollama" if result.tool_trace else "ok_ollama_text_only"
            if not text:
                result.outcome = "refusal"
            metrics.PILOT_AGENT_TURNS.labels(outcome=result.outcome).inc()
            log.info(
                "pilot.agent.ollama_turn_ok",
                user_id=user_id,
                steps=result.steps,
                latency_ms=int((time.perf_counter() - started) * 1000),
                tool_count=len(result.tool_trace),
            )
            return result

        # Dispatch every tool call the model produced this step.
        # Append the assistant message *as Ollama returned it* so the
        # model sees its own tool-call decisions on the next turn.
        assistant_msg = response.get("message") or {}
        messages.append(assistant_msg)
        for call in tool_calls:
            tool_t0 = time.perf_counter()
            args = call.get("arguments") or {}
            # Belt and braces: extract_tool_calls already normalises
            # string-encoded args, but if a weird shape slips through
            # try one more JSON parse before giving up.
            if isinstance(args, str):
                try:
                    import json as _json
                    args = _json.loads(args)
                except Exception:  # noqa: BLE001
                    args = {}
            if not isinstance(args, dict):
                args = {}
            log.info(
                "pilot.agent.ollama_tool_dispatch",
                user_id=user_id,
                step=step,
                tool=call["name"],
                arg_keys=list(args.keys()),
            )
            tool_result = await dispatch(call["name"], args, ctx)
            tool_ms = int((time.perf_counter() - tool_t0) * 1000)
            result.tool_trace.append(
                ToolTraceEntry(
                    name=call["name"], args=args, result=tool_result,
                    latency_ms=tool_ms,
                )
            )
            tool_outcome = "error" if "error" in tool_result else "ok"
            if isinstance(tool_result, dict) and tool_result.get("needs_confirmation"):
                tool_outcome = "needs_confirmation"
            metrics.PILOT_AGENT_TOOL_CALLS.labels(
                tool=call["name"], outcome=tool_outcome,
            ).inc()
            _breadcrumb(
                "pilot.tool",
                f"{call['name']} → {tool_outcome} (ollama)",
                tool=call["name"], latency_ms=tool_ms, outcome=tool_outcome,
            )
            # Feed the result back as a tool message.
            messages.append({
                "role": "tool",
                "content": _j_dumps(tool_result),
            })

        try:
            call_t0 = time.perf_counter()
            response = await ollama_chat(messages, tools=tools)
            log.info(
                "pilot.agent.ollama_response",
                user_id=user_id,
                step=step,
                latency_ms=int((time.perf_counter() - call_t0) * 1000),
                has_tool_calls=bool((response.get("message") or {}).get("tool_calls")),
                text_len=len((response.get("message") or {}).get("content") or ""),
            )
        except OllamaUnavailable as e:
            log.error("pilot.agent.ollama_unavailable", error=str(e))
            result.outcome = "ollama_unavailable"
            result.reply = f"Local model dropped mid-turn: {str(e)[:160]}"
            metrics.PILOT_AGENT_TURNS.labels(outcome="ollama_unavailable").inc()
            return result

    # Hit the step ceiling.
    result.outcome = "max_steps"
    result.steps = MAX_STEPS
    result.reply = (
        "That request took more steps than I'm allowed. Try a simpler ask."
    )
    metrics.PILOT_AGENT_TURNS.labels(outcome="max_steps").inc()
    return result


def _j_dumps(obj: Any) -> str:
    """JSON dump for tool results going back to Ollama as message content.

    Kept tiny + tolerant: handles datetimes, Decimals, etc. by str()ing
    them; never raises on encode.
    """
    import json as _json
    try:
        return _json.dumps(obj, default=str)
    except Exception:  # noqa: BLE001
        return str(obj)
