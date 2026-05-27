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

You are an elite career strategist. 97% of follow-up emails are deleted on sight because
they all say the same thing: "I applied X days ago and haven't heard back." Yours will not.

THE FUNDAMENTAL RULE: A follow-up email is not a status check. It is a second chance to
demonstrate value. If you don't add something — a thought, an insight, a proof point —
you are just adding noise to someone's inbox.

━━━━━━━━━━━━━━━━━━━━━━━━
CONTEXT
Company:       {company}
Role:          {role}
Days elapsed:  {days_elapsed}
━━━━━━━━━━━━━━━━━━━━━━━━

STRUCTURE — 3 sentences maximum, 70 words maximum:

SENTENCE 1 — THE HOOK (replaces the boring status opener)
Do NOT open with "I applied X days ago." That is the sentence every recruiter skips.
Instead, open with ONE of these approaches:
  A) A specific insight about {company}'s product, stack, or challenge that you've
     thought about since applying — and what you'd do about it.
  B) A concrete achievement or recent work that maps directly to the {role}'s core need.
  C) A brief statement that shows you understand what makes this role hard.

SENTENCE 2 — THE ANCHOR
Connect the hook back to your application. Confirm your interest is specific, not generic.
One sentence. No superlatives. No "I would be a great fit."

SENTENCE 3 — THE ASK (low friction)
Make it trivially easy for them to respond.
Examples: "A quick yes or no on whether the role is still moving would help me plan."
          "Happy to share [something specific] if that would help."
NOT: "Please let me know if there are any updates at your convenience."

━━━━━━━━━━━━━━━━━━━━━━━━
HARD CONSTRAINTS
- Opener exactly: "{greeting}"
- Closer exactly: "Best,\\n[Your name]"
- 70 words maximum. No exceptions. Every extra word weakens it.
- Zero apology for following up. You have done nothing wrong.
- Zero generic enthusiasm ("excited about this opportunity").
- Zero hedging ("I know you're busy").
- If you cannot add genuine value in sentence 1, write less — not more filler.

Write only the email body.
"""


def build_cover_letter_prompt(
    company: str,
    role: str,
    jd_text: str | None,
    resume_text: str | None,
    contact_name: str | None,
    tone: str = "professional",
) -> str:
    salutation = f"Dear {contact_name}," if contact_name else "Dear Hiring Team,"
    closer_name = (
        salutation.replace("Dear ", "").replace(",", "").strip()
    )

    jd_block = (
        f"\nJOB DESCRIPTION (read every line — mine it for specific technical requirements, "
        f"product challenges, and stack details):\n{jd_text[:2500].strip()}\n"
        if jd_text and jd_text.strip()
        else f"\nNo job description provided — infer requirements from the role title '{role}' "
        f"at a company called '{company}'. Make reasonable, specific assumptions.\n"
    )
    resume_block = (
        f"\nCANDIDATE'S FULL RESUME (every word is real — use specific details, "
        f"never invent or round numbers):\n{resume_text[:3500].strip()}\n"
        if resume_text and resume_text.strip()
        else (
            f"\nNo resume provided. Write a compelling letter using generic but credible "
            f"engineering achievements suitable for a {role} candidate.\n"
        )
    )

    tone_guide = {
        "professional": (
            "TONE: Confident, peer-to-peer. Imagine the best engineer at their previous "
            "company writing to a hiring manager they respect. No superlatives. "
            "No corporate filler. Every sentence earns its place."
        ),
        "concise": (
            "TONE: Maximum density. 210-240 words total. "
            "One precise sentence per idea. Treat every word as expensive. "
            "If a sentence can be cut without losing meaning, cut it."
        ),
        "enthusiastic": (
            "TONE: Warm and genuinely interested — but grounded in specifics, never generic. "
            "Show enthusiasm through concrete knowledge of the company's work, "
            "not through adjectives. No exclamation marks. No 'I would love to'."
        ),
    }.get(tone, "TONE: Confident, peer-to-peer professional.")

    return f"""{_SYSTEM}

You are a ghost-writer who has written cover letters that landed candidates at Google,
Stripe, Figma, and top YC companies. Your letters get read because the first sentence
is impossible to ignore. Recruiters forward them to hiring managers unprompted.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ROLE & COMPANY
Company: {company}
Role:    {role}
Opener:  {salutation}
{jd_block}{resume_block}
{tone_guide}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 1 — MINE BEFORE YOU WRITE (do this mentally before drafting)

From the resume, identify:
  (A) The single most impressive, quantified achievement — the number or outcome
      that makes even a skeptical reader pause. If the resume has metrics, use them
      exactly. If not, pick the most specific and impactful thing.
  (B) Two or three technical skills or tools that appear in BOTH the resume and JD —
      these are your relevance anchors.
  (C) One specific thing about {company} from the JD — a product detail, technical
      challenge, scale problem, or stated mission — that connects to (A).

