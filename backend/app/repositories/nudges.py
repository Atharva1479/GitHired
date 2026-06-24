from datetime import date

import asyncpg

from app.exceptions import NotFound
from app.models import NudgeOut
from app.services import metrics

_COLS = """
    id, type, reference_type, reference_id, severity, message,
    fired_on_date, read_at, acted_at, snoozed_until, created_at
"""


def _row_to_out(row: asyncpg.Record) -> NudgeOut:
    return NudgeOut.model_validate(dict(row))


async def insert_if_absent(
    conn: asyncpg.Connection,
    user_id: int,
    *,
    type_: str,
    reference_type: str,
    reference_id: int | None,
    severity: str,
    message: str,
    fired_on_date: date,
) -> int:
    """Returns 1 if inserted, 0 if dedup index matched."""
    val = await conn.fetchval(
        """
        INSERT INTO nudges (
            user_id, type, reference_type, reference_id, severity, message, fired_on_date
        ) VALUES ($1,$2,$3,$4,$5,$6,$7)
        ON CONFLICT DO NOTHING
        RETURNING 1
        """,
        user_id, type_, reference_type, reference_id, severity, message, fired_on_date,
    )
    if val == 1:
        metrics.record_nudge(type_, severity)
        return 1
    return 0


async def insert_many(
    conn: asyncpg.Connection,
    user_id: int,
    candidates: list[tuple[str, str, int | None, str, str]],
    fired_on_date: date,
) -> int:
    """Batch-insert nudge candidates in a single query. Returns count of new rows inserted."""
    if not candidates:
        return []
    types = [c[0] for c in candidates]
    ref_types = [c[1] for c in candidates]
    ref_ids = [c[2] for c in candidates]
    severities = [c[3] for c in candidates]
    messages = [c[4] for c in candidates]
    rows = await conn.fetch(
        """
        INSERT INTO nudges (user_id, type, reference_type, reference_id, severity, message, fired_on_date)
        SELECT $1, t, rt, ri, sev, msg, $7
        FROM UNNEST($2::text[], $3::text[], $4::int[], $5::text[], $6::text[])
          AS u(t, rt, ri, sev, msg)
        ON CONFLICT DO NOTHING
        RETURNING type, severity
        """,
        user_id, types, ref_types, ref_ids, severities, messages, fired_on_date,
    )
    for r in rows:
        metrics.record_nudge(r["type"], r["severity"])
    return len(rows)


async def list_today(
    conn: asyncpg.Connection, user_id: int, today: date
) -> list[NudgeOut]:
    rows = await conn.fetch(
        f"""
        SELECT {_COLS} FROM nudges
        WHERE user_id = $1
          AND deleted_at IS NULL
          AND read_at IS NULL AND acted_at IS NULL
          AND (snoozed_until IS NULL OR snoozed_until < $2)
          AND fired_on_date <= $2
        ORDER BY CASE severity
                   WHEN 'overdue' THEN 0
                   WHEN 'due'     THEN 1
                   WHEN 'info'    THEN 2
                 END,
                 fired_on_date DESC,
                 id DESC
        """,
        user_id, today,
    )
    return [_row_to_out(r) for r in rows]


async def list_all(
    conn: asyncpg.Connection,
    user_id: int,
    *,
    unread: bool | None = None,
    severity: str | None = None,
    limit: int = 200,
) -> list[NudgeOut]:
    clauses = ["user_id = $1", "deleted_at IS NULL"]
    args: list[object] = [user_id]
    if unread is True:
        clauses.append("read_at IS NULL AND acted_at IS NULL")
    if severity:
        clauses.append(f"severity = ${len(args) + 1}")
        args.append(severity)
    args.append(limit)
    sql = (
        f"SELECT {_COLS} FROM nudges "
        f"WHERE {' AND '.join(clauses)} "
        f"ORDER BY created_at DESC LIMIT ${len(args)}"
    )
    rows = await conn.fetch(sql, *args)
    return [_row_to_out(r) for r in rows]


async def mark_read(conn: asyncpg.Connection, nudge_id: int, user_id: int) -> None:
    result = await conn.execute(
        "UPDATE nudges SET read_at = NOW() "
        "WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL "
        "AND read_at IS NULL",
        nudge_id, user_id,
    )
    if result.endswith(" 0"):
        # either not found or already read — confirm existence
        exists = await conn.fetchval(
            "SELECT 1 FROM nudges WHERE id = $1 AND user_id = $2 "
            "AND deleted_at IS NULL",
            nudge_id, user_id,
        )
        if not exists:
            raise NotFound(f"nudge id={nudge_id}")


async def mark_acted(conn: asyncpg.Connection, nudge_id: int, user_id: int) -> None:
    result = await conn.execute(
        "UPDATE nudges SET acted_at = NOW(), read_at = COALESCE(read_at, NOW()) "
        "WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL",
        nudge_id, user_id,
    )
    if result.endswith(" 0"):
        raise NotFound(f"nudge id={nudge_id}")


async def snooze(
    conn: asyncpg.Connection, nudge_id: int, user_id: int, days: int
) -> None:
    result = await conn.execute(
        "UPDATE nudges "
        "SET snoozed_until = (CURRENT_DATE + ($1::int * INTERVAL '1 day'))::date "
        "WHERE id = $2 AND user_id = $3 AND deleted_at IS NULL",
        days, nudge_id, user_id,
    )
    if result.endswith(" 0"):
        raise NotFound(f"nudge id={nudge_id}")
