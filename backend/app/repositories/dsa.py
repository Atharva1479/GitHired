"""DSA Progress Tracker — repository layer.

Provides CRUD for ``dsa_problems`` and ``dsa_analyses``, plus aggregated
stats with streak calculation. All rows are scoped by ``user_id``.
Soft-delete is used for problems (``deleted_at``); analyses are never
deleted (they are immutable audit records tied to a problem).
"""
from __future__ import annotations

import asyncpg

from app.exceptions import NotFound
from app.models import (
    DsaAnalysisOut,
    DsaDifficulty,
    DsaProblemCreate,
    DsaProblemOut,
    DsaProblemUpdate,
    DsaStatsOut,
    DsaTopicStats,
)

_PROBLEM_COLS = (
    "id, user_id, topic, difficulty, title, source_url, description, "
    "user_solution, solved_at, created_at, last_updated, deleted_at"
)

_ANALYSIS_COLS = (
    "id, problem_id, user_id, time_complexity, space_complexity, "
    "approach_summary, feedback, optimized_solution, optimized_explanation, "
    "dry_run_explanation, model, created_at"
)

_ALLOWED_DSA_UPDATE_COLS = frozenset({
    "topic", "difficulty", "title", "source_url", "description", "user_solution",
})


# ──────────────────────────  helpers  ────────────────────────────────


def _row_to_problem(
    row: asyncpg.Record,
    analysis: DsaAnalysisOut | None = None,
) -> DsaProblemOut:
    return DsaProblemOut.model_validate({**dict(row), "analysis": analysis})


def _row_to_analysis(row: asyncpg.Record) -> DsaAnalysisOut:
    return DsaAnalysisOut.model_validate(dict(row))


# ──────────────────────────  problems  ───────────────────────────────


async def list_problems(
    conn: asyncpg.Connection,
    user_id: int,
    topic: str | None = None,
) -> list[DsaProblemOut]:
    """Return all non-deleted problems for *user_id*, newest first.

    Attaches the latest analysis for each problem (if any) using
    DISTINCT ON so we get exactly one analysis row per problem_id.
    """
    # Fetch problems.
    if topic is not None:
        problem_rows = await conn.fetch(
            f"SELECT {_PROBLEM_COLS} FROM dsa_problems "
            "WHERE user_id = $1 AND deleted_at IS NULL AND topic = $2 "
            "ORDER BY solved_at DESC, id DESC",
            user_id, topic,
        )
    else:
        problem_rows = await conn.fetch(
            f"SELECT {_PROBLEM_COLS} FROM dsa_problems "
            "WHERE user_id = $1 AND deleted_at IS NULL "
            "ORDER BY solved_at DESC, id DESC",
            user_id,
        )

    if not problem_rows:
        return []

    problem_ids = [r["id"] for r in problem_rows]

    # Fetch latest analysis per problem using DISTINCT ON.
    analysis_rows = await conn.fetch(
        f"""
        SELECT DISTINCT ON (problem_id) {_ANALYSIS_COLS}
        FROM dsa_analyses
        WHERE problem_id = ANY($1::int[]) AND user_id = $2
        ORDER BY problem_id, created_at DESC
        """,
        problem_ids, user_id,
    )

    analysis_by_problem: dict[int, DsaAnalysisOut] = {
        r["problem_id"]: _row_to_analysis(r) for r in analysis_rows
    }

    return [
        _row_to_problem(r, analysis_by_problem.get(int(r["id"])))
        for r in problem_rows
    ]


async def get_problem(
    conn: asyncpg.Connection,
    problem_id: int,
    user_id: int,
) -> DsaProblemOut:
    """Fetch a single problem with its latest analysis; raise NotFound if missing."""
    row = await conn.fetchrow(
        f"SELECT {_PROBLEM_COLS} FROM dsa_problems "
        "WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL",
        problem_id, user_id,
    )
    if not row:
        raise NotFound(f"dsa_problem id={problem_id}")

    analysis_row = await conn.fetchrow(
        f"""
        SELECT {_ANALYSIS_COLS}
        FROM dsa_analyses
        WHERE problem_id = $1 AND user_id = $2
        ORDER BY created_at DESC
        LIMIT 1
        """,
        problem_id, user_id,
    )
    analysis = _row_to_analysis(analysis_row) if analysis_row else None
    return _row_to_problem(row, analysis)


async def create_problem(
    conn: asyncpg.Connection,
    user_id: int,
    data: DsaProblemCreate,
) -> DsaProblemOut:
    """Insert a new problem and return it (no analysis yet)."""
    row = await conn.fetchrow(
        f"""
        INSERT INTO dsa_problems
            (user_id, topic, difficulty, title, source_url, description,
             user_solution, solved_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
        RETURNING {_PROBLEM_COLS}
        """,
        user_id,
        data.topic,
        data.difficulty.value,
        data.title,
        data.source_url,
        data.description,
        data.user_solution,
    )
    return _row_to_problem(row)


