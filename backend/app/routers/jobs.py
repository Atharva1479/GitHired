"""Job discovery endpoints. Mounted at /api/jobs."""
from __future__ import annotations

from datetime import datetime, timezone

import asyncpg
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, Response

from app.deps import get_db, get_user_id
from app.models import (
    ApplyAndTrackOut,
    ApplyAndTrackRequest,
    JobResult,
    JobSearchCreate,
    JobSearchOut,
)
from app.repositories import jobs as repo
from app.services import job_search

log = structlog.get_logger("jobs_router")
router = APIRouter()


@router.get("/search", response_model=list[JobResult])
async def search_jobs(
    q: str = Query(min_length=1, max_length=200),
    location: str | None = Query(default=None),
    remote_only: bool = Query(default=False),
    experience: str | None = Query(default=None),
    freshness_hours: int = Query(default=24, ge=1, le=168),
    page: int = Query(default=1, ge=1, le=10),
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> list[JobResult]:
    results = await job_search.search_jobs(
        conn=conn,
        query=q,
        location=location,
        remote_only=remote_only,
        experience=experience,
        freshness_hours=freshness_hours,
        user_id=user_id,
        page=page,
    )
    return [JobResult(**r) for r in results]


@router.get("/searches", response_model=list[JobSearchOut])
async def list_searches(
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> list[JobSearchOut]:
    rows = await repo.list_searches(conn, user_id)
    return [JobSearchOut(**dict(r)) for r in rows]


@router.post("/searches", response_model=JobSearchOut, status_code=status.HTTP_201_CREATED)
async def create_search(
    body: JobSearchCreate,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> JobSearchOut:
    row = await repo.create_search(
        conn, user_id, body.name, body.query,
        body.location, body.remote_only, body.experience, body.freshness_hours,
    )
    return JobSearchOut(**dict(row))


@router.delete("/searches/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_search(
    search_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> Response:
    deleted = await repo.delete_search(conn, search_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Saved search not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/bookmark/{job_cache_id}", status_code=status.HTTP_201_CREATED)
async def bookmark_job(
    job_cache_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> JSONResponse:
    row = await conn.fetchrow("SELECT * FROM job_cache WHERE id = $1", job_cache_id)
    if not row:
        raise HTTPException(404, "Job not found in cache")
    bm = await repo.upsert_bookmark(
        conn, user_id,
        job_cache_id=row["id"],
        title=row["title"],
        company=row["company"],
        apply_url=row["apply_url"],
        posted_at=row["posted_at"],
        source=row["source"],
        external_id=row["external_id"],
        status="bookmarked",
    )
    return JSONResponse({"bookmark_id": bm["id"]}, status_code=201)


@router.get("/bookmarks")
async def list_bookmarks(
    status_filter: str | None = Query(default=None, alias="status"),
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> JSONResponse:
    rows = await repo.list_bookmarks(conn, user_id, status_filter)
    return JSONResponse([dict(r) for r in rows])


@router.post("/apply", response_model=ApplyAndTrackOut, status_code=status.HTTP_201_CREATED)
async def apply_and_track(
    body: ApplyAndTrackRequest,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> ApplyAndTrackOut:
    """Create a bookmark + application entry in one transaction.

    Returns 409 if the user has already applied to this job.
    """
    # Duplicate guard — check if user already applied to this exact job
    existing = await conn.fetchrow(
        "SELECT id, application_id FROM job_bookmarks WHERE user_id=$1 AND source=$2 AND external_id=$3 AND status='applied'",
        user_id, body.source, body.external_id,
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"already_applied:{existing['application_id']}",
        )

    async with conn.transaction():
        app_row = await conn.fetchrow(
            """
            INSERT INTO applications
              (user_id, company, role, source, status, applied_date, jd_url, jd_text)
            VALUES ($1, $2, $3, $4, 'Applied', CURRENT_DATE, $5, $6)
            RETURNING id
            """,
            user_id,
            body.company,
            body.title,
            _source_from_apply_url(body.apply_url),
            body.apply_url,
            body.description,
        )
        application_id: int = app_row["id"]

        bm = await repo.upsert_bookmark(
            conn, user_id,
            job_cache_id=body.job_cache_id,
            title=body.title,
            company=body.company,
            apply_url=body.apply_url,
            posted_at=body.posted_at,
            source=body.source,
            external_id=body.external_id,
            status="applied",
            application_id=application_id,
        )

    log.info("jobs.apply_and_track", user_id=user_id, company=body.company, application_id=application_id)
    return ApplyAndTrackOut(bookmark_id=bm["id"], application_id=application_id)


def _source_from_apply_url(url: str) -> str:
    u = url.lower()
    if "linkedin" in u:
        return "LinkedIn"
    if "naukri" in u:
        return "Naukri"
    if "indeed" in u:
        return "CompanySite"
    if "glassdoor" in u:
        return "CompanySite"
    return "Other"