The entire letter flows from these three findings. If you skip this step,
your letter will be generic, and generic letters are deleted.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 2 — WRITE USING THE STRUCTURE BELOW

PARAGRAPH 1 — THE ELECTRIC OPENER (2-3 sentences, 45-65 words)
────────────────────────────────────────────────────────────────
THE RULE: Open with PROOF, not desire. The first sentence must contain a specific
achievement or fact from the resume — not intent, not enthusiasm, not "I am applying."

The recruiter should read your first sentence and think:
"Wait — this person actually did that? Keep reading."

STRONG OPENER PATTERNS (use one of these as a template):
  • "[Achievement with metric] — that's the work I want to bring to the {role} role at {company}."
  • "The [specific challenge named in JD] is a problem I spent [time period] solving at [prev company]: [what you built/achieved]."
  • "At [company], I [specific achievement with outcome]. {company}'s focus on [specific detail from JD] is exactly where I want to apply that next."
  • "[Specific technology or system] at scale — [what you did] — is how I know I can contribute to [specific {company} product/challenge]."

Do NOT open with: "I", "My name is", "I am writing", "I am excited", "I would love",
any form of "I am applying", or any sentence that could be sent to a different company.

PARAGRAPH 2 — THE WHY-HERE EVIDENCE (3-4 sentences, 65-85 words)
────────────────────────────────────────────────────────────────
Prove you've done your research on {company} — not Wikipedia-level, but JD-level.
Name a specific technical challenge, product detail, or mission element from the JD.
Connect it to something concrete from your experience.
This paragraph must be IMPOSSIBLE to use at a different company.
Do not start with "I". Use your findings from Phase 1 (B) and (C).

PARAGRAPH 3 — THE DEPTH EVIDENCE (3-5 sentences, 75-100 words)
────────────────────────────────────────────────────────────────
Your two strongest achievements mapped directly to the JD's requirements.
Lead with outcomes and impact, not responsibilities.
Use named technologies, exact metrics, and concrete scale from the resume.
Every sentence answers "so what?" — what changed because you did this.
If the resume has numbers: use them verbatim. Never round up, never invent.

PARAGRAPH 4 — THE CLOSE (2-3 sentences, 30-50 words)
────────────────────────────────────────────────────────────────
State that you want to talk. Be direct — one clear ask.
One sentence on what you're looking for right now (the role, the company type, the problem).
Close with something that invites a response without begging for one.
Do NOT write "I look forward to hearing from you." That sentence is a reflex, not a close.

Closer:
Sincerely,
{closer_name}
[Your name]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WORD COUNT: 270-340 words (salutation and sign-off not included).

BANNED — never use any of these or any close variant:
"I am writing to express my interest / apply / inquire"
"I am excited about" / "excited to apply"
"I would love to" / "I'd love the opportunity"
"Passionate about" — prove it, don't name it
"Quick learner" / "fast learner" / "eager to learn"
"Hard worker" / "team player" / "results-driven" / "go-getter"
"I believe I would be a great fit"
"I look forward to hearing from you"
"Please find my resume attached" / "Please find attached"
"To whom it may concern"
"I am reaching out"
"Unique opportunity" / "amazing team" / "cutting-edge"
Two consecutive sentences starting with "I"
Any sentence that works equally well for a different company or role

SELF-CHECK before outputting — verify all 5:
1. Does sentence 1 contain a specific achievement or outcome, not a statement of intent?
2. Is there a named detail from {company}'s JD in paragraph 2 — product, tech, or challenge?
3. Does paragraph 3 have at least one concrete number or named technology from the resume?
4. Is the close original — NOT "look forward to hearing from you" or any variant?
5. Could ANY paragraph be copy-pasted into a cover letter for a different company? If yes, rewrite it.

Output: cover letter body only, salutation through sign-off. No subject line. No commentary before or after.
"""


def build_referral_ask_prompt(
    name: str, company: str, target_role: str, mutual_context: str | None
) -> str:
    context_block = (
        f"Relationship: {mutual_context}"
        if mutual_context
        else f"Relationship: no prior connection — this is a cold ask."
    )
    cold_note = (
        ""
        if mutual_context
        else f"\nFor cold asks: open by naming ONE specific, genuine reason you want to work at "
             f"{company} — a product, a technical problem they're solving, a team they're building. "
             "Not 'I've always admired your company.' Something that took 10 minutes to find.\n"
    )
    return f"""{_SYSTEM}

You are writing a LinkedIn DM that {name} will actually reply to.
Most referral asks are deleted. Yours will not — because it respects their time,
makes the ask specific, and makes it trivially easy to say yes or no.

