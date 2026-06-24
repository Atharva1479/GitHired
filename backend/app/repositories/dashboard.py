"""Dashboard repository — aggregate queries for the main dashboard page."""
from __future__ import annotations

import datetime as dt
import json
from typing import Any

import asyncpg


async def get_app_stats_row(conn: asyncpg.Connection, user_id: int) -> dict[str, Any]:
    row = await conn.fetchrow(
        """
        SELECT
          COUNT(*) AS total,
          COUNT(*) FILTER (WHERE status = 'Applied') AS applied,
          COUNT(*) FILTER (WHERE status IN ('Applied','Screening','Interview')) AS in_progress,
          COUNT(*) FILTER (WHERE status = 'Offer') AS offers,
          COUNT(*) FILTER (WHERE status IN ('Offer','Rejected','Ghosted')) AS closed,
          COUNT(*) FILTER (WHERE status = 'Ghosted') AS ghosted
        FROM applications
        WHERE user_id = $1 AND deleted_at IS NULL
        """,
        user_id,
    )
    return dict(row) if row else {}


async def get_referral_stats_row(conn: asyncpg.Connection, user_id: int) -> dict[str, Any]:
    row = await conn.fetchrow(
        """
        SELECT
          COUNT(*) AS total,
          COUNT(*) FILTER (WHERE connection_status IN
            ('Request Sent','Accepted','Msg Sent')) AS in_progress,
          COUNT(*) FILTER (WHERE connection_status = 'Referred') AS referred,
          COUNT(*) FILTER (WHERE connection_status IN ('Referred','Dropped')) AS closed
        FROM referral_contacts
        WHERE user_id = $1 AND deleted_at IS NULL
        """,
        user_id,
    )
    return dict(row) if row else {}


async def get_nudge_stats_row(
    conn: asyncpg.Connection, user_id: int, today: dt.date
) -> dict[str, Any]:
    row = await conn.fetchrow(
        """
        SELECT
          COUNT(*) AS today,
          COUNT(*) FILTER (WHERE severity = 'overdue') AS overdue
        FROM nudges
        WHERE user_id = $1
          AND deleted_at IS NULL
          AND read_at IS NULL AND acted_at IS NULL
          AND (snoozed_until IS NULL OR snoozed_until < $2)
          AND fired_on_date <= $2
        """,
        user_id, today,
    )
    return dict(row) if row else {}


async def get_activity_rows(
    conn: asyncpg.Connection, user_id: int, limit: int
) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        """
        SELECT id, event_type, payload, occurred_at
        FROM events
        WHERE user_id = $1 AND deleted_at IS NULL
        ORDER BY occurred_at DESC LIMIT $2
        """,
        user_id, limit,
    )
    out = []
    for r in rows:
        payload = r["payload"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        out.append({
            "id": r["id"],
            "event_type": r["event_type"],
            "payload": payload or {},
            "occurred_at": r["occurred_at"],
        })
    return out
