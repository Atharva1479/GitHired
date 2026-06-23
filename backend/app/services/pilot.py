"""Pilot — voice/chat AI co-pilot.

Orchestrates context gathering, Gemini chat generation, and turn persistence.
Tool execution (add app, move status) is intentionally deferred to a later
iteration — this MVP provides stats-aware conversational chat.
"""
from __future__ import annotations

import asyncio
import datetime as dt
from dataclasses import dataclass

import asyncpg
import google.generativeai as genai
import structlog

from app.config import settings
from app.services import metrics
from app.services.gemini_service import (
    GeminiUnavailable,
    _ensure_model,  # reuse the configured model singleton
    _estimate_cost_usd,
)
from app.services.ollama_service import OllamaUnavailable
from app.services.ollama_service import chat as ollama_chat

log = structlog.get_logger("pilot")


# ---------------------------------------------------------------------------
# Context gathering
# ---------------------------------------------------------------------------


@dataclass
class PilotContext:
    first_name: str
    today: str
    streak: int
    level: int
    xp_today_into_level: int
    applications_total: int
    applications_this_week: int
    in_progress: int
    offers: int
    referrals_total: int
    daily_quests: list[dict]
    recent_status_moves: list[str]

    def as_brief(self) -> str:
        q_text = (
            "; ".join(
                f"{q['title']} ({q['progress']}/{q['target']})"
                for q in self.daily_quests
                if not q.get("completed")
            )
            or "all done for today"
        )
        return (
            f"User: {self.first_name}. Date: {self.today}. "
            f"Streak: {self.streak} day(s). Level: {self.level}. "
            f"Applications total/this-week/in-progress/offers: "
            f"{self.applications_total}/{self.applications_this_week}/"
            f"{self.in_progress}/{self.offers}. "
            f"Referrals: {self.referrals_total}. "
            f"Today's quests: {q_text}. "
            f"Recent status moves: "
            f"{', '.join(self.recent_status_moves) or 'none'}."
        )


async def build_context(
    conn: asyncpg.Connection, user_id: int
) -> PilotContext:
    today = dt.date.today()
    user_row = await conn.fetchrow(
        "SELECT display_name FROM users WHERE id = $1", user_id,
    )
    name = (user_row["display_name"] or "there") if user_row else "there"
    first_name = name.split(" ")[0]

    apps_row = await conn.fetchrow(
        """
        SELECT
          COUNT(*) AS total,
          COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '7 days') AS this_week,
          COUNT(*) FILTER (WHERE status IN ('Applied','Screening','Interview')) AS in_progress,
          COUNT(*) FILTER (WHERE status = 'Offer') AS offers
        FROM applications WHERE user_id = $1 AND deleted_at IS NULL
        """,
        user_id,
    )
    ref_total = await conn.fetchval(
        "SELECT COUNT(*) FROM referral_contacts "
        "WHERE user_id = $1 AND deleted_at IS NULL",
        user_id,
    ) or 0

    prog_row = await conn.fetchrow(
        "SELECT current_xp, current_level, current_streak "
        "FROM user_progress WHERE user_id = $1 AND deleted_at IS NULL",
        user_id,
    )
    streak = int(prog_row["current_streak"]) if prog_row else 0
    level = int(prog_row["current_level"]) if prog_row else 1
    xp = int(prog_row["current_xp"]) if prog_row else 0

    from app.services.gamify import xp_to_next_level  # avoid circular

    into, _ = xp_to_next_level(xp)

    quest_rows = await conn.fetch(
        "SELECT code, target, progress, completed_at FROM quests "
        "WHERE user_id = $1 AND deleted_at IS NULL "
        "AND period = 'daily' AND expires_at > NOW() "
        "ORDER BY code",
        user_id,
    )
    from app.services.gamify import QUESTS

    daily_quests = [
        {
            "code": q["code"],
            "title": QUESTS[q["code"]].title if q["code"] in QUESTS else q["code"],
            "target": q["target"],
            "progress": q["progress"],
            "completed": q["completed_at"] is not None,
        }
        for q in quest_rows
    ]

    moves_rows = await conn.fetch(
        """
        SELECT payload FROM events
        WHERE user_id = $1 AND deleted_at IS NULL
          AND event_type = 'application.status_changed'
          AND occurred_at >= NOW() - INTERVAL '7 days'
        ORDER BY occurred_at DESC LIMIT 5
        """,
        user_id,
    )
    import json as _json
    recent: list[str] = []
    for r in moves_rows:
        p = r["payload"]
        if isinstance(p, str):
            p = _json.loads(p)
        if p:
            recent.append(f"app {p.get('application_id')} {p.get('from')}→{p.get('to')}")

    return PilotContext(
        first_name=first_name,
        today=today.isoformat(),
        streak=streak,
        level=level,
        xp_today_into_level=into,
        applications_total=int(apps_row["total"]) if apps_row else 0,
        applications_this_week=int(apps_row["this_week"]) if apps_row else 0,
        in_progress=int(apps_row["in_progress"]) if apps_row else 0,
        offers=int(apps_row["offers"]) if apps_row else 0,
        referrals_total=int(ref_total),
        daily_quests=daily_quests,
        recent_status_moves=recent,
    )


