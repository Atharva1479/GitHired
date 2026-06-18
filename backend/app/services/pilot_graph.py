"""Pilot LangGraph agent — replaces the hand-rolled ReAct loop in pilot_agent.py.

Uses langgraph.prebuilt.create_react_agent with ChatGoogleGenerativeAI or
ChatOllama depending on settings.llm_provider.

Public API:

    async def run_turn(
        conn: asyncpg.Connection,
        user_id: int,
        message: str,
        history: list[dict[str, Any]] | None = None,
    ) -> AgentTurnResult
"""
from __future__ import annotations

import asyncio
from typing import Any

import asyncpg
import structlog
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.prebuilt import create_react_agent

from app.config import settings
from app.services import pilot as pilot_module
from app.services.gemini_service import GeminiUnavailable
from app.services.ollama_service import OllamaUnavailable
from app.services.pilot_agent import (
    MAX_STEPS,
    WALL_BUDGET_SECONDS,
    _AGENT_PERSONA,
    AgentTurnResult,
    ToolTraceEntry,
)
from app.services.pilot_safety import check_message as _safety_check
from app.services.pilot_tool_adapters import adapt_tools
from app.services.pilot_tools import ToolContext

log = structlog.get_logger("pilot.graph")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TIMEOUT_REPLY = (
    "I ran out of time on that one. Could you try a simpler version of the question?"
)
_ERROR_REPLY = "Something went wrong on my end. Give me a moment and try again."


# ---------------------------------------------------------------------------
# LLM factories (kept as named functions so tests can mock _make_agent)
# ---------------------------------------------------------------------------


def _make_gemini() -> Any:
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key.get_secret_value(),
        temperature=0.4,
    )


def _make_ollama() -> Any:
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0.4,
    )


def _make_agent(tools: list[Any], llm: Any) -> Any:
    """Wrap create_react_agent so tests can mock the whole agent at one seam."""
    return create_react_agent(model=llm, tools=tools)


# ---------------------------------------------------------------------------
# History formatter
# ---------------------------------------------------------------------------


def _format_history(history: list[dict[str, Any]] | None) -> list:
    """Convert [{role, content}] dicts to LangChain messages.

    "user" → HumanMessage, "assistant" → AIMessage. Unknown roles skipped.
    """
    if not history:
        return []
    out = []
    for turn in history:
        role = turn.get("role", "")
        content = (turn.get("content") or "").strip()
        if not content:
            continue
        if role == "user":
            out.append(HumanMessage(content=content))
        elif role == "assistant":
            out.append(AIMessage(content=content))
        # skip unknown roles
    return out


# ---------------------------------------------------------------------------
# System prompt builder
# ---------------------------------------------------------------------------


async def _build_system_prompt(conn: asyncpg.Connection, user_id: int) -> str:
    """Combine the agent persona with a live brief context string.

    Calls pilot._build_brief_context() which returns a SESSION FACTS block
    including today's date, user_id, and any pending confirmations from
    the pilot_confirmations table. Crash-safe: on any error returns just
    the persona so the agent always has something to work with.
    """
    try:
        # _build_brief_context is the private function found in pilot_agent.py
        # that fetches pending confirmations + date context.
        from app.services.pilot_agent import _build_brief_context

        brief = await _build_brief_context(user_id, conn)
    except Exception:  # noqa: BLE001
        brief = ""

    if brief:
        return f"{_AGENT_PERSONA}\n\n{brief}"
    return _AGENT_PERSONA


# ---------------------------------------------------------------------------
# Audit log (crash-safe, always called in finally)
# ---------------------------------------------------------------------------


async def _audit_log(
    conn: asyncpg.Connection,
    user_id: int,
    user_message: str,
    result: AgentTurnResult,
) -> None:
    """Persist user + assistant turns. Never raises."""
    try:
        session_id = await pilot_module.find_or_create_today_session(conn, user_id)
        await pilot_module.record_turn(
            conn,
            user_id,
            session_id,
            "user",
            user_message,
            tokens_in=result.tokens_in,
        )
        await pilot_module.record_turn(
            conn,
            user_id,
            session_id,
            "assistant",
            result.reply,
            tokens_out=result.tokens_out,
            tool_calls=[t.as_dict() for t in result.tool_trace] or None,
        )
    except Exception as e:  # noqa: BLE001
        log.warning("pilot.graph.audit_failed", error=str(e))


# ---------------------------------------------------------------------------
# State extraction helpers
# ---------------------------------------------------------------------------


def _extract_reply(state: dict[str, Any]) -> str:
    """Return the content of the last AIMessage in state['messages']."""
    messages = state.get("messages") or []
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            return (msg.content or "").strip()
    return ""


def _extract_tokens(state: dict[str, Any]) -> tuple[int, int]:
    """Sum input/output tokens from all AIMessages in state['messages']."""
    tokens_in = 0
    tokens_out = 0
    for msg in state.get("messages") or []:
        if isinstance(msg, AIMessage):
            meta = getattr(msg, "usage_metadata", None) or {}
            tokens_in += int(meta.get("input_tokens", 0) or 0)
            tokens_out += int(meta.get("output_tokens", 0) or 0)
    return tokens_in, tokens_out


