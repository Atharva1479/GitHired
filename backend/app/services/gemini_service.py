import asyncio

import google.generativeai as genai
import structlog

from app.config import settings
from app.services import metrics

log = structlog.get_logger("gemini")

# Approx Gemini 2.5 Flash pricing (USD per token). Update when Google's pricing moves.
_PRICE_INPUT_PER_TOKEN = 0.075 / 1_000_000
_PRICE_OUTPUT_PER_TOKEN = 0.30 / 1_000_000


def _estimate_cost_usd(prompt_tokens: int, output_tokens: int) -> float:
    return prompt_tokens * _PRICE_INPUT_PER_TOKEN + output_tokens * _PRICE_OUTPUT_PER_TOKEN

_SYSTEM = """\
You write short professional messages for a junior software engineer who is
job hunting. Your job is to produce a copy-paste-ready message body. Nothing
else.

REGISTER
Calm, specific, confident. Like a peer writing to another professional.
Never deferential. Never desperate. Never excited. Plain English, the way a
literate adult actually writes.

OUTPUT
Plain prose only. No markdown, no bullets, no headers, no subject line, no
explanations before or after the message, no quotes around the message.

BANNED PHRASES — never use any of these, or any close variant:
"I hope this email finds you well"
"I hope you're doing well"
"I am reaching out"
"Reaching out to"
"Just wanted to"   ("just" as a softener is banned anywhere)
"Touching base", "Circling back", "Looping in", "Following up to follow up"
"I would love to", "I'd love the opportunity"
"Kindly", "Please find attached"
"It is important to note", "It's worth mentioning"
"Furthermore", "Moreover", "In conclusion", "Additionally"
"Leverage", "Synergy", "Robust", "Tapestry", "Delve", "Navigate the market"
"In today's fast-paced world"
"Passionate about", "Dream role", "Dream company"
"Thank you for your time and consideration"
"I appreciate your time"

BANNED CONSTRUCTIONS
- Triplet adjective lists ("hardworking, dedicated, and passionate")
- Em dashes used as separators — write two sentences instead
- Hedging openers ("I know you're busy, but…")
- Generic gratitude in advance ("thanks in advance!")
- Self-deprecation ("apologies for the trouble")
- Sentences that begin with "I'm" three times in a row

STYLE
Short sentences. Concrete over abstract. Verbs over nouns. Specifics over
generalities. If you can cut a word, cut it.
"""


class GeminiUnavailable(Exception):
    """Raised when the model is unreachable, unconfigured, or quota'd."""


_configured = False
_model: genai.GenerativeModel | None = None


def _ensure_model() -> genai.GenerativeModel:
    global _configured, _model
    key = settings.gemini_api_key.get_secret_value()
    if not key or key in {"test-key", "dev", "your_key_here"}:
        raise GeminiUnavailable("no API key configured")
    if not _configured:
        genai.configure(api_key=key)
        _configured = True
    if _model is None:
        _model = genai.GenerativeModel(settings.gemini_model)
    return _model


def build_followup_email_prompt(
    company: str, role: str, days_elapsed: int, contact_name: str | None
) -> str:
    contact = contact_name or "Hiring Team"
    greeting = f"Hi {contact}," if contact_name else f"Hi {company} team,"
    return f"""{_SYSTEM}

TASK
Write a follow-up email after {days_elapsed} days without a reply on my
application to {company} for the {role} role.

WHAT GOES IN THE BODY
1. One sentence stating you applied {days_elapsed} days ago for the {role}
   role and are still interested. State it as a fact, not an apology.
2. One short sentence anchoring why this role specifically — a concrete
   detail about the team/product/problem, not generic enthusiasm.
3. A one-line ask: where the role stands, or whether they need anything
   else from your side.

HARD CONSTRAINTS
- Body length: 70 words maximum. Shorter is better.
- Two short paragraphs, max three sentences total.
- Opener exactly: "{greeting}"
- Closer exactly: "Best,\\n[Your name]" on its own two lines.
- No subject line.
- No bullets, no markdown.
- Do not thank them for their time. Do not apologise for following up.

Write only the email body.
"""


