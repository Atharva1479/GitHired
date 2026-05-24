"""Crisis-language detection for the voice agent.

The job-hunt context routinely surfaces rejection, burnout, and anxiety
— Pilot acknowledges those plainly per the persona. But when the user
crosses into self-harm / suicidal ideation, the agent must step out of
advisor mode and hand off to a real resource. We do this with a small
keyword pass at the start of every turn, not via the LLM, so the
behavior is deterministic and auditable.

This module is intentionally narrow:
- Detects explicit crisis language (suicidal ideation, self-harm intent)
- Returns a structured outcome the agent layer injects as a hard rule
  prepended to the persona for that turn ONLY
- Never tries to diagnose; only escalates to human resources
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Compiled at import time. Word-boundary anchored so common false
# friends ("kill it on the interview") don't match.
_CRISIS_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pat, re.IGNORECASE)
    for pat in (
        r"\b(kill|killing|harm|hurt|end)\s+(my|me)self\b",
        r"\bsuicid(?:e|al|ality)\b",
        r"\btake\s+my\s+(own\s+)?life\b",
        r"\bend\s+(it\s+all|my\s+life)\b",
        r"\b(don'?t|do\s+not)\s+want\s+to\s+(live|be\s+alive|exist|be\s+here)\b",
        r"\bi\s+want\s+to\s+die\b",
        r"\bnothing\s+(left\s+)?to\s+live\s+for\b",
        r"\bself\s*[- ]?harm\b",
        r"\bcut(ting)?\s+myself\b",
    )
)

# Crisis-hotline numbers vary by country. We surface a generic global
# resource and the user can find their own. This is deliberately not
# country-detection magic — getting that wrong is worse than generic.
_SAFETY_PREAMBLE = (
    "CRISIS OVERRIDE — the user's most recent message contains language "
    "suggesting suicidal ideation or self-harm. This OVERRIDES everything "
    "else in your persona for this single reply.\n"
    "\n"
    "Required behavior, in this order:\n"
    "1. Open with one short sentence that acknowledges their pain without "
    "minimising it. Do NOT mention the job hunt. Do NOT suggest "
    "productivity activities.\n"
    "2. State plainly that you're a job-tracking tool and not equipped to "
    "help with this, and that a trained human is.\n"
    "3. Point them to a real resource. Use exactly: \"Please reach out to "
    "a crisis line right now — in the US, 988. Elsewhere, search "
    "'findahelpline.com' for one near you.\"\n"
    "4. Ask them, gently, if there is someone in their life they can "
    "tell right now.\n"
    "\n"
    "Do not call any tools this turn. Do not propose tasks. Do not "
    "default-cheer them up. Keep the whole reply under 4 sentences."
)


@dataclass(frozen=True)
class SafetyDecision:
    """Outcome of the crisis check for one user message."""

    triggered: bool
    matched_pattern: str | None = None

    def preamble(self) -> str:
        return _SAFETY_PREAMBLE if self.triggered else ""


def check_message(message: str) -> SafetyDecision:
    """Return a SafetyDecision for the given user message.

    Pure function — no I/O, no LLM call. Called once per user turn.
    """
    if not message:
        return SafetyDecision(triggered=False)
    for pat in _CRISIS_PATTERNS:
        m = pat.search(message)
        if m:
            return SafetyDecision(triggered=True, matched_pattern=m.group(0))
    return SafetyDecision(triggered=False)