# ---------------------------------------------------------------------------
# Persona + prompts
# ---------------------------------------------------------------------------


_PERSONA = """\
You are Pilot, the job-hunt co-pilot for a junior software engineer. You
talk to one person — the user — in real time, in text or by voice.

WHO YOU ARE
A trusted friend who happens to know hiring well. Calm under pressure.
Direct. Specific. You don't sell hope, you give signal.

VOICE
Text-message register, not memo register. Sentences are short. You sound
like a person, not a chatbot. You never refer to yourself as an AI,
assistant, model, or "language model". You are Pilot.

LANGUAGE
Always respond in English only, regardless of the language the user writes or speaks in. If the user addresses you in another language, reply in English without comment.

HARD RULES
- Maximum 2 sentences per reply, unless the user explicitly asks for detail.
- When the user mentions rejection, burnout, exhaustion, anxiety, or
  doubt: lead with one sentence of plain acknowledgement before anything
  else. Do not minimise. Do not pivot to "let's focus on the positive".
- Never invent numbers or facts. Only state numbers the context block
  gives you. If you don't know, say so in one short sentence.
- If asked to do something you can't yet do (create applications, move
  statuses, send messages), say so plainly in one sentence and tell them
  exactly where in the UI to do it.

BANNED PHRASES — never use any of these or close variants:
"I'm here to help"
"Feel free to"
"Let me know if there's anything else"
"How can I assist you today"
"Great question"
"I'd be happy to", "I would love to"
"Absolutely", "Certainly", "Of course"
"Just" used as a softener
"As an AI", "I'm an AI", "language model"
"Hope you're doing well", "Hope this helps"
"Leverage", "Synergy", "Robust", "Delve", "Navigate the job market"
"Keep your chin up", "Stay positive", "Don't give up"
"You've got this", "You're doing amazing"

BANNED CONSTRUCTIONS
- Em dashes used as separators. Use periods.
- Bulleted or numbered lists, unless the user explicitly asks for a list.
- Markdown of any kind. No bold, no italics, no headers, no code fences.
- Emojis.
- Triplet adjective lists.
- Starting two consecutive sentences with "I".

WHAT GOOD LOOKS LIKE
USER: how am i doing this week?
GOOD: You've sent 7 applications and two are at phone screen. Want me to
pull up the ones still waiting?

USER: i got rejected from anthropic
GOOD: That stings. Anthropic is a hard one. The pipeline isn't a
referendum on you — want to redirect the energy into the next two apps?
"""


