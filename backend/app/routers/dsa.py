"""DSA Progress Tracker REST endpoints.

Mounted at /api/dsa. The router is intentionally thin: it converts
Pydantic models → repo calls and emits the audit event + gamify XP
for creates and AI analysis. All authorisation is via the existing
``Depends(get_user_id)`` session check; rows are filtered by
user_id in the repo SQL.
"""
from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.config import settings
from app.deps import get_db, get_user_id
from app.models import (
    DsaAnalysisOut,
    DsaProblemCreate,
    DsaProblemOut,
    DsaProblemUpdate,
    DsaStatsOut,
)
from app.repositories import dsa as repo
from app.repositories.events import emit
from app.services import gamify
from app.services.dsa_ai import analyze_solution
from app.services.security import limiter

router = APIRouter()

_ANALYZE_RATE = f"{settings.pilot_rate_limit_per_minute}/minute"


# ──────────────────────────  stats  ───────────────────────────────────


@router.get("/stats", response_model=DsaStatsOut)
async def get_stats(
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> DsaStatsOut:
    return await repo.get_stats(conn, user_id)


# ──────────────────────────  problems  ────────────────────────────────


@router.get("/problems", response_model=list[DsaProblemOut])
async def list_problems(
    topic: str | None = Query(default=None),
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> list[DsaProblemOut]:
    return await repo.list_problems(conn, user_id, topic=topic)


@router.post(
    "/problems",
    response_model=DsaProblemOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_problem(
    data: DsaProblemCreate,
    response: Response,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> DsaProblemOut:
    async with conn.transaction():
        problem = await repo.create_problem(conn, user_id, data)
        await emit(
            conn, user_id, "dsa.problem_logged",
            {"problem_id": problem.id, "topic": problem.topic},
        )
        gam = await gamify.record_event(
            conn, user_id, "dsa.problem_logged",
            ref_type="dsa_problem", ref_id=problem.id,
        )
    gamify.attach(response, gam)
    return problem


@router.get("/problems/{problem_id}", response_model=DsaProblemOut)
async def get_problem(
    problem_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> DsaProblemOut:
    return await repo.get_problem(conn, problem_id, user_id)


@router.patch("/problems/{problem_id}", response_model=DsaProblemOut)
async def update_problem(
    problem_id: int,
    patch: DsaProblemUpdate,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> DsaProblemOut:
    return await repo.update_problem(conn, problem_id, user_id, patch)


@router.delete(
    "/problems/{problem_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_problem(
    problem_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> Response:
    await repo.soft_delete_problem(conn, problem_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ──────────────────────────  analyze  ─────────────────────────────────


@router.post(
    "/problems/{problem_id}/analyze",
    response_model=DsaAnalysisOut,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(_ANALYZE_RATE)
async def analyze_problem(
    request: Request,
    problem_id: int,
    response: Response,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> DsaAnalysisOut:
    problem = await repo.get_problem(conn, problem_id, user_id)

    if not problem.user_solution:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot analyze: problem has no user_solution.",
        )

    try:
        result = await analyze_solution(
            title=problem.title,
            topic=problem.topic,
            description=problem.description,
            user_solution=problem.user_solution,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI analysis unavailable. Try again later.",
        ) from exc

    async with conn.transaction():
        analysis = await repo.create_analysis(
            conn,
            problem_id=problem_id,
            user_id=user_id,
            time_complexity=result["time_complexity"],
            space_complexity=result["space_complexity"],
            approach_summary=result["approach_summary"],
            feedback=result["feedback"],
            optimized_solution=result["optimized_solution"],
            optimized_explanation=result["optimized_explanation"],
            dry_run_explanation=result["dry_run_explanation"],
            model=result.get("model", "gemini"),
        )
        gam = await gamify.record_event(
            conn, user_id, "dsa.problem_analyzed",
            ref_type="dsa_problem", ref_id=problem_id,
        )
    gamify.attach(response, gam)
    return analysis
