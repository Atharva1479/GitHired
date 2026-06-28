"""Interview repository — CRUD for the four interview tables."""
from __future__ import annotations

import json
from typing import Any

import asyncpg

from app.models import (
    InterviewQuestionReport,
    InterviewReport,
    InterviewSession,
    InterviewTurn,
)


async def create_agent_session(
    conn: asyncpg.Connection,
    user_id: int,
    topic: str,
    role: str,
    years_exp: str,
    target_turns: int,
    thread_id: str,
) -> InterviewSession:
    """Create an interview session in agent mode with a LangGraph thread_id."""
    row = await conn.fetchrow(
        """
        INSERT INTO interview_sessions
            (user_id, topic, role, years_exp, duration_min, total_questions, agent_mode, agent_thread_id)
        VALUES ($1, $2, $3, $4, 0, $5, true, $6)
        RETURNING *
        """,
        user_id, topic, role, years_exp, target_turns, thread_id,
    )
    return InterviewSession.model_validate(dict(row))


async def save_agent_turn(
    conn: asyncpg.Connection,
    session_id: int,
    question_index: int,
    question: str,
    user_answer: str,
    score: int,
    feedback: str,
    ideal_answer: str,
    turn_type: str,
    followup_depth: int,
    parent_turn_id: int | None,
    agent_decision: str | None,
    model_name: str | None = None,
    latency_ms: int = 0,
) -> InterviewTurn:
    """Save a turn produced by the LangGraph agent."""
    row = await conn.fetchrow(
        """
        INSERT INTO interview_turns
            (session_id, question_index, question, user_answer,
             turn_type, followup_depth, parent_turn_id, agent_decision,
             model_name, latency_ms)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        RETURNING *
        """,
        session_id, question_index, question, user_answer,
        turn_type, followup_depth, parent_turn_id, agent_decision,
        model_name or None, latency_ms,
    )
    # Also write to question_reports for unified report queries
    await conn.execute(
        """
        INSERT INTO interview_question_reports
            (session_id, question_index, question, user_answer, ideal_answer,
             score, feedback, model_name, latency_ms)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """,
        session_id, question_index, question, user_answer, ideal_answer,
        score, feedback, model_name or None, latency_ms,
    )
    return InterviewTurn.model_validate(dict(row))


async def create_session(
    conn: asyncpg.Connection,
    user_id: int,
    topic: str,
    role: str,
    years_exp: str,
    duration_min: int,
    total_questions: int,
) -> InterviewSession:
    row = await conn.fetchrow(
        """
        INSERT INTO interview_sessions
            (user_id, topic, role, years_exp, duration_min, total_questions)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING *
        """,
        user_id, topic, role, years_exp, duration_min, total_questions,
    )
    return InterviewSession.model_validate(dict(row))


async def get_session(
    conn: asyncpg.Connection,
    session_id: int,
    user_id: int,
) -> InterviewSession | None:
    row = await conn.fetchrow(
        "SELECT * FROM interview_sessions WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL",
        session_id, user_id,
    )
    return InterviewSession.model_validate(dict(row)) if row else None


async def save_turn(
    conn: asyncpg.Connection,
    session_id: int,
    question_index: int,
    question: str,
    user_answer: str,
) -> InterviewTurn:
    row = await conn.fetchrow(
        """
        INSERT INTO interview_turns (session_id, question_index, question, user_answer)
        VALUES ($1, $2, $3, $4)
        RETURNING *
        """,
        session_id, question_index, question, user_answer,
    )
    return InterviewTurn.model_validate(dict(row))


async def end_session(conn: asyncpg.Connection, session_id: int) -> None:
    await conn.execute(
        "UPDATE interview_sessions SET status = 'ended', ended_at = now() WHERE id = $1 AND deleted_at IS NULL",
        session_id,
    )


async def get_turns(
    conn: asyncpg.Connection,
    session_id: int,
) -> list[InterviewTurn]:
    rows = await conn.fetch(
        "SELECT * FROM interview_turns WHERE session_id = $1 ORDER BY question_index",
        session_id,
    )
    return [InterviewTurn.model_validate(dict(r)) for r in rows]


async def save_question_reports(
    conn: asyncpg.Connection,
    session_id: int,
    items: list[dict[str, Any]],
) -> None:
    await conn.executemany(
        """
        INSERT INTO interview_question_reports
            (session_id, question_index, question, user_answer, ideal_answer,
             score, feedback, model_name, latency_ms)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """,
        [
            (
                session_id,
                i["question_index"],
                i["question"],
                i["user_answer"],
                i["ideal_answer"],
                i["score"],
                i["feedback"],
                i.get("model") or None,
                i.get("latency_ms", 0),
            )
            for i in items
        ],
    )


async def save_report(
    conn: asyncpg.Connection,
    session_id: int,
    overall_score: int,
    skill_breakdown: dict[str, Any],
    summary: str,
) -> InterviewReport:
    row = await conn.fetchrow(
        """
        INSERT INTO interview_reports (session_id, overall_score, skill_breakdown, summary)
        VALUES ($1, $2, $3, $4)
        RETURNING *
        """,
        session_id, overall_score, json.dumps(skill_breakdown), summary,
    )
    r = dict(row)
    if isinstance(r.get("skill_breakdown"), str):
        r["skill_breakdown"] = json.loads(r["skill_breakdown"])
    return InterviewReport.model_validate(r)


async def get_report(
    conn: asyncpg.Connection,
    session_id: int,
) -> InterviewReport | None:
    row = await conn.fetchrow(
        "SELECT * FROM interview_reports WHERE session_id = $1",
        session_id,
    )
    if not row:
        return None
    r = dict(row)
    if isinstance(r.get("skill_breakdown"), str):
        r["skill_breakdown"] = json.loads(r["skill_breakdown"])
    return InterviewReport.model_validate(r)


async def get_question_reports(
    conn: asyncpg.Connection,
    session_id: int,
) -> list[InterviewQuestionReport]:
    rows = await conn.fetch(
        "SELECT * FROM interview_question_reports WHERE session_id = $1 ORDER BY question_index",
        session_id,
    )
    return [InterviewQuestionReport.model_validate(dict(r)) for r in rows]


async def soft_delete_session(
    conn: asyncpg.Connection,
    session_id: int,
    user_id: int,
) -> bool:
    result = await conn.execute(
        "UPDATE interview_sessions SET deleted_at = now() WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL",
        session_id, user_id,
    )
    return result == "UPDATE 1"


async def list_sessions(
    conn: asyncpg.Connection,
    user_id: int,
) -> list[InterviewSession]:
    rows = await conn.fetch(
        "SELECT * FROM interview_sessions WHERE user_id = $1 AND deleted_at IS NULL ORDER BY created_at DESC",
        user_id,
    )
    return [InterviewSession.model_validate(dict(r)) for r in rows]