def _build_chat_prompt(
    ctx: PilotContext, message: str, history: list[dict]
) -> str:
    transcript_lines: list[str] = []
    for turn in history[-8:]:
        role = "USER" if turn.get("role") == "user" else "PILOT"
        content = (turn.get("content") or "").strip()
        if content:
            transcript_lines.append(f"{role}: {content}")
    transcript_lines.append(f"USER: {message.strip()}")
    transcript = "\n".join(transcript_lines)

    return f"""{_PERSONA}

CURRENT USER CONTEXT (do not recite back; use only when relevant)
{ctx.as_brief()}

CONVERSATION SO FAR
{transcript}

Reply as PILOT now. Two short sentences maximum. No preamble.

PILOT:"""


def _build_greeting_prompt(ctx: PilotContext) -> str:
    # Pick the most useful single hook for today.
    incomplete = [q for q in ctx.daily_quests if not q.get("completed")]
    if ctx.streak >= 3 and ctx.applications_this_week == 0:
        hook = "the streak is up but no applications this week yet"
    elif incomplete:
        q = incomplete[0]
        hook = (
            f"today's focus: '{q['title']}' (currently "
            f"{q.get('progress', 0)}/{q.get('target', 1)})"
        )
    elif ctx.applications_this_week >= 5:
        hook = f"strong week so far — {ctx.applications_this_week} applications in"
    else:
        hook = "first move of the day moves the needle"

    return f"""{_PERSONA}

CURRENT USER CONTEXT
First name: {ctx.first_name}
Streak: {ctx.streak} day(s)
Applications this week: {ctx.applications_this_week}
Hook for today: {hook}

TASK
Greet {ctx.first_name} in one or two short sentences. Anchor the second
sentence on the hook above so the greeting feels relevant, not generic.

CONSTRAINTS
- Open with their first name or skip a name entirely. Never "Hey there".
- If the streak is 0 or 1 day, do not mention it.
- If the streak is greater than or equal to 3, mention it once, plainly,
  without drama (no "amazing", "incredible", "on fire").
- Do not list multiple stats. Do not say "you've been doing great".
- One spoken-style greeting that would sound natural read aloud.

Write only the greeting.
"""


# ---------------------------------------------------------------------------
# Session/turn persistence
# ---------------------------------------------------------------------------


async def _find_or_create_today_session(
    conn: asyncpg.Connection, user_id: int
) -> int:
    row = await conn.fetchrow(
        "SELECT id FROM voice_sessions "
        "WHERE user_id = $1 AND deleted_at IS NULL "
        "AND started_at::date = CURRENT_DATE "
        "ORDER BY started_at DESC LIMIT 1",
        user_id,
    )
    if row:
        return int(row["id"])
    row = await conn.fetchrow(
        "INSERT INTO voice_sessions (user_id) VALUES ($1) RETURNING id",
        user_id,
    )
    assert row is not None
    return int(row["id"])


async def _record_turn(
    conn: asyncpg.Connection,
    user_id: int,
    session_id: int,
    role: str,
    content: str,
    *,
    tokens_in: int = 0,
    tokens_out: int = 0,
    cost_usd: float = 0.0,
    tool_calls: list[dict] | None = None,
) -> None:
    import json as _json
    tc_json = _json.dumps(tool_calls) if tool_calls else None
    await conn.execute(
        "INSERT INTO voice_turns (session_id, user_id, role, content, "
        "tokens_in, tokens_out, tool_calls) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)",
        session_id, user_id, role, content, tokens_in, tokens_out, tc_json,
    )
    await conn.execute(
        "UPDATE voice_sessions SET turn_count = turn_count + 1, "
        "cost_usd = cost_usd + $2 WHERE id = $1",
        session_id, cost_usd,
    )


async def find_or_create_today_session(
    conn: asyncpg.Connection, user_id: int
) -> int:
    """Public-ish: re-exposed for the agent so it can audit-log turns."""
    return await _find_or_create_today_session(conn, user_id)