def _extract_tool_trace(state: dict[str, Any]) -> list[ToolTraceEntry]:
    """Build ToolTraceEntry list from AIMessage.tool_calls + ToolMessage content."""
    messages = state.get("messages") or []
    # Map tool_call_id → ToolMessage content for result lookup
    tool_results: dict[str, str] = {}
    for msg in messages:
        if isinstance(msg, ToolMessage):
            tool_results[msg.tool_call_id] = str(msg.content or "")

    trace: list[ToolTraceEntry] = []
    for msg in messages:
        if not isinstance(msg, AIMessage):
            continue
        for tc in getattr(msg, "tool_calls", None) or []:
            call_id = tc.get("id", "")
            result_str = tool_results.get(call_id, "")
            try:
                import json as _json

                result_dict = _json.loads(result_str) if result_str else {}
            except Exception:  # noqa: BLE001
                result_dict = {"raw": result_str}
            trace.append(
                ToolTraceEntry(
                    name=tc.get("name", ""),
                    args=tc.get("args") or {},
                    result=result_dict if isinstance(result_dict, dict) else {"raw": result_dict},
                    latency_ms=0,
                )
            )
    return trace


# ---------------------------------------------------------------------------
# Core turn runner (single LLM invocation)
# ---------------------------------------------------------------------------


async def _invoke_agent(
    agent: Any,
    messages: list,
) -> dict[str, Any]:
    """Call agent.ainvoke with the recursion_limit config."""
    return await agent.ainvoke(
        {"messages": messages},
        config={"recursion_limit": MAX_STEPS * 2 + 1},
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def run_turn(
    conn: asyncpg.Connection,
    user_id: int,
    message: str,
    history: list[dict[str, Any]] | None = None,
) -> AgentTurnResult:
    """Run a single user turn through the LangGraph create_react_agent.

    Routing follows settings.llm_provider:
      gemini — only Gemini
      ollama  — only Ollama
      auto    — Gemini first; on GeminiUnavailable fall back to Ollama
    """
    provider = (settings.llm_provider or "auto").lower()

    # Safety check — deterministic, no LLM involved
    safety = _safety_check(message)
    if safety.triggered:
        log.warning(
            "pilot.graph.safety_triggered",
            user_id=user_id,
            matched=safety.matched_pattern,
        )

    result = AgentTurnResult(reply="")

    try:
        ctx = ToolContext(user_id=user_id, conn=conn)
        tools = adapt_tools(ctx)

        system_prompt = await _build_system_prompt(conn, user_id)

        # Prepend crisis preamble to system prompt when triggered
        if safety.triggered:
            system_prompt = safety.preamble() + "\n\n" + system_prompt

        messages: list = (
            [SystemMessage(content=system_prompt)]
            + _format_history(history)
            + [HumanMessage(content=message)]
        )

        # Build LLM
        if provider == "ollama":
            llm = _make_ollama()
        else:
            llm = _make_gemini()

        agent = _make_agent(tools, llm)

        try:
            state = await asyncio.wait_for(
                _invoke_agent(agent, messages),
                timeout=WALL_BUDGET_SECONDS,
            )
        except asyncio.TimeoutError:
            result.reply = _TIMEOUT_REPLY
            result.outcome = "timeout"
            return result
        except GeminiUnavailable:
            if provider != "auto":
                result.reply = _ERROR_REPLY
                result.outcome = "error"
                return result
            # Auto fallback: retry entire turn with Ollama
            log.warning("pilot.graph.gemini_unavailable_fallback", user_id=user_id)
            ollama_llm = _make_ollama()
            ollama_agent = _make_agent(tools, ollama_llm)
            try:
                state = await asyncio.wait_for(
                    _invoke_agent(ollama_agent, messages),
                    timeout=WALL_BUDGET_SECONDS,
                )
                result.outcome = "ok_ollama"
            except asyncio.TimeoutError:
                result.reply = _TIMEOUT_REPLY
                result.outcome = "timeout"
                return result
            except OllamaUnavailable:
                result.reply = _ERROR_REPLY
                result.outcome = "error"
                return result
        except OllamaUnavailable:
            result.reply = _ERROR_REPLY
            result.outcome = "error"
            return result

        # Extract results from LangGraph state
        reply = _extract_reply(state)
        if not reply:
            result.reply = "Not sure how to answer that. Could you rephrase?"
            result.outcome = "refusal"
            return result

        result.reply = reply
        if result.outcome == "":
            result.outcome = "ok"

        tokens_in, tokens_out = _extract_tokens(state)
        result.tokens_in = tokens_in
        result.tokens_out = tokens_out

        result.tool_trace = _extract_tool_trace(state)
        result.steps = len(result.tool_trace)

    finally:
        await _audit_log(conn, user_id, message, result)

    return result
