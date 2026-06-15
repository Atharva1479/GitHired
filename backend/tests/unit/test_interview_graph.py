"""Unit tests for the LangGraph interview agent.

All LLM calls are mocked — no real Gemini/Ollama/DB needed.
Uses MemorySaver (in-memory checkpointer) for graph state.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from app.services.interview_graph import (
    InterviewState,
    TurnRecord,
    _build_graph,
    decide_next,
    init_graph,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _base_state(**overrides: Any) -> InterviewState:
    """Build a minimal InterviewState dict for testing."""
    base: InterviewState = {
        "session_id": 1,
        "user_id": 99,
        "topic": "Python",
        "role": "Backend Engineer",
        "years_exp": "2",
        "difficulty": "medium",
        "jd_text": None,
        "target_turns": 5,
        "topic_clusters": ["Core", "Async", "Testing"],
        "current_question": "What is a generator?",
        "current_topic_tag": "Core",
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
    base.update(overrides)  # type: ignore[typeddict-unknown-key]
    return base


def _make_turn(score: int, turn_type: str = "primary", depth: int = 0) -> TurnRecord:
    return TurnRecord(
        turn_id=1,
        question="Q?",
        user_answer="A.",
        score=score,
        feedback="ok",
        ideal_answer="ideal",
        turn_type=turn_type,  # type: ignore[typeddict-item]
        followup_depth=depth,
        topic_tag="Core",
    )


# ── decide_next routing logic ─────────────────────────────────────────────────

class TestDecideNext:
    def test_wrap_up_when_primary_hits_target(self) -> None:
        state = _base_state(
            turns=[_make_turn(8)],
            primary_questions_asked=5,
            target_turns=5,
            followup_depth=0,
        )
        assert decide_next(state) == "wrap_up"

    def test_wrap_up_when_total_turns_exceeds_cap(self) -> None:
        turns = [_make_turn(7)] * 10
        state = _base_state(
            turns=turns,
            primary_questions_asked=4,
            target_turns=5,
            followup_depth=0,
        )
        # total >= target + 4 = 9 → wrap_up
        assert decide_next(state) == "wrap_up"

    def test_follow_up_on_low_score_within_depth(self) -> None:
        state = _base_state(
            turns=[_make_turn(3)],
            primary_questions_asked=1,
            target_turns=5,
            followup_depth=0,
        )
        assert decide_next(state) == "follow_up"

    def test_no_follow_up_at_max_depth(self) -> None:
        state = _base_state(
            turns=[_make_turn(2)],
            primary_questions_asked=1,
            target_turns=5,
            followup_depth=2,
        )
        assert decide_next(state) == "next_topic"

    def test_next_topic_on_good_score(self) -> None:
        state = _base_state(
            turns=[_make_turn(8)],
            primary_questions_asked=1,
            target_turns=5,
            followup_depth=0,
        )
        assert decide_next(state) == "next_topic"

    def test_boundary_score_4_triggers_followup(self) -> None:
        state = _base_state(
            turns=[_make_turn(4)],
            primary_questions_asked=1,
            target_turns=5,
            followup_depth=0,
        )
        assert decide_next(state) == "follow_up"

    def test_boundary_score_5_goes_next_topic(self) -> None:
        state = _base_state(
            turns=[_make_turn(5)],
            primary_questions_asked=1,
            target_turns=5,
            followup_depth=0,
        )
        assert decide_next(state) == "next_topic"

    def test_empty_turns_returns_next_topic(self) -> None:
        state = _base_state(turns=[], primary_questions_asked=0, target_turns=5)
        assert decide_next(state) == "next_topic"

    def test_depth_1_still_allows_followup(self) -> None:
        state = _base_state(
            turns=[_make_turn(2)],
            primary_questions_asked=1,
            target_turns=5,
            followup_depth=1,
        )
        assert decide_next(state) == "follow_up"


# ── Difficulty adjustment ─────────────────────────────────────────────────────

class TestDifficultyAdjustment:
    """evaluate_answer should compute difficulty_adjustment based on running avg."""

    @pytest.mark.asyncio
    async def test_high_score_increases_difficulty(self) -> None:
        from app.services.interview_graph import evaluate_answer

        state = _base_state(
            current_question="What is GIL?",
            current_topic_tag="Core",
            followup_depth=0,
            primary_questions_asked=0,
            turns=[],
            topics_covered=[],
            topic_scores={},
            pending_answer="The GIL prevents...",
        )

        mock_eval = {"ideal_answer": "ideal", "score": 9, "feedback": "great"}
        with patch("app.services.interview_graph.evaluate_turn", AsyncMock(return_value=mock_eval)):
            result = await evaluate_answer(state)

        assert result["difficulty_adjustment"] == 1
        assert result["running_avg_score"] == 9.0

    @pytest.mark.asyncio
    async def test_low_score_decreases_difficulty(self) -> None:
        from app.services.interview_graph import evaluate_answer

        state = _base_state(
            current_question="What is GIL?",
            current_topic_tag="Core",
            followup_depth=0,
            primary_questions_asked=0,
            turns=[],
            topics_covered=[],
            topic_scores={},
            pending_answer="I don't know.",
        )

        mock_eval = {"ideal_answer": "ideal", "score": 2, "feedback": "poor"}
        with patch("app.services.interview_graph.evaluate_turn", AsyncMock(return_value=mock_eval)):
            result = await evaluate_answer(state)

        assert result["difficulty_adjustment"] == -1

    @pytest.mark.asyncio
    async def test_medium_score_keeps_difficulty(self) -> None:
        from app.services.interview_graph import evaluate_answer

        state = _base_state(
            current_question="What is GIL?",
            current_topic_tag="Core",
            followup_depth=0,
            primary_questions_asked=0,
            turns=[],
            topics_covered=[],
            topic_scores={},
            pending_answer="The GIL is a mutex...",
        )

        mock_eval = {"ideal_answer": "ideal", "score": 6, "feedback": "ok"}
        with patch("app.services.interview_graph.evaluate_turn", AsyncMock(return_value=mock_eval)):
            result = await evaluate_answer(state)

        assert result["difficulty_adjustment"] == 0


# ── Full graph flow with MemorySaver ──────────────────────────────────────────

MOCK_PLAN = {
    "topic_clusters": ["Core", "Async", "Testing"],
    "opening_question": "Explain Python's GIL.",
    "opening_topic_tag": "Core",
}
MOCK_NEXT_Q = {"question": "What is asyncio?", "topic_tag": "Async"}
MOCK_FOLLOWUP_Q = {"question": "Can you elaborate on the event loop?", "topic_tag": "Async"}
MOCK_EVAL_HIGH = {"ideal_answer": "ideal", "score": 8, "feedback": "good"}
MOCK_EVAL_LOW = {"ideal_answer": "ideal", "score": 3, "feedback": "weak"}
MOCK_REPORT = {
    "overall_score": 75,
    "skill_breakdown": {"Core": 80, "Async": 70},
    "summary": "Solid performance overall.",
}


def _mock_patches():
    """Return a context-manager stack that mocks all LLM calls."""
    return [
        patch("app.services.interview_graph.plan_interview_topics", AsyncMock(return_value=MOCK_PLAN)),
        patch("app.services.interview_graph.generate_next_question", AsyncMock(return_value=MOCK_NEXT_Q)),
        patch("app.services.interview_graph.generate_followup_question", AsyncMock(return_value=MOCK_FOLLOWUP_Q)),
        patch("app.services.interview_graph.evaluate_turn", AsyncMock(return_value=MOCK_EVAL_HIGH)),
        patch("app.services.interview_graph.generate_report", AsyncMock(return_value=MOCK_REPORT)),
    ]


@pytest.fixture
async def graph_with_memory():
    """Build and compile the graph with MemorySaver for unit tests."""
    checkpointer = MemorySaver()
    await init_graph(checkpointer)
    from app.services.interview_graph import compiled_graph
    return compiled_graph


class TestGraphFlow:
    @pytest.mark.asyncio
    async def test_start_returns_first_question(self, graph_with_memory: Any) -> None:
        graph = graph_with_memory
        config = {"configurable": {"thread_id": "test-thread-1"}}
        initial = _base_state(target_turns=2)

        with _mock_patches()[0]:  # only plan_interview is called on first ainvoke
            result = await graph.ainvoke(initial, config)

        assert result["current_question"] == "Explain Python's GIL."
        assert result["topic_clusters"] == ["Core", "Async", "Testing"]
        assert result["interview_complete"] is False

    @pytest.mark.asyncio
    async def test_answer_advances_to_next_question(self, graph_with_memory: Any) -> None:
        graph = graph_with_memory
        config = {"configurable": {"thread_id": "test-thread-2"}}
        initial = _base_state(target_turns=3)

        patches = _mock_patches()
        with patches[0], patches[1], patches[3]:  # plan + next_q + eval
            await graph.ainvoke(initial, config)
            result = await graph.ainvoke(Command(resume="My answer about GIL"), config)

        assert result["current_question"] == "What is asyncio?"
        assert len(result["turns"]) == 1
        assert result["turns"][0]["score"] == 8

    @pytest.mark.asyncio
    async def test_low_score_triggers_followup(self, graph_with_memory: Any) -> None:
        graph = graph_with_memory
        config = {"configurable": {"thread_id": "test-thread-3"}}
        initial = _base_state(target_turns=5)

        low_eval = AsyncMock(return_value=MOCK_EVAL_LOW)
        patches = _mock_patches()
        with patches[0], patches[2], patch("app.services.interview_graph.evaluate_turn", low_eval):
            await graph.ainvoke(initial, config)
            result = await graph.ainvoke(Command(resume="I don't know"), config)

        assert result["current_question"] == "Can you elaborate on the event loop?"
        assert result["followup_depth"] == 1
        assert result["turns"][0]["score"] == 3

    @pytest.mark.asyncio
    async def test_interview_completes_after_target_turns(self, graph_with_memory: Any) -> None:
        graph = graph_with_memory
        config = {"configurable": {"thread_id": "test-thread-4"}}
        # target_turns=1 means after one primary question the interview wraps up
        initial = _base_state(target_turns=1)

        patches = _mock_patches()
        with patches[0], patches[1], patches[3], patches[4]:
            await graph.ainvoke(initial, config)
            result = await graph.ainvoke(Command(resume="My answer"), config)

        assert result["interview_complete"] is True
        assert result["report_data"] is not None
        assert result["report_data"]["overall_score"] == 75

    @pytest.mark.asyncio
    async def test_topics_covered_updates_after_answer(self, graph_with_memory: Any) -> None:
        graph = graph_with_memory
        config = {"configurable": {"thread_id": "test-thread-5"}}
        initial = _base_state(target_turns=3)

        patches = _mock_patches()
        with patches[0], patches[1], patches[3]:
            await graph.ainvoke(initial, config)
            result = await graph.ainvoke(Command(resume="Answer"), config)

        assert "Core" in result["topics_covered"]

    @pytest.mark.asyncio
    async def test_primary_questions_counted_correctly(self, graph_with_memory: Any) -> None:
        graph = graph_with_memory
        config = {"configurable": {"thread_id": "test-thread-6"}}
        initial = _base_state(target_turns=5)

        patches = _mock_patches()
        with patches[0], patches[1], patches[3]:
            await graph.ainvoke(initial, config)
            result = await graph.ainvoke(Command(resume="Answer"), config)

        assert result["primary_questions_asked"] == 1

    @pytest.mark.asyncio
    async def test_followup_does_not_increment_primary_count(self, graph_with_memory: Any) -> None:
        graph = graph_with_memory
        config = {"configurable": {"thread_id": "test-thread-7"}}
        initial = _base_state(target_turns=5)

        low_eval = AsyncMock(return_value=MOCK_EVAL_LOW)
        high_eval = AsyncMock(return_value=MOCK_EVAL_HIGH)

        with _mock_patches()[0], _mock_patches()[2]:
            with patch("app.services.interview_graph.evaluate_turn", low_eval):
                await graph.ainvoke(initial, config)
                result = await graph.ainvoke(Command(resume="Bad answer"), config)

            # Now submit the follow-up answer (should not increment primary count)
            with patch("app.services.interview_graph.evaluate_turn", high_eval):
                with _mock_patches()[1]:  # next_question after followup resolves
                    result = await graph.ainvoke(Command(resume="Better answer"), config)

        # primary_questions_asked should still be 1 (the follow-up doesn't count)
        assert result["primary_questions_asked"] == 1
