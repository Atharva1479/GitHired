import datetime as dt

import asyncpg
from fastapi import APIRouter, Depends, Response, status

from app.deps import get_db, get_user_id
from app.services import gamify

router = APIRouter()


@router.get("/state")
async def get_state(
    response: Response,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> dict:
    async with conn.transaction():
        await gamify.rotate_quests_for_user(conn, user_id)
        gam = await gamify.record_event(
            conn, user_id, "daily.login",
            ref_type="login", ref_id=dt.date.today().toordinal(),
        )
        state = await gamify.get_state(conn, user_id)
    gamify.attach(response, gam)
    return state.to_dict()


@router.post("/acknowledge", status_code=status.HTTP_204_NO_CONTENT)
async def acknowledge(
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> Response:
    await gamify.acknowledge(conn, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/achievements")
async def list_achievements(
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> list[dict]:
    return await gamify.list_achievements(conn, user_id)
