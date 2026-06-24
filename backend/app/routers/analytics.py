import asyncio
import datetime as dt

import asyncpg
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config import settings
from app.deps import get_db, get_user_id
from app.repositories import analytics as analytics_repo
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
    funnel_row = await analytics_repo.get_funnel_row(conn, user_id)
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

    source_rows = await analytics_repo.get_source_rows(conn, user_id)
    by_source = []
    for r in source_rows:
        s_closed = int(r["closed"])
        s_ghosted = int(r["ghosted"])
        s_rate = round(((s_closed - s_ghosted) / s_closed) * 100) if s_closed else 0
        by_source.append(
            SourceStat(source=r["source"], count=int(r["total"]), response_rate=s_rate)
        )

    eight_weeks_ago = dt.date.today() - dt.timedelta(weeks=8)
    trend_rows = await analytics_repo.get_weekly_trend_rows(conn, user_id, eight_weeks_ago)
    weekly_trend = [
        WeekPoint(week_start=str(r["week_start"]), count=int(r["cnt"]))
        for r in trend_rows
    ]

    status_rows = await analytics_repo.get_status_rows(conn, user_id)
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
    import structlog as _structlog
    _log = _structlog.get_logger("analytics")
    task = asyncio.create_task(send_digest_for_user(user_id))
    task.add_done_callback(
        lambda t: t.exception() and _log.error(
            "digest.trigger_failed", user_id=user_id, error=str(t.exception())
        )
    )
    return {"status": "queued"}