def build_referral_ask_prompt(
    name: str, company: str, target_role: str, mutual_context: str | None
) -> str:
    context_block = (
        f"How you know them: {mutual_context}\n"
        if mutual_context
        else "How you know them: not yet — this is a cold introduction.\n"
    )
    return f"""{_SYSTEM}

TASK
Write a LinkedIn DM to {name}, who works at {company}, asking if they'd
refer you for the {target_role} role at {company}.

CONTEXT
Target company: {company}
Target role: {target_role}
{context_block}
WHAT GOES IN THE MESSAGE
1. One short line anchoring on them specifically — their work, role, or the
   mutual context above. If there's no mutual context, anchor on a concrete
   reason for {company} (a product, team, or problem). Not flattery.
2. One short line on what you want: a referral for the {target_role} role.
3. One short line making it easy to say no, and offering to send your
   resume plus a three-line intro if they're game.

HARD CONSTRAINTS
- Length: 60 words maximum.
- Opener exactly: "Hi {name},"
- Closer: your initials on a new line. No "Best regards", no "Thanks!".
- LinkedIn DM register: conversational, no business-letter formality.
- Never reference being a "passionate" or "dedicated" engineer.
- Never write "I came across your profile" or any variant.

Write only the DM body.
"""


def build_referral_followup_prompt(
    name: str, company: str, days_since_msg: int
) -> str:
    return f"""{_SYSTEM}

TASK
Write a short LinkedIn nudge to {name} at {company}. It has been
{days_since_msg} days since you asked them for a referral.

TONE
A gentle bump from someone who respects their time. Do not restate the
original ask. Do not guilt them. Treat the silence as "they're busy" not
"they're ignoring you".

WHAT GOES IN THE MESSAGE
1. One line that surfaces the prior message without summarising it
   ("if this got buried", "in case it slipped past you").
2. One line giving them an easy way out — that you understand if the
   timing is off or it's not something they can help with.

HARD CONSTRAINTS
- Length: 30 words maximum.
- Opener exactly: "Hi {name},"
- Closer: your initials on a new line.
- Banned openers: "Just bumping", "Just checking in", "Following up to follow up".
- No subject line. No "thanks in advance".

Write only the DM body.
"""


def _fallback(draft_type: str, **kw: object) -> str:
    if draft_type == "followup_email":
        company = kw.get("company")
        role = kw.get("role")
        days = kw.get("days_elapsed")
        contact_name = kw.get("contact_name")
        greeting = (
            f"Hi {contact_name}," if contact_name else f"Hi {company} team,"
        )
        return (
            f"{greeting}\n\n"
            f"I applied for the {role} role {days} days ago and am still very "
            f"interested. If anything else is useful from my side or you can share "
            "where things stand, I'd appreciate the update.\n\n"
            "Best,\n[Your name]"
        )
    if draft_type == "referral_ask":
        name = kw.get("name")
        company = kw.get("company")
        target = kw.get("target_role")
        return (
            f"Hi {name},\n\n"
            f"I'm putting in for the {target} role at {company} this week. "
            "Would you be open to referring me? Happy to send my resume and a "
            "short intro. Totally fine to say no.\n\n"
            "[Your initials]"
        )
    if draft_type == "referral_followup":
        name = kw.get("name")
        return (
            f"Hi {name},\n\n"
            "Bumping the previous note in case it got buried. Completely fine "
            "if it's not a fit right now.\n\n"
            "[Your initials]"
        )
    return ""


async def generate(prompt: str, *, max_output_tokens: int = 400) -> tuple[str, int, int]:
    """Returns (text, prompt_tokens, output_tokens). Raises GeminiUnavailable."""
    try:
        model = _ensure_model()
        resp = await asyncio.to_thread(
            model.generate_content,
            prompt,
            generation_config={
                "max_output_tokens": max_output_tokens,
                "temperature": 0.75,
                "top_p": 0.9,
            },
        )
    except GeminiUnavailable:
        raise
    except Exception as e:  # noqa: BLE001
        log.warning("gemini.failure", error=str(e))
        outcome = "rate_limited" if "429" in str(e) or "quota" in str(e).lower() else "error"
        metrics.record_gemini(settings.gemini_model, outcome)
        raise GeminiUnavailable(str(e)) from e

    text = (getattr(resp, "text", "") or "").strip()
    if not text:
        metrics.record_gemini(settings.gemini_model, "error")
        raise GeminiUnavailable("empty response")
    usage = getattr(resp, "usage_metadata", None)
    p_tok = int(getattr(usage, "prompt_token_count", 0) or 0) if usage else 0
    o_tok = int(getattr(usage, "candidates_token_count", 0) or 0) if usage else 0
    metrics.record_gemini(
        settings.gemini_model, "ok", _estimate_cost_usd(p_tok, o_tok)
    )
    return text, p_tok, o_tok


async def generate_or_fallback(
    *, draft_type: str, prompt: str, **fb_kw: object
) -> tuple[str, str, int, int, bool]:
    """Returns (content, model_name, p_tok, o_tok, fallback_flag)."""
    try:
        text, pt, ot = await generate(prompt)
        return text, settings.gemini_model, pt, ot, False
    except GeminiUnavailable:
        metrics.record_gemini(settings.gemini_model, "fallback")
        return _fallback(draft_type, **fb_kw), "template", 0, 0, True
