from datetime import date

import asyncpg
from fastapi import APIRouter, Depends, Query, Response, status

from app.deps import get_db, get_user_id
from app.models import ApplicationCreate, ApplicationOut, ApplicationUpdate, Source, Status
from app.repositories import applications as repo
from app.repositories.events import emit
from app.services import gamify

router = APIRouter()


@router.get("", response_model=list[ApplicationOut])
async def list_applications(
    status_: Status | None = Query(default=None, alias="status"),
    source: Source | None = None,
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    limit: int = Query(default=200, ge=1, le=500),
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> list[ApplicationOut]:
    return await repo.list_applications(
        conn, user_id,
        status=status_, source=source, date_from=date_from, date_to=date_to, limit=limit,
    )


@router.get("/{app_id}", response_model=ApplicationOut)
async def get_application(
    app_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> ApplicationOut:
    return await repo.get_application(conn, app_id, user_id)


@router.post("", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
async def create_application(
    data: ApplicationCreate,
    response: Response,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> ApplicationOut:
    async with conn.transaction():
        app = await repo.create_application(conn, user_id, data)
        await emit(conn, user_id, "application.created", {
            "application_id": app.id, "company": app.company, "role": app.role,
        })
        gam = await gamify.record_event(
            conn, user_id, "app.added", ref_type="application", ref_id=app.id,
        )
    gamify.attach(response, gam)
    return app


@router.patch("/{app_id}", response_model=ApplicationOut)
async def update_application(
    app_id: int,
    patch: ApplicationUpdate,
    response: Response,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> ApplicationOut:
    async with conn.transaction():
        before, after = await repo.update_application(conn, app_id, user_id, patch)
        if before.status != after.status:
            await emit(conn, user_id, "application.status_changed", {
                "application_id": app_id, "from": before.status, "to": after.status,
            })
            event_key = gamify.STATUS_EVENT_KEY.get(after.status)
            if event_key:
                gam = await gamify.record_event(
                    conn, user_id, event_key,
                    ref_type=f"status:{after.status}", ref_id=app_id,
                )
                gamify.attach(response, gam)
    return after


@router.delete("/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application(
    app_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> Response:
    await repo.soft_delete_application(conn, app_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{app_id}/followup", response_model=ApplicationOut)
async def followup_application(
    app_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> ApplicationOut:
    async with conn.transaction():
        app = await repo.increment_followup(conn, app_id, user_id)
        await emit(conn, user_id, "application.followup", {
            "application_id": app_id, "follow_up_count": app.follow_up_count,
        })
    return app
