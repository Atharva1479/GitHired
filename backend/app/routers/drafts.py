import re
from datetime import date

import asyncpg
from fastapi import APIRouter, Depends, Response, status

from app.config import settings
from app.deps import get_db, get_user_id
from app.exceptions import RateLimited
from app.models import CoverLetterRequest, DraftOut, DraftRequest
from app.repositories import applications as apps_repo
from app.repositories import drafts as drafts_repo
from app.repositories import referrals as refs_repo
from app.services import gamify
from app.services.gemini_service import (
    build_cover_letter_prompt,
    build_followup_email_prompt,
    build_referral_ask_prompt,
    build_referral_followup_prompt,
    generate_or_fallback,
)
from app.services.ats.text_extractor import extract_text_from_bytes

router = APIRouter()


async def _check_quota(conn: asyncpg.Connection, user_id: int) -> None:
    today_count = await drafts_repo.daily_count(conn, user_id)
    if today_count >= settings.drafts_per_user_per_day:
        raise RateLimited(f"daily limit {settings.drafts_per_user_per_day} reached")


async def _get_sender_name(conn: asyncpg.Connection, user_id: int) -> str | None:
    """Return sender's full name from display_name."""
    row = await conn.fetchrow("SELECT display_name FROM users WHERE id = $1", user_id)
    name = (row["display_name"] or "").strip() if row else ""
    return name or None


_GREETING_RE  = re.compile(r'^Hi\s+.{1,60},\s*\n+', re.IGNORECASE)
# Strip entire sign-off block starting from common sign-off word
_SIGN_OFF_RE  = re.compile(
    r'\n+(?:Best|Regards|Cheers|Sincerely|Thanks?|Warm\s+regards?|Kind\s+regards?)[,.]?[\s\S]*$',
    re.IGNORECASE,
)
# Strip a single trailing bad line (initials / placeholder) when no sign-off word present
_BAD_LAST_RE  = re.compile(
    r'^(\[.*\]|[A-Z][A-Za-z.]{0,3})[,.]?\s*$',
    re.IGNORECASE,
)


def _strip_greeting_closer(text: str) -> str:
    """Remove any greeting and sign-off block the AI included so we can inject our own."""
    text = _GREETING_RE.sub("", text)       # drop leading "Hi X,\n"
    text = _SIGN_OFF_RE.sub("", text)       # drop "Best,...\nName" block
    # If a stray initials / placeholder line survived as the last line, drop it too
    lines = text.strip().splitlines()
    if lines and _BAD_LAST_RE.match(lines[-1].strip()):
        lines.pop()
    return "\n".join(lines).strip()


def _fix_closer(text: str, full_name: str | None) -> str:
    """No-op — kept for import safety."""
    return text


