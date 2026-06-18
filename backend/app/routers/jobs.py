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
from app.repositories import resumes as resumes_repo
from app.services import job_search
from app.services.ats.scorer import analyze_resume
from app.services.job_search import get_similar_jobs

log = structlog.get_logger("jobs_router")
router = APIRouter()


@router.get("/search", response_model=list[JobResult])
async def search_jobs(
    q: str = Query(min_length=1, max_length=200),
    location: str | None = Query(default=None),
    remote_only: bool = Query(default=False),
    experience: str | None = Query(default=None),
    resume_id: int | None = Query(default=None),
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> list[JobResult]:
    results = await job_search.search_jobs(
        conn=conn,
        query=q,
        location=location,
        remote_only=remote_only,
        experience=experience,
        user_id=user_id,
        resume_id=resume_id,
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


@router.get("/{job_cache_id}/similar", response_model=list[JobResult])
async def similar_jobs(
    job_cache_id: int,
    limit: int = Query(default=3, ge=1, le=10),
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> list[JobResult]:
    """Return similar fresh jobs from cache based on the applied job's title."""
    results = await get_similar_jobs(conn, job_cache_id, user_id, limit)
    return [JobResult(**r) for r in results]


async def _get_resume_and_job(
    conn: asyncpg.Connection,
    user_id: int,
    job_cache_id: int,
) -> tuple[str | None, str | None]:
    """Return (resume_text, jd_text) or (None, None) on missing data."""
    resume_text = await conn.fetchval(
        "SELECT parsed_text FROM resumes WHERE user_id=$1 AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 1",
        user_id,
    )
    jd_text = await conn.fetchval(
        "SELECT description FROM job_cache WHERE id=$1", job_cache_id
    )
    return resume_text, jd_text


@router.get("/{job_cache_id}/match")
async def match_resume(
    job_cache_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> JSONResponse:
    """Score user's latest resume against a cached job description.

    Returns { score, grade, top_missing } or { score: null } if no resume/JD.
    """
    resume_text, jd_text = await _get_resume_and_job(conn, user_id, job_cache_id)
    if not resume_text:
        return JSONResponse({"score": None, "grade": None, "top_missing": [], "reason": "no_resume"})
    if not jd_text:
        return JSONResponse({"score": None, "grade": None, "top_missing": [], "reason": "no_jd"})

    try:
        result = await analyze_resume(resume_text, jd_text)
        top_missing = (result.get("required_missing") or [])[:4]
        return JSONResponse({
            "score": result["overall_score"],
            "grade": result.get("grade", ""),
            "top_missing": top_missing,
        })
    except Exception as exc:
        log.warning("jobs.match_failed", job_cache_id=job_cache_id, error=str(exc))
        return JSONResponse({"score": None, "grade": None, "top_missing": [], "reason": "error"})


@router.post("/{job_cache_id}/ats-scan")
async def ats_scan(
    job_cache_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> JSONResponse:
    """Run full ATS analysis using the user's latest resume vs this job's JD.

    Frontend stores the result in localStorage and navigates to /ats/results.
    """
    resume_text, jd_text = await _get_resume_and_job(conn, user_id, job_cache_id)
    if not resume_text:
        raise HTTPException(422, "No resume uploaded. Upload a resume first in the Skills Analyser.")
    if not jd_text:
        raise HTTPException(422, "This job has no description available for scanning.")

    try:
        result = await analyze_resume(resume_text, jd_text)
        return JSONResponse(result)
    except Exception as exc:
        log.error("jobs.ats_scan_failed", job_cache_id=job_cache_id, error=str(exc))
        raise HTTPException(500, "ATS scan failed. Please try again.")


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
