"""LangGraph agentic interview system.

StateGraph that:
  - Dynamically generates questions based on coverage + scores
  - Asks follow-ups on weak answers (up to depth 2)
  - Adapts difficulty in real-time
  - Persists state across HTTP requests via PostgreSQL checkpointing
  - Uses interrupt() for human-in-the-loop (graph pauses waiting for user answer)

Public API:
  init_graph(checkpointer)  — compile graph at startup
  compiled_graph            — the compiled CompiledStateGraph (set after init_graph)
"""
from __future__ import annotations

from typing import Any, Literal, TypedDict

import structlog
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.services.interview_ai import (
    evaluate_turn,
    generate_followup_question,
    generate_next_question,
    generate_report,
    plan_interview_topics,
)

log = structlog.get_logger("interview_graph")

# Compiled graph stored at module level after init_graph() is called at startup
compiled_graph: Any = None


# ── State ──────────────────────────────────────────────────────────────────────

class TurnRecord(TypedDict):
    turn_id: int
    question: str
    user_answer: str
    score: int
    feedback: str
    ideal_answer: str
    turn_type: Literal["primary", "followup"]
    followup_depth: int
    topic_tag: str


class InterviewState(TypedDict):
    # Session context — set once in plan_interview, never mutated
    session_id: int
    user_id: int
    topic: str
    role: str
    years_exp: str
    difficulty: str
    jd_text: str | None
    target_turns: int
    topic_clusters: list[str]

    # Current turn
    current_question: str
    current_topic_tag: str
    primary_questions_asked: int
    followup_depth: int   # 0 = fresh question, 1-2 = follow-up
    turns: list[TurnRecord]

    # Coverage & adaptation
    topics_covered: list[str]
    topic_scores: dict[str, list[int]]
    running_avg_score: float
    difficulty_adjustment: int  # -1 | 0 | +1

    # Flow control
    last_decision: Literal["follow_up", "next_topic", "wrap_up", "start", ""]
    pending_answer: str | None
    interview_complete: bool

    # Output
    report_data: dict[str, Any] | None


# ── Nodes ─────────────────────────────────────────────────────────────────────

async def plan_interview(state: InterviewState) -> dict[str, Any]:
    """Plan topic clusters and generate the opening question."""
    plan = await plan_interview_topics(
        state["topic"],
        state["role"],
        state["years_exp"],
        state["difficulty"],
        state.get("jd_text"),
    )
    log.info(
        "interview_graph.plan_interview",
        session_id=state["session_id"],
        clusters=plan["topic_clusters"],
    )
    return {
        "topic_clusters": plan["topic_clusters"],
        "current_question": plan["opening_question"],
        "current_topic_tag": plan["opening_topic_tag"],
        "last_decision": "start",
    }


async def generate_question(state: InterviewState) -> dict[str, Any]:
    """Generate the next question based on coverage gaps and performance."""
    result = await generate_next_question(
        state["topic"],
        state["role"],
        state["difficulty"],
        state["topics_covered"],
        state["topic_scores"],
        state["topic_clusters"],
        state["turns"],
        state["difficulty_adjustment"],
    )
    return {
        "current_question": result["question"],
        "current_topic_tag": result["topic_tag"],
        "followup_depth": 0,
    }


async def await_answer(state: InterviewState) -> dict[str, Any]:
    """Human-in-the-loop node — graph pauses here waiting for user answer."""
    answer = interrupt("Waiting for user answer")
    return {"pending_answer": answer}


async def evaluate_answer(state: InterviewState) -> dict[str, Any]:
    """Evaluate the user's answer and update coverage/scores."""
    answer = state.get("pending_answer") or ""
    question = state["current_question"]
    topic_tag = state["current_topic_tag"]

    eval_result = await evaluate_turn(
        state["topic"], state["role"], question, answer
    )

    score = eval_result["score"]
    is_primary = state["followup_depth"] == 0

    # Update topic scores
    topic_scores = dict(state["topic_scores"])
    topic_scores.setdefault(topic_tag, []).append(score)

    # Update topics covered list
    topics_covered = list(state["topics_covered"])
    if topic_tag not in topics_covered:
        topics_covered.append(topic_tag)

    # Recalculate running average
    all_scores = [s for scores in topic_scores.values() for s in scores]
    running_avg = sum(all_scores) / len(all_scores) if all_scores else 0.0

    # Difficulty adjustment: push harder if avg > 7.5, ease if avg < 4
    if running_avg >= 7.5:
        difficulty_adjustment = 1
    elif running_avg < 4.0:
        difficulty_adjustment = -1
    else:
        difficulty_adjustment = 0

    # Build turn record (DB write handled in router after graph completes)
    new_turn: TurnRecord = {
        "turn_id": -1,  # will be set after DB insert
        "question": question,
        "user_answer": answer,
        "score": score,
        "feedback": eval_result["feedback"],
        "ideal_answer": eval_result["ideal_answer"],
        "turn_type": "primary" if is_primary else "followup",
        "followup_depth": state["followup_depth"],
        "topic_tag": topic_tag,
    }

    primary_asked = state["primary_questions_asked"] + (1 if is_primary else 0)

    log.info(
        "interview_graph.evaluate_answer",
        session_id=state["session_id"],
        score=score,
        topic=topic_tag,
        primary_asked=primary_asked,
    )

    return {
        "turns": state["turns"] + [new_turn],
        "pending_answer": None,
        "topics_covered": topics_covered,
        "topic_scores": topic_scores,
        "running_avg_score": running_avg,
        "difficulty_adjustment": difficulty_adjustment,
        "primary_questions_asked": primary_asked,
    }


