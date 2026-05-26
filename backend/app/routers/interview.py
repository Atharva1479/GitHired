"""AI Interview endpoints. Mounted at /api/interview."""
from __future__ import annotations

import asyncio

import asyncpg
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.database import pool
from app.deps import get_db, get_user_id
from app.services.interview_ai import (
    evaluate_turn,
    generate_questions,
    generate_report,
)
from app.repositories import interview as repo

log = structlog.get_logger("interview_router")
router = APIRouter()


class StartSessionRequest(BaseModel):
    topic: str
    role: str
    years_exp: str
    num_questions: int = 7
    difficulty: str = "medium"
    jd_text: str | None = None
    custom_questions: list[str] | None = None

    @property
    def duration_min(self) -> int:
        return 30 if self.num_questions <= 7 else 60


class StartSessionResponse(BaseModel):
    session_id: int
    questions: list[str]
    total_questions: int


@router.post("/sessions", response_model=StartSessionResponse, status_code=status.HTTP_201_CREATED)
async def start_session(
    body: StartSessionRequest,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> StartSessionResponse:
    if body.custom_questions:
        questions = [q.strip() for q in body.custom_questions if q.strip()]
        if not questions:
            raise HTTPException(status_code=400, detail="No valid custom questions provided")
    else:
        try:
            questions = await generate_questions(
                body.topic, body.role, body.years_exp,
                body.num_questions, body.difficulty, body.jd_text,
            )
        except Exception as exc:
            log.warning("interview.generate_questions_failed", error=str(exc))
            raise HTTPException(status_code=503, detail="AI question generation unavailable. Try again.")
    total = len(questions)
    session = await repo.create_session(
        conn, user_id, body.topic, body.role, body.years_exp, body.duration_min, total
    )
    return StartSessionResponse(
        session_id=session.id,
        questions=questions,
        total_questions=total,
    )


class SubmitTurnRequest(BaseModel):
    question_index: int
    question: str
    user_answer: str


@router.post("/sessions/{session_id}/turns")
async def submit_turn(
    session_id: int,
    body: SubmitTurnRequest,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> JSONResponse:
    session = await repo.get_session(conn, session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "active":
        raise HTTPException(status_code=400, detail="Session already ended")
    await repo.save_turn(conn, session_id, body.question_index, body.question, body.user_answer)
    return JSONResponse({"ok": True})


@router.post("/sessions/{session_id}/end")
async def end_session(
    session_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> JSONResponse:
    session = await repo.get_session(conn, session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "active":
        return JSONResponse({"ok": True, "session_id": session_id})

    turns = await repo.get_turns(conn, session_id)
    await repo.end_session(conn, session_id)

    async def _bg_report() -> None:
        try:
            evals: list[dict] = []
            for t in turns:
                ev = await evaluate_turn(session.topic, session.role, t.question, t.user_answer)
                evals.append({
                    "question_index": t.question_index,
                    "question": t.question,
                    "user_answer": t.user_answer,
                    **ev,
                })
            rpt = await generate_report(session.topic, session.role, evals)
            # Acquire a fresh connection — the request-scoped conn is already released
            async with pool().acquire() as bg_conn:
                await repo.save_question_reports(bg_conn, session_id, evals)
                await repo.save_report(
                    bg_conn, session_id,
                    rpt["overall_score"],
                    rpt["skill_breakdown"],
                    rpt["summary"],
                )
            log.info("interview.report_generated", session_id=session_id)
        except Exception as exc:
            log.error("interview.report_bg_failed", session_id=session_id, error=str(exc))

    asyncio.create_task(_bg_report())
    return JSONResponse({"ok": True, "session_id": session_id})


@router.get("/sessions/{session_id}/report")
async def get_report(
    session_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> JSONResponse:
    session = await repo.get_session(conn, session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    report = await repo.get_report(conn, session_id)
    if not report:
        return JSONResponse({"status": "pending"}, status_code=202)

    question_reports = await repo.get_question_reports(conn, session_id)
    return JSONResponse({
        "status": "ready",
        "session": {
            "id": session.id,
            "topic": session.topic,
            "role": session.role,
            "years_exp": session.years_exp,
            "duration_min": session.duration_min,
            "created_at": session.created_at.isoformat(),
        },
        "overall_score": report.overall_score,
        "skill_breakdown": report.skill_breakdown,
        "summary": report.summary,
        "questions": [
            {
                "question_index": qr.question_index,
                "question": qr.question,
                "user_answer": qr.user_answer,
                "ideal_answer": qr.ideal_answer,
                "score": qr.score,
                "feedback": qr.feedback,
            }
            for qr in question_reports
        ],
    })


@router.delete("/sessions/{session_id}", status_code=status.HTTP_200_OK)
async def delete_session(
    session_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> JSONResponse:
    deleted = await repo.soft_delete_session(conn, session_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return JSONResponse({"ok": True})


@router.get("/history")
async def get_history(
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> JSONResponse:
    sessions = await repo.list_sessions(conn, user_id)
    return JSONResponse([
        {
            "id": s.id,
            "topic": s.topic,
            "role": s.role,
            "years_exp": s.years_exp,
            "duration_min": s.duration_min,
            "status": s.status,
            "created_at": s.created_at.isoformat(),
        }
        for s in sessions
    ])
