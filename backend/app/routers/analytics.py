import asyncio
import datetime as dt

import asyncpg
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config import settings
from app.deps import get_db, get_user_id
from app.services.email_digest import send_digest_for_user, send_weekly_digest_for_all

router = APIRouter()


class FunnelStats(BaseModel):
    """
    Snapshot counts per pipeline stage. `applied` = total applications ever submitted
    (top of funnel). `screened`/`interviewed` = cumulative count of apps that reached or passed this stage.
    """
    applied: int
    screened: int
    interviewed: int
    offered: int
    response_rate: int   # % of closed apps that got a response (not Ghosted)
    offer_rate: int      # % of applied that became Offer


class SourceStat(BaseModel):
    source: str
    count: int
    response_rate: int   # % of closed from this source that got a response


class WeekPoint(BaseModel):
    week_start: str   # ISO date string "YYYY-MM-DD"
    count: int


class StatusStat(BaseModel):
    status: str
    count: int


class AnalyticsStats(BaseModel):
    funnel: FunnelStats
    by_source: list[SourceStat]
    weekly_trend: list[WeekPoint]    # last 8 weeks
    by_status: list[StatusStat]


@router.get("/stats", response_model=AnalyticsStats)
async def analytics_stats(
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> AnalyticsStats:
    # --- Funnel ---
    funnel_row = await conn.fetchrow(
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
    total = int(funnel_row["applied"])
    closed = int(funnel_row["closed"])
    ghosted = int(funnel_row["ghosted"])
    offered = int(funnel_row["offered"])
    response_rate = round(((closed - ghosted) / closed) * 100) if closed else 0
    offer_rate = round((offered / total) * 100) if total else 0

    funnel = FunnelStats(
        applied=total,
        screened=int(funnel_row["screened"]),
        interviewed=int(funnel_row["interviewed"]),
        offered=offered,
        response_rate=response_rate,
        offer_rate=offer_rate,
    )

    # --- By Source ---
    source_rows = await conn.fetch(
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
    by_source = []
    for r in source_rows:
        s_closed = int(r["closed"])
        s_ghosted = int(r["ghosted"])
        s_rate = round(((s_closed - s_ghosted) / s_closed) * 100) if s_closed else 0
        by_source.append(
            SourceStat(source=r["source"], count=int(r["total"]), response_rate=s_rate)
        )

    # --- Weekly Trend (last 8 weeks) ---
    eight_weeks_ago = dt.date.today() - dt.timedelta(weeks=8)
    trend_rows = await conn.fetch(
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
        eight_weeks_ago,
    )
    weekly_trend = [
        WeekPoint(week_start=str(r["week_start"]), count=int(r["cnt"]))
        for r in trend_rows
    ]

    # --- By Status ---
    status_rows = await conn.fetch(
        """
        SELECT status, COUNT(*) AS cnt
        FROM applications
        WHERE user_id = $1 AND deleted_at IS NULL
        GROUP BY status
        ORDER BY cnt DESC
        """,
        user_id,
    )
    by_status = [
        StatusStat(status=r["status"], count=int(r["cnt"]))
        for r in status_rows
    ]

    return AnalyticsStats(
        funnel=funnel,
        by_source=by_source,
        weekly_trend=weekly_trend,
        by_status=by_status,
    )


@router.post("/digest/trigger", status_code=202)
async def trigger_digest(
    user_id: int = Depends(get_user_id),
) -> dict[str, str]:
    """Dev endpoint: fire the weekly digest for the requesting user. Requires auth."""
    if settings.environment == "production":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Not available in production")
    import logging
    _log = logging.getLogger("analytics")
    task = asyncio.create_task(send_digest_for_user(user_id))
    task.add_done_callback(
        lambda t: t.exception() and _log.exception(
            "digest.trigger_failed user_id=%d", user_id, exc_info=t.exception()
        )
    )
    return {"status": "queued"}
