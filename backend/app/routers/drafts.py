from datetime import date

import asyncpg
from fastapi import APIRouter, Depends, Response, status

from app.config import settings
from app.deps import get_db, get_user_id
from app.exceptions import RateLimited
from app.models import DraftOut, DraftRequest
from app.repositories import applications as apps_repo
from app.repositories import drafts as drafts_repo
from app.repositories import referrals as refs_repo
from app.services import gamify
from app.services.gemini_service import (
    build_followup_email_prompt,
    build_referral_ask_prompt,
    build_referral_followup_prompt,
    generate_or_fallback,
)

router = APIRouter()


async def _check_quota(conn: asyncpg.Connection, user_id: int) -> None:
    today_count = await drafts_repo.daily_count(conn, user_id)
    if today_count >= settings.drafts_per_user_per_day:
        raise RateLimited(f"daily limit {settings.drafts_per_user_per_day} reached")


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
    prompt = build_followup_email_prompt(
        company=app.company,
        role=app.role,
        days_elapsed=days_elapsed,
        contact_name=app.contact_name,
    )
    text, model, pt, ot, fb = await generate_or_fallback(
        draft_type="followup_email",
        prompt=prompt,
        company=app.company,
        role=app.role,
        days_elapsed=days_elapsed,
        contact_name=app.contact_name,
    )
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
    prompt = build_referral_ask_prompt(
        name=ref.name,
        company=ref.company,
        target_role=ref.target_role,
        mutual_context=ref.mutual_context,
    )
    text, model, pt, ot, fb = await generate_or_fallback(
        draft_type="referral_ask",
        prompt=prompt,
        name=ref.name,
        company=ref.company,
        target_role=ref.target_role,
    )
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
    base = ref.referral_msg_sent_date or ref.last_updated.date()
    days_since_msg = max((date.today() - base).days, 1)
    prompt = build_referral_followup_prompt(
        name=ref.name, company=ref.company, days_since_msg=days_since_msg,
    )
    text, model, pt, ot, fb = await generate_or_fallback(
        draft_type="referral_followup",
        prompt=prompt,
        name=ref.name,
    )
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