@router.post(
    "/application/{app_id}/followup",
    response_model=DraftOut,
    status_code=status.HTTP_200_OK,
)
async def application_followup(
    app_id: int,
    response: Response,
    body: DraftRequest = DraftRequest(),
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> DraftOut:
    app = await apps_repo.get_application(conn, app_id, user_id)

    if not body.regenerate:
        cached = await drafts_repo.latest_fresh(
            conn, user_id,
            entity_type="application",
            entity_id=app_id,
            draft_type="followup_email",
        )
        if cached:
            return cached

    await _check_quota(conn, user_id)
    days_elapsed = (date.today() - app.applied_date).days

    # Load resume text + sender name (application resume → skill-gap resumes → display_name)
    sender_name: str | None = None
    resume_text_for_prompt: str | None = None

    if app.resume_file_name:
        resume_path = settings.upload_dir / str(user_id) / str(app_id) / "resume.pdf"
        if resume_path.exists():
            try:
                from app.services.ats.resume_parser import parse_resume
                raw = await extract_text_from_bytes(resume_path.read_bytes(), "resume.pdf")
                resume_text_for_prompt = raw
                parsed = parse_resume(raw)
                lines = [l.strip() for l in parsed.get("contact", []) if l.strip()]
                for line in lines[:3]:
                    if len(line) > 3 and " " in line and not any(c.isdigit() for c in line):
                        sender_name = line
                        break
            except Exception:
                pass

    if not sender_name:
        sender_name = await _get_sender_name(conn, user_id)

    # Fall back to skill-gap resume text if no application resume
    if not resume_text_for_prompt:
        row = await conn.fetchrow(
            "SELECT parsed_text FROM resumes WHERE user_id = $1 AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 1",
            user_id,
        )
        if row and row["parsed_text"]:
            resume_text_for_prompt = row["parsed_text"]

    prompt = build_followup_email_prompt(
        company=app.company,
        role=app.role,
        days_elapsed=days_elapsed,
        contact_name=app.contact_name,
        sender_name=sender_name,
        resume_text=resume_text_for_prompt,
    )
    text, model, pt, ot, fb = await generate_or_fallback(
        draft_type="followup_email",
        prompt=prompt,
        company=app.company,
        role=app.role,
        days_elapsed=days_elapsed,
        contact_name=app.contact_name,
    )
    greeting = f"Hi {app.contact_name}," if app.contact_name else "Hi Hiring Team,"
    closer = f"Best,\n{sender_name}" if sender_name else "Best,"
    text = f"{greeting}\n\n{_strip_greeting_closer(text.strip())}\n\n{closer}"
    draft = await drafts_repo.insert(
        conn, user_id,
        entity_type="application",
        entity_id=app_id,
        draft_type="followup_email",
        content=text, model=model,
        prompt_tokens=pt, output_tokens=ot, fallback=fb,
    )
    gam = await gamify.record_event(
        conn, user_id, "draft.sent", ref_type="draft", ref_id=draft.id,
    )
    gamify.attach(response, gam)
    return draft


@router.post(
    "/application/{app_id}/cover-letter",
    response_model=DraftOut,
    status_code=status.HTTP_200_OK,
)
async def application_cover_letter(
    app_id: int,
    response: Response,
    body: CoverLetterRequest = CoverLetterRequest(),
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> DraftOut:
    app = await apps_repo.get_application(conn, app_id, user_id)

    if not body.regenerate:
        cached = await drafts_repo.latest_fresh(
            conn, user_id,
            entity_type="application",
            entity_id=app_id,
            draft_type="cover_letter",
        )
        if cached:
            return cached

    # Read the uploaded resume from disk and extract its text
    resume_text: str | None = None
    if app.resume_file_name:
        resume_path = settings.upload_dir / str(user_id) / str(app_id) / "resume.pdf"
        if resume_path.exists():
            try:
                resume_text = await extract_text_from_bytes(resume_path.read_bytes(), "resume.pdf")
            except Exception:
                resume_text = None

    await _check_quota(conn, user_id)
    prompt = build_cover_letter_prompt(
        company=app.company,
        role=app.role,
        jd_text=app.jd_text,
        resume_text=resume_text,
        contact_name=app.contact_name,
        tone=body.tone,
    )
    text, model, pt, ot, fb = await generate_or_fallback(
        draft_type="cover_letter",
        prompt=prompt,
        company=app.company,
        role=app.role,
        contact_name=app.contact_name,
    )
    draft = await drafts_repo.insert(
        conn, user_id,
        entity_type="application",
        entity_id=app_id,
        draft_type="cover_letter",
        content=text, model=model,
        prompt_tokens=pt, output_tokens=ot, fallback=fb,
    )
    gam = await gamify.record_event(
        conn, user_id, "draft.sent", ref_type="draft", ref_id=draft.id,
    )
    gamify.attach(response, gam)
    return draft


@router.post(
    "/referral/{ref_id}/ask",
    response_model=DraftOut,
    status_code=status.HTTP_200_OK,
)
async def referral_ask(
    ref_id: int,
    response: Response,
    body: DraftRequest = DraftRequest(),
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> DraftOut:
    ref = await refs_repo.get_referral(conn, ref_id, user_id)

    if not body.regenerate:
        cached = await drafts_repo.latest_fresh(
            conn, user_id,
            entity_type="referral",
            entity_id=ref_id,
            draft_type="referral_ask",
        )
        if cached:
            return cached

    await _check_quota(conn, user_id)

    # sender name: any resume for this user → fallback to display_name
    sender_name: str | None = await _get_sender_name(conn, user_id)

    # JD: find a matching application by company + role
    jd_row = await conn.fetchrow(
        """
        SELECT jd_text FROM applications
        WHERE user_id = $1 AND deleted_at IS NULL
          AND jd_text IS NOT NULL AND jd_text != ''
          AND company ILIKE $2
        ORDER BY created_at DESC LIMIT 1
        """,
        user_id, f"%{ref.company}%",
    )
    jd_text: str | None = jd_row["jd_text"] if jd_row else None

    prompt = build_referral_ask_prompt(
        name=ref.name,
        company=ref.company,
        target_role=ref.target_role,
        mutual_context=ref.mutual_context,
        sender_name=sender_name,
        jd_text=jd_text,
    )
    text, model, pt, ot, fb = await generate_or_fallback(
        draft_type="referral_ask",
        prompt=prompt,
        name=ref.name,
        company=ref.company,
        target_role=ref.target_role,
    )
    closer = f"Best,\n{sender_name}" if sender_name else "Best,"
    text = f"Hi {ref.name},\n\n{_strip_greeting_closer(text.strip())}\n\n{closer}"
    draft = await drafts_repo.insert(
        conn, user_id,
        entity_type="referral",
        entity_id=ref_id,
        draft_type="referral_ask",
        content=text, model=model,
        prompt_tokens=pt, output_tokens=ot, fallback=fb,
    )
    gam = await gamify.record_event(
        conn, user_id, "draft.sent", ref_type="draft", ref_id=draft.id,
    )
    gamify.attach(response, gam)
    return draft


@router.post(
    "/referral/{ref_id}/followup",
    response_model=DraftOut,
    status_code=status.HTTP_200_OK,
)
async def referral_followup(
    ref_id: int,
    response: Response,
    body: DraftRequest = DraftRequest(),
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> DraftOut:
    ref = await refs_repo.get_referral(conn, ref_id, user_id)

    if not body.regenerate:
        cached = await drafts_repo.latest_fresh(
            conn, user_id,
            entity_type="referral",
            entity_id=ref_id,
            draft_type="referral_followup",
        )
        if cached:
            return cached

    await _check_quota(conn, user_id)
    sender_name = await _get_sender_name(conn, user_id)
    base = ref.referral_msg_sent_date or ref.last_updated.date()
    days_since_msg = max((date.today() - base).days, 1)
    prompt = build_referral_followup_prompt(
        name=ref.name, company=ref.company,
        days_since_msg=days_since_msg, sender_name=sender_name,
    )
    text, model, pt, ot, fb = await generate_or_fallback(
        draft_type="referral_followup",
        prompt=prompt,
        name=ref.name,
    )
    closer = f"Best,\n{sender_name}" if sender_name else "Best,"
    text = f"Hi {ref.name},\n\n{_strip_greeting_closer(text.strip())}\n\n{closer}"
    draft = await drafts_repo.insert(
        conn, user_id,
        entity_type="referral",
        entity_id=ref_id,
        draft_type="referral_followup",
        content=text, model=model,
        prompt_tokens=pt, output_tokens=ot, fallback=fb,
    )
    gam = await gamify.record_event(
        conn, user_id, "draft.sent", ref_type="draft", ref_id=draft.id,
    )
    gamify.attach(response, gam)
    return draft


@router.get(
    "/{entity_type}/{entity_id}/history", response_model=list[DraftOut]
)
async def history(
    entity_type: str,
    entity_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> list[DraftOut]:
    if entity_type not in ("application", "referral"):
        from app.exceptions import NotFound
        raise NotFound(f"unknown entity_type={entity_type}")
    return await drafts_repo.history(
        conn, user_id, entity_type=entity_type, entity_id=entity_id,
    )
