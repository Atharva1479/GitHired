import datetime as dt

import asyncpg
from fastapi import APIRouter, Depends, Query, Response, status

from app.deps import get_db, get_user_id
from app.models import NudgeOut, NudgeSeverity, SnoozeBody
from app.repositories import nudges as repo
from app.services.nudge_engine import run_all_checks

router = APIRouter()


@router.get("", response_model=list[NudgeOut])
async def list_nudges(
    unread: bool | None = Query(default=None),
    severity: NudgeSeverity | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> list[NudgeOut]:
    return await repo.list_all(
        conn, user_id, unread=unread, severity=severity, limit=limit
    )


@router.get("/today", response_model=list[NudgeOut])
async def list_today(
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> list[NudgeOut]:
    return await repo.list_today(conn, user_id, dt.date.today())


@router.post("/{nudge_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(
    nudge_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> Response:
    await repo.mark_read(conn, nudge_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{nudge_id}/acted", status_code=status.HTTP_204_NO_CONTENT)
async def mark_acted(
    nudge_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> Response:
    await repo.mark_acted(conn, nudge_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{nudge_id}/snooze", status_code=status.HTTP_204_NO_CONTENT)
async def snooze(
    nudge_id: int,
    body: SnoozeBody,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> Response:
    await repo.snooze(conn, nudge_id, user_id, body.days)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/run", status_code=status.HTTP_202_ACCEPTED)
async def run_now(
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> dict[str, int]:
    inserted = await run_all_checks(conn, user_id, dt.date.today())
    return {"inserted": inserted}