async def record_turn(
    conn: asyncpg.Connection,
    user_id: int,
    session_id: int,
    role: str,
    content: str,
    *,
    tokens_in: int = 0,
    tokens_out: int = 0,
    cost_usd: float = 0.0,
    tool_calls: list[dict] | None = None,
) -> None:
    """Public wrapper around _record_turn for the agent."""
    await _record_turn(
        conn, user_id, session_id, role, content,
        tokens_in=tokens_in, tokens_out=tokens_out,
        cost_usd=cost_usd, tool_calls=tool_calls,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def _generate(prompt: str, *, max_output_tokens: int = 220) -> tuple[str, int, int]:
    model = _ensure_model()
    resp = await asyncio.to_thread(
        model.generate_content,
        prompt,
        generation_config={
            "max_output_tokens": max_output_tokens,
            "temperature": 0.7,
            "top_p": 0.9,
        },
    )
    text = (getattr(resp, "text", "") or "").strip()
    if not text:
        raise GeminiUnavailable("empty response")
    usage = getattr(resp, "usage_metadata", None)
    p = int(getattr(usage, "prompt_token_count", 0) or 0) if usage else 0
    o = int(getattr(usage, "candidates_token_count", 0) or 0) if usage else 0
    return text, p, o


async def greet(conn: asyncpg.Connection, user_id: int) -> str:
    ctx = await build_context(conn, user_id)
    prompt = _build_greeting_prompt(ctx)
    try:
        text, p, o = await _generate(prompt, max_output_tokens=120)
        cost = _estimate_cost_usd(p, o)
        metrics.record_gemini(settings.gemini_model, "ok", cost)
        metrics.PILOT_TURNS.labels(outcome="ok", kind="greeting").inc()
        return text
    except Exception as e:  # noqa: BLE001
        log.warning("pilot.greet_failed", error=str(e))

    # Ollama fallback — short greeting prompt, 30s cap
    try:
        resp = await asyncio.wait_for(
            ollama_chat(
                [{"role": "user", "content": prompt}],
                tools=None,
                temperature=0.7,
            ),
            timeout=30.0,
        )
        text = (resp.get("message", {}).get("content") or "").strip()
        if text:
            metrics.PILOT_TURNS.labels(outcome="ok_ollama", kind="greeting").inc()
            return text
    except (OllamaUnavailable, asyncio.TimeoutError, Exception) as e:  # noqa: BLE001
        log.warning("pilot.greet_ollama_failed", error=str(e))

    metrics.PILOT_TURNS.labels(outcome="error", kind="greeting").inc()
    return _fallback_greeting(ctx)


async def chat_turn(
    conn: asyncpg.Connection,
    user_id: int,
    message: str,
    history: list[dict],
) -> dict:
    """Returns {reply, tokens_in, tokens_out}."""
    ctx = await build_context(conn, user_id)
    prompt = _build_chat_prompt(ctx, message, history)
    try:
        text, p, o = await _generate(prompt, max_output_tokens=220)
        outcome = "ok"
    except Exception as e:  # noqa: BLE001
        log.warning("pilot.chat_failed", error=str(e))
        outcome = "error"
        text = (
            "I'm having trouble reaching my brain right now. Try again in a "
            "moment — your data is safe."
        )
        p = o = 0

    cost = _estimate_cost_usd(p, o)
    if outcome == "ok":
        metrics.record_gemini(settings.gemini_model, "ok", cost)
    metrics.PILOT_TURNS.labels(outcome=outcome, kind="chat").inc()

    session_id = await _find_or_create_today_session(conn, user_id)
    await _record_turn(
        conn, user_id, session_id, "user", message, tokens_in=p,
    )
    await _record_turn(
        conn, user_id, session_id, "assistant", text,
        tokens_out=o, cost_usd=cost,
    )
    return {"reply": text, "tokens_in": p, "tokens_out": o}


def _fallback_greeting(ctx: PilotContext) -> str:
    name = ctx.first_name
    if ctx.applications_this_week == 0 and ctx.streak < 3:
        return f"{name}. First application of the week moves the needle."
    if ctx.streak >= 7:
        return f"{name}. {ctx.streak} days in. Pick the next one and let's go."
    if ctx.applications_this_week >= 5:
        return f"Good pace this week, {name}. {ctx.applications_this_week} applications so far."
    return f"{name}. One real move today is enough."
