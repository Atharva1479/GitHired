import json
from typing import Any

import asyncpg


async def emit(
    conn: asyncpg.Connection,
    user_id: int,
    event_type: str,
    payload: dict[str, Any] | None = None,
) -> None:
    await conn.execute(
        "INSERT INTO events (user_id, event_type, payload) VALUES ($1, $2, $3::jsonb)",
        user_id, event_type, json.dumps(payload or {}),
    )
