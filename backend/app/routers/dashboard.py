from datetime import date, datetime
from typing import Any

import asyncpg
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.deps import get_db, get_user_id

router = APIRouter()


class ApplicationsStats(BaseModel):
    total: int
    applied: int
    in_progress: int
    offers: int
    response_rate: int


class ReferralsStats(BaseModel):
    total: int
    in_progress: int
    referred: int
    conversion_rate: int


class NudgesStats(BaseModel):
    today: int
    overdue: int


class DashboardStats(BaseModel):
    applications: ApplicationsStats
    referrals: ReferralsStats
    nudges: NudgesStats


class ActivityItem(BaseModel):
    id: int
    event_type: str
    payload: dict[str, Any]
    occurred_at: datetime


@router.get("/stats", response_model=DashboardStats)
async def stats(
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> DashboardStats:
    app_row = await conn.fetchrow(
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
    a_total = int(app_row["total"])
    a_closed = int(app_row["closed"])
    a_ghosted = int(app_row["ghosted"])
    a_response = (
        round(((a_closed - a_ghosted) / a_closed) * 100) if a_closed else 0
    )

    ref_row = await conn.fetchrow(
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
    r_total = int(ref_row["total"])
    r_referred = int(ref_row["referred"])
    r_closed = int(ref_row["closed"])
    r_conv = round((r_referred / r_closed) * 100) if r_closed else 0

    nudge_row = await conn.fetchrow(
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
        user_id, date.today(),
    )

    return DashboardStats(
        applications=ApplicationsStats(
            total=a_total,
            applied=int(app_row["applied"]),
            in_progress=int(app_row["in_progress"]),
            offers=int(app_row["offers"]),
            response_rate=a_response,
        ),
        referrals=ReferralsStats(
            total=r_total,
            in_progress=int(ref_row["in_progress"]),
            referred=r_referred,
            conversion_rate=r_conv,
        ),
        nudges=NudgesStats(
            today=int(nudge_row["today"]),
            overdue=int(nudge_row["overdue"]),
        ),
    )


@router.get("/activity", response_model=list[ActivityItem])
async def activity(
    limit: int = Query(default=15, ge=1, le=50),
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> list[ActivityItem]:
    import json

    rows = await conn.fetch(
        """
        SELECT id, event_type, payload, occurred_at
        FROM events
        WHERE user_id = $1 AND deleted_at IS NULL
        ORDER BY occurred_at DESC LIMIT $2
        """,
        user_id, limit,
    )
    out: list[ActivityItem] = []
    for r in rows:
        payload = r["payload"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        out.append(
            ActivityItem(
                id=r["id"],
                event_type=r["event_type"],
                payload=payload or {},
                occurred_at=r["occurred_at"],
            )
        )
    return out