def decide_next(state: InterviewState) -> Literal["follow_up", "next_topic", "wrap_up"]:
    """Pure logic router — decides the next step based on score + progress."""
    if not state["turns"]:
        return "next_topic"

    last_turn = state["turns"][-1]
    score = last_turn["score"]
    depth = state["followup_depth"]
    primary = state["primary_questions_asked"]
    target = state["target_turns"]
    total_turns = len(state["turns"])

    # Hard wrap-up: hit target or total turn cap
    if primary >= target or total_turns >= target + 4:
        return "wrap_up"

    # Follow-up: low score and not at max depth
    if score <= 4 and depth < 2:
        return "follow_up"

    return "next_topic"


async def generate_followup(state: InterviewState) -> dict[str, Any]:
    """Generate a targeted follow-up drilling into the weakness."""
    last_turn = state["turns"][-1]
    result = await generate_followup_question(
        state["topic"],
        state["role"],
        last_turn["question"],
        last_turn["user_answer"],
        state["followup_depth"],
    )
    return {
        "current_question": result["question"],
        "current_topic_tag": result["topic_tag"],
        "followup_depth": state["followup_depth"] + 1,
        "last_decision": "follow_up",
    }


async def generate_final_report(state: InterviewState) -> dict[str, Any]:
    """Generate final report and mark interview complete."""
    # Build question evals format expected by generate_report()
    question_evals = [
        {
            "question_index": i,
            "question": t["question"],
            "user_answer": t["user_answer"],
            "score": t["score"],
            "feedback": t["feedback"],
        }
        for i, t in enumerate(state["turns"])
    ]

    report = await generate_report(state["topic"], state["role"], question_evals)

    log.info(
        "interview_graph.generate_report",
        session_id=state["session_id"],
        overall_score=report["overall_score"],
        turns=len(state["turns"]),
    )

    return {
        "report_data": report,
        "interview_complete": True,
        "last_decision": "wrap_up",
    }


def _route_decide_next(state: InterviewState) -> Literal["follow_up", "next_topic", "wrap_up"]:
    return decide_next(state)


# ── Graph wiring ───────────────────────────────────────────────────────────────

def _build_graph() -> StateGraph:
    workflow = StateGraph(InterviewState)

    workflow.add_node("plan_interview", plan_interview)
    workflow.add_node("generate_question", generate_question)
    workflow.add_node("await_answer", await_answer)
    workflow.add_node("evaluate_answer", evaluate_answer)
    workflow.add_node("generate_followup", generate_followup)
    workflow.add_node("generate_final_report", generate_final_report)

    workflow.add_edge(START, "plan_interview")
    workflow.add_edge("plan_interview", "await_answer")
    workflow.add_edge("await_answer", "evaluate_answer")
    workflow.add_conditional_edges(
        "evaluate_answer",
        _route_decide_next,
        {
            "follow_up": "generate_followup",
            "next_topic": "generate_question",
            "wrap_up": "generate_final_report",
        },
    )
    workflow.add_edge("generate_followup", "await_answer")
    workflow.add_edge("generate_question", "await_answer")
    workflow.add_edge("generate_final_report", END)

    return workflow


async def init_graph(checkpointer: BaseCheckpointSaver) -> None:
    """Compile the interview graph with the given checkpointer. Called at startup."""
    global compiled_graph
    # setup() only exists on PostgresSaver — MemorySaver (used in tests) has no-op init
    if hasattr(checkpointer, "setup"):
        await checkpointer.setup()  # create checkpoint tables (idempotent)
    workflow = _build_graph()
    compiled_graph = workflow.compile(checkpointer=checkpointer)
    log.info("interview_graph.initialized")


def get_graph() -> Any:
    """Return the compiled graph; raises if init_graph() hasn't been called."""
    if compiled_graph is None:
        raise RuntimeError("Interview graph not initialized. Call init_graph() at startup.")
    return compiled_graph
