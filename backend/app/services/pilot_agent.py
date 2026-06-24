"""Pilot agent — thin shim that delegates to the LangGraph implementation.

This module now contains only the dataclasses and constants that other
modules import, plus ``_build_brief_context`` (imported by
``pilot_graph._build_system_prompt``) and a ``run_turn`` shim that
forwards every call to ``pilot_graph.run_turn``.

The full ReAct loop (Gemini + Ollama) lives in
``app.services.pilot_graph``.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any

import asyncpg

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
# Brief context builder (imported by pilot_graph._build_system_prompt)
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
