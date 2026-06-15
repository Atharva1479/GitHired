"""Tests for the LangGraph agent interview router endpoints.

All LLM calls and DB interactions are mocked.
The graph itself is replaced with a mock so these tests are pure unit tests
of the router logic (auth, validation, DB writes, response shape).
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import InterviewSession


@pytest.fixture(autouse=True)
def _mock_pg_checkpointer():
    """Prevent the real AsyncPostgresSaver from connecting during TestClient startup.

    On Windows, psycopg async mode requires SelectorEventLoop but pytest/TestClient
    uses ProactorEventLoop. We stub the context manager so it yields a no-op
    MagicMock, allowing the lifespan to complete without a real DB connection.
    """
    mock_checkpointer = MagicMock()
    mock_checkpointer.setup = AsyncMock()

    @asynccontextmanager
    async def _fake_from_conn_string(*args: Any, **kwargs: Any):
        yield mock_checkpointer

    with patch(
        "app.main.AsyncPostgresSaver.from_conn_string",
        side_effect=_fake_from_conn_string,
    ):
        yield


# ── Shared fixtures ───────────────────────────────────────────────────────────

SESSION_ID = 9001


def _make_session(agent_mode: bool = True, thread_id: str | None = None, status: str = "active") -> InterviewSession:
    return InterviewSession(
        id=SESSION_ID,
        user_id=99,
        topic="Python",
        role="Backend Engineer",
        years_exp="2",
        duration_min=0,
        total_questions=5,
        status=status,
        created_at=datetime(2026, 6, 15, 10, 0, 0),
        agent_mode=agent_mode,
        agent_thread_id=thread_id or "test-thread-abc",
    )


# Graph state returned after first ainvoke (graph paused at first interrupt)
INITIAL_GRAPH_STATE = {
    "session_id": SESSION_ID,
    "user_id": 99,
    "topic": "Python",
    "current_question": "Explain the GIL.",
    "current_topic_tag": "Core",
    "topic_clusters": ["Core", "Async"],
    "primary_questions_asked": 0,
    "followup_depth": 0,
    "turns": [],
    "topics_covered": [],
    "topic_scores": {},
    "running_avg_score": 0.0,
    "difficulty_adjustment": 0,
    "last_decision": "start",
    "pending_answer": None,
    "interview_complete": False,
    "report_data": None,
    "target_turns": 5,
}

# Graph state after first answer (graph paused at second interrupt)
AFTER_ANSWER_STATE = {
    **INITIAL_GRAPH_STATE,
    "current_question": "What is asyncio?",
    "current_topic_tag": "Async",
    "primary_questions_asked": 1,
    "followup_depth": 0,
    "turns": [
        {
            "turn_id": -1,
            "question": "Explain the GIL.",
            "user_answer": "GIL is a mutex...",
            "score": 8,
            "feedback": "good",
            "ideal_answer": "ideal",
            "turn_type": "primary",
            "followup_depth": 0,
            "topic_tag": "Core",
        }
    ],
    "topics_covered": ["Core"],
    "topic_scores": {"Core": [8]},
    "running_avg_score": 8.0,
    "last_decision": "next_topic",
}

COMPLETED_STATE = {
    **AFTER_ANSWER_STATE,
    "interview_complete": True,
    "report_data": {
        "overall_score": 80,
        "skill_breakdown": {"Core": 80},
        "summary": "Good.",
    },
}

FOLLOWUP_STATE = {
    **INITIAL_GRAPH_STATE,
    "current_question": "Can you go deeper on the event loop?",
    "current_topic_tag": "Core",
    "primary_questions_asked": 1,
    "followup_depth": 1,
    "turns": [
        {
            "turn_id": -1,
            "question": "Explain the GIL.",
            "user_answer": "I don't know.",
            "score": 3,
            "feedback": "weak",
            "ideal_answer": "ideal",
            "turn_type": "primary",
            "followup_depth": 0,
            "topic_tag": "Core",
        }
    ],
    "topics_covered": ["Core"],
    "topic_scores": {"Core": [3]},
    "running_avg_score": 3.0,
    "last_decision": "follow_up",
}


# ── POST /api/interview/sessions/agent ───────────────────────────────────────

class TestStartAgentSession:
    def test_returns_first_question(self) -> None:
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value=INITIAL_GRAPH_STATE)

        mock_session = _make_session()

        with (
            patch("app.routers.interview.ig.get_graph", return_value=mock_graph),
            patch("app.routers.interview.repo.create_agent_session", AsyncMock(return_value=mock_session)),
            patch("app.routers.interview.uuid.uuid4", return_value=uuid.UUID("00000000-0000-0000-0000-000000000001")),
        ):
            with TestClient(app) as client:
                r = client.post("/api/interview/sessions/agent", json={
                    "topic": "Python",
                    "role": "Backend Engineer",
                    "years_exp": "2",
                    "difficulty": "medium",
                    "target_turns": 5,
                })

        assert r.status_code == 201
        body = r.json()
        assert body["session_id"] == SESSION_ID
        assert body["first_question"] == "Explain the GIL."
        assert body["topic_clusters"] == ["Core", "Async"]
        assert body["agent_mode"] is True
        assert body["thread_id"] == "00000000-0000-0000-0000-000000000001"

    def test_503_when_graph_raises(self) -> None:
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(side_effect=RuntimeError("LLM unavailable"))

        mock_session = _make_session()

        with (
            patch("app.routers.interview.ig.get_graph", return_value=mock_graph),
            patch("app.routers.interview.repo.create_agent_session", AsyncMock(return_value=mock_session)),
        ):
            with TestClient(app) as client:
                r = client.post("/api/interview/sessions/agent", json={
                    "topic": "Python",
                    "role": "Backend Engineer",
                    "years_exp": "2",
                    "difficulty": "medium",
                    "target_turns": 5,
                })

        assert r.status_code == 503

    def test_validation_rejects_empty_topic(self) -> None:
        with TestClient(app) as client:
            r = client.post("/api/interview/sessions/agent", json={
                "topic": "",
                "role": "Backend Engineer",
                "years_exp": "2",
                "difficulty": "medium",
                "target_turns": 5,
            })
        assert r.status_code == 422

    def test_validation_rejects_too_many_turns(self) -> None:
        with TestClient(app) as client:
            r = client.post("/api/interview/sessions/agent", json={
                "topic": "Python",
                "role": "Engineer",
                "years_exp": "1",
                "difficulty": "medium",
                "target_turns": 99,  # max is 20
            })
        assert r.status_code == 422


# ── POST /api/interview/sessions/{id}/answer ─────────────────────────────────

class TestSubmitAgentAnswer:
    def test_returns_next_question(self) -> None:
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value=AFTER_ANSWER_STATE)

        mock_session = _make_session()
        mock_turn = MagicMock()
        mock_turn.id = 42

        with (
            patch("app.routers.interview.ig.get_graph", return_value=mock_graph),
            patch("app.routers.interview.repo.get_session", AsyncMock(return_value=mock_session)),
            patch("app.routers.interview.repo.save_agent_turn", AsyncMock(return_value=mock_turn)),
        ):
            with TestClient(app) as client:
                r = client.post(f"/api/interview/sessions/{SESSION_ID}/answer", json={"answer": "GIL is a mutex..."})

        assert r.status_code == 200
        body = r.json()
        assert body["next_question"] == "What is asyncio?"
        assert body["interview_complete"] is False
        assert body["followup_depth"] == 0
        assert body["agent_status"] == "asking"
        assert body["question_number"] == 2

    def test_returns_follow_up(self) -> None:
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value=FOLLOWUP_STATE)

        mock_session = _make_session()
        mock_turn = MagicMock()
        mock_turn.id = 43

        with (
            patch("app.routers.interview.ig.get_graph", return_value=mock_graph),
            patch("app.routers.interview.repo.get_session", AsyncMock(return_value=mock_session)),
            patch("app.routers.interview.repo.save_agent_turn", AsyncMock(return_value=mock_turn)),
        ):
            with TestClient(app) as client:
                r = client.post(f"/api/interview/sessions/{SESSION_ID}/answer", json={"answer": "I don't know."})

        assert r.status_code == 200
        body = r.json()
        assert body["followup_depth"] == 1
        assert body["interview_complete"] is False
        assert body["next_question"] == "Can you go deeper on the event loop?"

    def test_returns_complete_when_interview_done(self) -> None:
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value=COMPLETED_STATE)

        mock_session = _make_session()
        mock_turn = MagicMock()
        mock_turn.id = 44

        with (
            patch("app.routers.interview.ig.get_graph", return_value=mock_graph),
            patch("app.routers.interview.repo.get_session", AsyncMock(return_value=mock_session)),
            patch("app.routers.interview.repo.save_agent_turn", AsyncMock(return_value=mock_turn)),
            patch("app.routers.interview.repo.end_session", AsyncMock()),
            patch("app.routers.interview.repo.save_report", AsyncMock()),
            patch("app.routers.interview.pool") as mock_pool,
        ):
            mock_pool.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_pool.return_value.__aexit__ = AsyncMock(return_value=None)
            with TestClient(app) as client:
                r = client.post(f"/api/interview/sessions/{SESSION_ID}/answer", json={"answer": "Final answer"})

        assert r.status_code == 200
        body = r.json()
        assert body["interview_complete"] is True
        assert body["next_question"] is None
        assert body["agent_status"] == "done"

    def test_404_for_unknown_session(self) -> None:
        mock_graph = MagicMock()
        with (
            patch("app.routers.interview.ig.get_graph", return_value=mock_graph),
            patch("app.routers.interview.repo.get_session", AsyncMock(return_value=None)),
        ):
            with TestClient(app) as client:
                r = client.post("/api/interview/sessions/9999/answer", json={"answer": "test"})

        assert r.status_code == 404

    def test_400_for_non_agent_session(self) -> None:
        mock_graph = MagicMock()
        non_agent_session = _make_session(agent_mode=False)

        with (
            patch("app.routers.interview.ig.get_graph", return_value=mock_graph),
            patch("app.routers.interview.repo.get_session", AsyncMock(return_value=non_agent_session)),
        ):
            with TestClient(app) as client:
                r = client.post(f"/api/interview/sessions/{SESSION_ID}/answer", json={"answer": "test"})

        assert r.status_code == 400
        assert "agent-mode" in r.json()["detail"]

    def test_400_for_already_ended_session(self) -> None:
        mock_graph = MagicMock()
        ended_session = _make_session(status="ended")

        with (
            patch("app.routers.interview.ig.get_graph", return_value=mock_graph),
            patch("app.routers.interview.repo.get_session", AsyncMock(return_value=ended_session)),
        ):
            with TestClient(app) as client:
                r = client.post(f"/api/interview/sessions/{SESSION_ID}/answer", json={"answer": "test"})

        assert r.status_code == 400

    def test_503_when_graph_raises(self) -> None:
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(side_effect=RuntimeError("graph error"))

        mock_session = _make_session()

        with (
            patch("app.routers.interview.ig.get_graph", return_value=mock_graph),
            patch("app.routers.interview.repo.get_session", AsyncMock(return_value=mock_session)),
        ):
            with TestClient(app) as client:
                r = client.post(f"/api/interview/sessions/{SESSION_ID}/answer", json={"answer": "test"})

        assert r.status_code == 503
