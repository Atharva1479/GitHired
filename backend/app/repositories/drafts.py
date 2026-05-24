import asyncpg

from app.models import DraftOut

_COLS = """
    id, entity_type, entity_id, draft_type, content, model,
    prompt_tokens, output_tokens, fallback, created_at
"""


def _row_to_out(row: asyncpg.Record, *, cached: bool) -> DraftOut:
    d = dict(row)
    d["cached"] = cached
    return DraftOut.model_validate(d)


async def latest_fresh(
    conn: asyncpg.Connection,
    user_id: int,
    *,
    entity_type: str,
    entity_id: int,
    draft_type: str,
    fresh_hours: int = 24,
) -> DraftOut | None:
    row = await conn.fetchrow(
        f"""
        SELECT {_COLS} FROM drafts
        WHERE user_id = $1 AND entity_type = $2 AND entity_id = $3
          AND draft_type = $4
          AND deleted_at IS NULL
          AND created_at >= NOW() - ($5::int * INTERVAL '1 hour')
        ORDER BY created_at DESC LIMIT 1
        """,
        user_id, entity_type, entity_id, draft_type, fresh_hours,
    )
    return _row_to_out(row, cached=True) if row else None


async def insert(
    conn: asyncpg.Connection,
    user_id: int,
    *,
    entity_type: str,
    entity_id: int,
    draft_type: str,
    content: str,
    model: str,
    prompt_tokens: int = 0,
    output_tokens: int = 0,
    fallback: bool = False,
) -> DraftOut:
    row = await conn.fetchrow(
        f"""
        INSERT INTO drafts (
            user_id, entity_type, entity_id, draft_type, content, model,
            prompt_tokens, output_tokens, fallback
        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
        RETURNING {_COLS}
        """,
        user_id, entity_type, entity_id, draft_type, content, model,
        prompt_tokens, output_tokens, fallback,
    )
    return _row_to_out(row, cached=False)


async def daily_count(conn: asyncpg.Connection, user_id: int) -> int:
    val = await conn.fetchval(
        "SELECT COALESCE(draft_count, 0) FROM v_user_daily_drafts "
        "WHERE user_id = $1 AND day = CURRENT_DATE",
        user_id,
    )
    return int(val or 0)


async def history(
    conn: asyncpg.Connection,
    user_id: int,
    *,
    entity_type: str,
    entity_id: int,
    limit: int = 20,
) -> list[DraftOut]:
    rows = await conn.fetch(
        f"""
        SELECT {_COLS} FROM drafts
        WHERE user_id = $1 AND entity_type = $2 AND entity_id = $3
          AND deleted_at IS NULL
        ORDER BY created_at DESC LIMIT $4
        """,
        user_id, entity_type, entity_id, limit,
    )
    return [_row_to_out(r, cached=True) for r in rows]
