"""AI Interview endpoints. Mounted at /api/interview."""
from __future__ import annotations

import asyncio
import contextvars
import uuid

import asyncpg
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from langgraph.types import Command
from pydantic import BaseModel

from app.database import pool
from app.deps import get_db, get_user_id
from app.models import (
    StartAgentSessionRequest,
    StartAgentSessionResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
)
from app.services.interview_ai import (
    evaluate_turn,
    generate_questions,
    generate_report,
)
from app.services import interview_graph as ig
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
            # Acquire a fresh connection — the request-scoped conn is already released.
            # Both writes are in one transaction so a crash can't leave a partial report.
            async with pool().acquire() as bg_conn:
                async with bg_conn.transaction():
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

    # Pass an explicit context copy so structlog request_id/user_id are visible in the task.
    asyncio.create_task(_bg_report(), context=contextvars.copy_context())
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


@router.post("/sessions/agent", response_model=StartAgentSessionResponse, status_code=status.HTTP_201_CREATED)
async def start_agent_session(
    body: StartAgentSessionRequest,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> StartAgentSessionResponse:
    """Start an agentic interview session backed by LangGraph."""
    graph = ig.get_graph()
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    session = await repo.create_agent_session(
        conn, user_id, body.topic, body.role, body.years_exp, body.target_turns, thread_id
    )

    initial_state: dict = {
        "session_id": session.id,
        "user_id": user_id,
        "topic": body.topic,
        "role": body.role,
        "years_exp": body.years_exp,
        "difficulty": body.difficulty,
        "jd_text": body.jd_text,
        "target_turns": body.target_turns,
        "topic_clusters": [],
        "current_question": "",
        "current_topic_tag": "",
        "primary_questions_asked": 0,
        "followup_depth": 0,
        "turns": [],
        "topics_covered": [],
        "topic_scores": {},
        "running_avg_score": 0.0,
        "difficulty_adjustment": 0,
        "last_decision": "",
        "pending_answer": None,
        "interview_complete": False,
        "report_data": None,
    }

    try:
        result = await graph.ainvoke(initial_state, config)
    except Exception as exc:
        log.error("interview.agent_start_failed", session_id=session.id, error=str(exc))
        raise HTTPException(status_code=503, detail="Agent initialization failed. Try again.")

    return StartAgentSessionResponse(
        session_id=session.id,
        thread_id=thread_id,
        first_question=result.get("current_question", ""),
        topic_clusters=result.get("topic_clusters", []),
        target_turns=body.target_turns,
    )


@router.post("/sessions/{session_id}/answer", response_model=SubmitAnswerResponse)
async def submit_agent_answer(
    session_id: int,
    body: SubmitAnswerRequest,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> SubmitAnswerResponse:
    """Submit an answer to the current question and receive the next one."""
    graph = ig.get_graph()

    session = await repo.get_session(conn, session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.agent_mode or not session.agent_thread_id:
        raise HTTPException(status_code=400, detail="Not an agent-mode session")
    if session.status != "active":
        raise HTTPException(status_code=400, detail="Session already ended")

    config = {"configurable": {"thread_id": session.agent_thread_id}}

    try:
        result = await graph.ainvoke(Command(resume=body.answer), config)
    except Exception as exc:
        log.error("interview.agent_answer_failed", session_id=session_id, error=str(exc))
        raise HTTPException(status_code=503, detail="Agent processing failed. Try again.")

    interview_complete = result.get("interview_complete", False)
    turns: list = result.get("turns", [])
    question_number = len(turns) + 1

    # If a new turn was completed, persist it to DB
    if turns:
        last_turn = turns[-1]
        if last_turn.get("turn_id") == -1:
            # This turn hasn't been saved yet — determine parent_turn_id for follow-ups
            parent_id = None
            if last_turn.get("turn_type") == "followup" and len(turns) >= 2:
                # Parent is the previous primary turn
                for t in reversed(turns[:-1]):
                    if t.get("turn_type") == "primary":
                        parent_id = t.get("turn_id") if t.get("turn_id") != -1 else None
                        break

            saved = await repo.save_agent_turn(
                conn,
                session_id=session_id,
                question_index=len(turns) - 1,
                question=last_turn["question"],
                user_answer=last_turn["user_answer"],
                score=last_turn["score"],
                feedback=last_turn["feedback"],
                ideal_answer=last_turn.get("ideal_answer", ""),
                turn_type=last_turn.get("turn_type", "primary"),
                followup_depth=last_turn.get("followup_depth", 0),
                parent_turn_id=parent_id,
                agent_decision=result.get("last_decision"),
            )
            # Update the turn_id in the checkpoint (best-effort; non-fatal)
            turns[-1]["turn_id"] = saved.id

    if interview_complete:
        await repo.end_session(conn, session_id)
        report_data = result.get("report_data")
        if report_data:
            async with pool().acquire() as bg_conn:
                await repo.save_report(
                    bg_conn, session_id,
                    report_data.get("overall_score", 0),
                    report_data.get("skill_breakdown", {}),
                    report_data.get("summary", ""),
                )
        return SubmitAnswerResponse(
            next_question=None,
            question_number=question_number,
            followup_depth=0,
            interview_complete=True,
            agent_status="done",
        )

    followup_depth = result.get("followup_depth", 0)
    last_decision = result.get("last_decision", "")
    agent_status = "wrapping_up" if last_decision == "wrap_up" else "asking"

    return SubmitAnswerResponse(
        next_question=result.get("current_question"),
        question_number=question_number,
        followup_depth=followup_depth,
        interview_complete=False,
        agent_status=agent_status,
    )


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
