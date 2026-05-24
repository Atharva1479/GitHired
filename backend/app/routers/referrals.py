import asyncpg
from fastapi import APIRouter, Depends, Query, Response, status

from app.deps import get_db, get_user_id
from app.models import (
    ApplicationOut,
    ConnectionStatus,
    ReferralCreate,
    ReferralOut,
    ReferralUpdate,
)
from app.repositories import referrals as repo
from app.repositories.events import emit
from app.services import gamify

router = APIRouter()


@router.get("", response_model=list[ReferralOut])
async def list_referrals(
    connection_status: ConnectionStatus | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> list[ReferralOut]:
    return await repo.list_referrals(
        conn, user_id, connection_status=connection_status, limit=limit
    )


@router.get("/{ref_id}", response_model=ReferralOut)
async def get_referral(
    ref_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> ReferralOut:
    return await repo.get_referral(conn, ref_id, user_id)


@router.post("", response_model=ReferralOut, status_code=status.HTTP_201_CREATED)
async def create_referral(
    data: ReferralCreate,
    response: Response,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> ReferralOut:
    async with conn.transaction():
        ref = await repo.create_referral(conn, user_id, data)
        await emit(conn, user_id, "referral.created", {
            "referral_id": ref.id, "name": ref.name, "company": ref.company,
        })
        gam = await gamify.record_event(
            conn, user_id, "referral.added", ref_type="referral", ref_id=ref.id,
        )
    gamify.attach(response, gam)
    return ref


@router.patch("/{ref_id}", response_model=ReferralOut)
async def update_referral(
    ref_id: int,
    patch: ReferralUpdate,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> ReferralOut:
    async with conn.transaction():
        before, after = await repo.update_referral(conn, ref_id, user_id, patch)
        if before.connection_status != after.connection_status:
            await emit(conn, user_id, "referral.status_changed", {
                "referral_id": ref_id,
                "from": before.connection_status,
                "to": after.connection_status,
            })
    return after


@router.delete("/{ref_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_referral(
    ref_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> Response:
    await repo.soft_delete_referral(conn, ref_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{ref_id}/mark-accepted", response_model=ReferralOut)
async def mark_accepted(
    ref_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> ReferralOut:
    async with conn.transaction():
        ref = await repo.mark_accepted(conn, ref_id, user_id)
        await emit(conn, user_id, "referral.accepted", {"referral_id": ref_id})
    return ref


@router.post("/{ref_id}/mark-sent", response_model=ReferralOut)
async def mark_sent(
    ref_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> ReferralOut:
    async with conn.transaction():
        ref = await repo.mark_sent(conn, ref_id, user_id)
        await emit(conn, user_id, "referral.message_sent", {"referral_id": ref_id})
    return ref


@router.post("/{ref_id}/mark-replied", response_model=ReferralOut)
async def mark_replied(
    ref_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> ReferralOut:
    async with conn.transaction():
        ref = await repo.mark_replied(conn, ref_id, user_id)
        await emit(conn, user_id, "referral.replied", {"referral_id": ref_id})
    return ref


@router.post(
    "/{ref_id}/link-application/{app_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def link_application(
    ref_id: int,
    app_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> Response:
    async with conn.transaction():
        await repo.link_application(conn, ref_id, app_id, user_id)
        await emit(conn, user_id, "referral.linked", {
            "referral_id": ref_id, "application_id": app_id,
        })
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/{ref_id}/link-application/{app_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def unlink_application(
    ref_id: int,
    app_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> Response:
    await repo.unlink_application(conn, ref_id, app_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{ref_id}/applications", response_model=list[ApplicationOut])
async def list_linked_applications(
    ref_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> list[ApplicationOut]:
    return await repo.list_linked_applications(conn, ref_id, user_id)