async def update_problem(
    conn: asyncpg.Connection,
    problem_id: int,
    user_id: int,
    data: DsaProblemUpdate,
) -> DsaProblemOut:
    """Partially update a problem; raise NotFound if no rows updated."""
    fields = data.model_dump(exclude_unset=True)
    if not fields:
        # Nothing to change — return current state with latest analysis.
        return await get_problem(conn, problem_id, user_id)
    # Handle enum serialization
    if "difficulty" in fields and isinstance(fields.get("difficulty"), DsaDifficulty):
        fields["difficulty"] = fields["difficulty"].value
    for key in fields:
        if key not in _ALLOWED_DSA_UPDATE_COLS:
            raise ValueError(f"Unexpected column: {key}")
    sets = [f"{k} = ${i + 1}" for i, k in enumerate(fields)]
    args: list[object] = list(fields.values())
    sets.append("last_updated = NOW()")
    args.extend([problem_id, user_id])

    row = await conn.fetchrow(
        f"UPDATE dsa_problems SET {', '.join(sets)} "
        f"WHERE id = ${len(args) - 1} AND user_id = ${len(args)} "
        f"AND deleted_at IS NULL RETURNING {_PROBLEM_COLS}",
        *args,
    )
    if not row:
        raise NotFound(f"dsa_problem id={problem_id}")

    # Attach latest analysis.
    analysis_row = await conn.fetchrow(
        f"""
        SELECT {_ANALYSIS_COLS}
        FROM dsa_analyses
        WHERE problem_id = $1 AND user_id = $2
        ORDER BY created_at DESC
        LIMIT 1
        """,
        problem_id, user_id,
    )
    analysis = _row_to_analysis(analysis_row) if analysis_row else None
    return _row_to_problem(row, analysis)


async def soft_delete_problem(
    conn: asyncpg.Connection,
    problem_id: int,
    user_id: int,
) -> None:
    """Soft-delete a problem by setting deleted_at=NOW()."""
    result = await conn.execute(
        "UPDATE dsa_problems SET deleted_at = NOW() "
        "WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL",
        problem_id, user_id,
    )
    if result.endswith(" 0"):
        raise NotFound(f"dsa_problem id={problem_id}")


# ──────────────────────────  analyses  ───────────────────────────────


async def create_analysis(
    conn: asyncpg.Connection,
    problem_id: int,
    user_id: int,
    time_complexity: str,
    space_complexity: str,
    approach_summary: str,
    feedback: str,
    optimized_solution: str,
    optimized_explanation: str,
    dry_run_explanation: str,
    model: str = "gemini",
) -> DsaAnalysisOut:
    """Insert a new AI analysis record for a problem and return it."""
    row = await conn.fetchrow(
        "SELECT id FROM dsa_problems WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL",
        problem_id, user_id,
    )
    if not row:
        raise NotFound(f"dsa_problem id={problem_id}")
    row = await conn.fetchrow(
        f"""
        INSERT INTO dsa_analyses
            (problem_id, user_id, time_complexity, space_complexity,
             approach_summary, feedback, optimized_solution, optimized_explanation,
             dry_run_explanation, model)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        RETURNING {_ANALYSIS_COLS}
        """,
        problem_id,
        user_id,
        time_complexity,
        space_complexity,
        approach_summary,
        feedback,
        optimized_solution,
        optimized_explanation,
        dry_run_explanation,
        model,
    )
    return _row_to_analysis(row)


# ──────────────────────────  stats  ──────────────────────────────────


async def get_stats(
    conn: asyncpg.Connection,
    user_id: int,
) -> DsaStatsOut:
    """Aggregate stats: total solved, by difficulty, per topic, streak."""
    # Total solved + by difficulty.
    diff_rows = await conn.fetch(
        """
        SELECT difficulty, COUNT(*) AS cnt
        FROM dsa_problems
        WHERE user_id = $1 AND deleted_at IS NULL
        GROUP BY difficulty
        """,
        user_id,
    )
    by_difficulty: dict[str, int] = {r["difficulty"]: int(r["cnt"]) for r in diff_rows}
    total_solved = sum(by_difficulty.values())

    # Per-topic counts + analyzed count.
    topic_rows = await conn.fetch(
        """
        SELECT
            p.topic,
            COUNT(DISTINCT p.id) AS cnt,
            COUNT(DISTINCT p.id) FILTER (WHERE a.id IS NOT NULL) AS analyzed
        FROM dsa_problems p
        LEFT JOIN dsa_analyses a ON a.problem_id = p.id AND a.user_id = p.user_id
        WHERE p.user_id = $1 AND p.deleted_at IS NULL
        GROUP BY p.topic
        ORDER BY cnt DESC
        """,
        user_id,
    )
    topics = [
        DsaTopicStats(
            topic=r["topic"],
            count=int(r["cnt"]),
            analyzed=int(r["analyzed"]),
        )
        for r in topic_rows
    ]

    # Total problems that have at least one analysis.
    analyzed_count: int = await conn.fetchval(
        """
        SELECT COUNT(DISTINCT problem_id)
        FROM dsa_analyses
        WHERE user_id = $1
        """,
        user_id,
    ) or 0

    # Streak: consecutive days (ending today) where the user solved ≥1 problem.
    streak_days: int = await conn.fetchval(
        """
        WITH daily AS (
            SELECT DISTINCT DATE(solved_at AT TIME ZONE 'UTC') AS d
            FROM dsa_problems
            WHERE user_id = $1 AND deleted_at IS NULL
        ),
        numbered AS (
            SELECT d, ROW_NUMBER() OVER (ORDER BY d DESC) AS rn FROM daily
        )
        SELECT COUNT(*)
        FROM numbered
        WHERE d = (CURRENT_DATE - (rn - 1) * INTERVAL '1 day')::date
        """,
        user_id,
    ) or 0

    return DsaStatsOut(
        total_solved=total_solved,
        by_difficulty=by_difficulty,
        topics=topics,
        analyzed_count=analyzed_count,
        streak_days=int(streak_days),
    )


__all__ = [
    "list_problems",
    "get_problem",
    "create_problem",
    "update_problem",
    "soft_delete_problem",
    "create_analysis",
    "get_stats",
]
