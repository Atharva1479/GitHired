from collections.abc import AsyncIterator

import asyncpg
from fastapi import HTTPException, Request

from app.database import pool
from app.services import session
from app.services.observability import set_user_context

MVP_USER_ID = 1  # seed user; tests override get_user_id to return this


async def get_db() -> AsyncIterator[asyncpg.Connection]:
    async with pool().acquire() as conn:
        yield conn


async def get_user_id(request: Request) -> int:
    uid = session.read(request)
    if uid is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    set_user_context(uid)
    return uid
