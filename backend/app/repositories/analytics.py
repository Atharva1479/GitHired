"""Analytics repository — all read-only aggregate queries for the analytics page."""
from __future__ import annotations

import datetime as dt
from typing import Any

import asyncpg


async def get_funnel_row(conn: asyncpg.Connection, user_id: int) -> dict[str, Any]:
    row = await conn.fetchrow(
        """
        SELECT
          COUNT(*) AS applied,
          COUNT(*) FILTER (WHERE status IN ('Screening','Interview','Offer','Rejected','Ghosted')) AS screened,
          COUNT(*) FILTER (WHERE status IN ('Interview','Offer')) AS interviewed,
          COUNT(*) FILTER (WHERE status = 'Offer') AS offered,
          COUNT(*) FILTER (WHERE status IN ('Offer','Rejected','Ghosted')) AS closed,
          COUNT(*) FILTER (WHERE status = 'Ghosted') AS ghosted
        FROM applications
        WHERE user_id = $1 AND deleted_at IS NULL
        """,
        user_id,
    )
    return dict(row) if row else {}


async def get_source_rows(conn: asyncpg.Connection, user_id: int) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        """
        SELECT
          source,
          COUNT(*) AS total,
          COUNT(*) FILTER (WHERE status IN ('Offer','Rejected','Ghosted')) AS closed,
          COUNT(*) FILTER (WHERE status = 'Ghosted') AS ghosted
        FROM applications
        WHERE user_id = $1 AND deleted_at IS NULL
        GROUP BY source
        ORDER BY total DESC
        """,
        user_id,
    )
    return [dict(r) for r in rows]


async def get_weekly_trend_rows(
    conn: asyncpg.Connection, user_id: int, since: dt.date
) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        """
        SELECT
          date_trunc('week', applied_date)::date AS week_start,
          COUNT(*) AS cnt
        FROM applications
        WHERE user_id = $1
          AND deleted_at IS NULL
          AND applied_date >= $2
        GROUP BY week_start
        ORDER BY week_start
        """,
        user_id,
        since,
    )
    return [dict(r) for r in rows]


async def get_status_rows(conn: asyncpg.Connection, user_id: int) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        """
        SELECT status, COUNT(*) AS cnt
        FROM applications
        WHERE user_id = $1 AND deleted_at IS NULL
        GROUP BY status
        ORDER BY cnt DESC
        """,
        user_id,
    )
    return [dict(r) for r in rows]