━━━━━━━━━━━━━━━━━━━━━━━━
CONTEXT
Person:  {name} at {company}
Role:    {target_role}
{context_block}{cold_note}
━━━━━━━━━━━━━━━━━━━━━━━━
STRUCTURE — 3 sentences, 55 words maximum:

SENTENCE 1 — THE ANCHOR
Warm outreach or cold: anchor on something real and specific.
  • If you know them: reference the mutual context naturally. "We met at X" or "You helped me with Y."
  • If cold: one concrete reason you want THIS company — their product direction, a specific technical
    problem they're known for, or something they built. NOT "I've been following your work."

SENTENCE 2 — THE DIRECT ASK
State exactly what you want: a referral for the {target_role} role.
Be direct. Do not soften it into ambiguity. "Would you be open to referring me
for the {target_role} role?" is a complete sentence.

SENTENCE 3 — THE EASY OUT + OFFER
Make yes and no both frictionless.
Offer to send your resume and a short intro paragraph if they're up for it.
Acknowledge explicitly that it's fine if the timing or fit isn't right.
Example: "Happy to send my resume and a short blurb — and totally fine if it's not the right time."

━━━━━━━━━━━━━━━━━━━━━━━━
HARD CONSTRAINTS
- Opener exactly: "Hi {name},"
- Closer: your initials only, on a new line. No "Best regards", no "Thanks!", no sign-off phrase.
- 55 words maximum. Every word costs them attention. Spend it wisely.
- LinkedIn DM register: conversational. No business-letter formality.
- Do NOT open with flattery ("I've always admired", "I love what {company} is doing").
- Do NOT say "passionate", "dedicated", "hardworking", or any self-descriptor.
- Do NOT say "I came across your profile" or any variant.
- Do NOT apologise for asking.

Write only the DM body. No commentary.
"""


def build_referral_followup_prompt(
    name: str, company: str, days_since_msg: int
) -> str:
    urgency = (
        "It has been a short time — keep the tone light and genuinely low-pressure."
        if days_since_msg <= 5
        else "It has been a while — acknowledge it briefly but without guilt."
    )
    return f"""{_SYSTEM}

You are writing a LinkedIn follow-up to {name} at {company}.
{days_since_msg} days have passed since your referral ask. No reply yet.
{urgency}

THE SINGLE RULE: This message must feel like it was sent by someone who is
completely at peace with a "no" — because they are. The moment a follow-up
feels needy or guilty, it becomes a burden. Yours is not a burden.

━━━━━━━━━━━━━━━━━━━━━━━━
STRUCTURE — 2 sentences, 30 words maximum:

SENTENCE 1 — SURFACE WITHOUT GUILT
Bring the previous message back into view without restating it.
Do NOT begin with "Just", "Following up", or "Checking in" — those are the
exact words that make people groan when they open their inbox.
Instead: "Bumping this up in case it got lost" or "In case my note from last week
slipped by" or "Resurfacing this in case the timing is better now."

SENTENCE 2 — THE GENUINE OUT
Make it explicitly, warmly easy for them to say no or ignore this.
"Completely fine if it's not a fit — no action needed." or
"No worries at all if the timing isn't right."

━━━━━━━━━━━━━━━━━━━━━━━━
HARD CONSTRAINTS
- Opener exactly: "Hi {name},"
- Closer: your initials only, on a new line. No sign-off phrase.
- 30 words maximum. No exceptions.
- Do NOT say: "Just", "Following up", "Checking in", "I know you're busy",
  "Sorry to bother", "Thanks in advance", "Hope you're well", "Circling back".
- Zero guilt. Zero pressure. Zero apology.

Write only the DM body. No commentary.
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
    if draft_type == "cover_letter":
        company = kw.get("company")
        role = kw.get("role")
        contact_name = kw.get("contact_name")
        salutation = f"Dear {contact_name}," if contact_name else "Dear Hiring Team,"
        closer_name = contact_name or company
        return (
            f"{salutation}\n\n"
            f"My background in software engineering aligns directly with what you're building at "
            f"{company}. The {role} role caught my attention because it sits at the intersection "
            "of the technical challenges I've spent the last few years solving.\n\n"
            f"[Add a specific sentence about why {company} specifically — their product, mission, "
            "or a recent development that connects to your experience.]\n\n"
            "In my most recent role, I [describe your top 2-3 achievements with concrete outcomes "
            "— e.g. 'shipped a feature used by 50K daily users', 'reduced deploy time from 45 "
            "minutes to 8 minutes', 'led the migration of a legacy monolith to microservices']. "
            f"Each of these maps directly to what I'd bring to the {role} position.\n\n"
            f"I'd welcome a conversation about how I can contribute to {company}'s next chapter. "
            "Happy to share more details or work through a technical problem together.\n\n"
            "Sincerely,\n[Your name]"
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
