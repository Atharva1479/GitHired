"""Unit tests for pilot_graph — TDD pass.

No real LLM, no DB, no network. All external calls are mocked.
"""
from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from app.services.pilot_agent import AgentTurnResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ai_message(content: str = "Done!", tool_calls: list | None = None) -> AIMessage:
    """Build a minimal AIMessage with optional usage_metadata."""
    msg = AIMessage(content=content)
    # Attach usage_metadata mirroring real LangChain shape
    msg.usage_metadata = {"input_tokens": 10, "output_tokens": 5}  # type: ignore[attr-defined]
    if tool_calls is not None:
        msg.tool_calls = tool_calls  # type: ignore[attr-defined]
    return msg


def _fake_agent_state(content: str = "Done!") -> dict[str, Any]:
    """Return a minimal LangGraph state dict containing one AIMessage."""
    return {"messages": [_make_ai_message(content)]}


# ---------------------------------------------------------------------------
# TestRunTurnContract
# ---------------------------------------------------------------------------


class TestRunTurnContract:
    """Verify the public contract of run_turn without touching any real service."""

    @pytest.mark.asyncio
    async def test_returns_agent_turn_result(self) -> None:
        """Happy path: run_turn returns AgentTurnResult with reply and ok outcome."""
        conn = MagicMock()
        mock_agent = MagicMock()
        mock_agent.ainvoke = AsyncMock(return_value=_fake_agent_state("Done!"))

        with (
            patch(
                "app.services.pilot_graph._build_system_prompt",
                new=AsyncMock(return_value="You are Pilot."),
            ),
            patch(
                "app.services.pilot_graph._make_agent",
                return_value=mock_agent,
            ),
            patch(
                "app.services.pilot_graph._audit_log",
                new=AsyncMock(),
            ),
            patch(
                "app.services.pilot_graph.adapt_tools",
                return_value=[],
            ),
        ):
            from app.services.pilot_graph import run_turn

            result = await run_turn(conn=conn, user_id=1, message="hello")

        assert isinstance(result, AgentTurnResult)
        assert result.reply == "Done!"
        assert result.outcome == "ok"

    @pytest.mark.asyncio
    async def test_wall_budget_exceeded_returns_timeout_outcome(self) -> None:
        """When ainvoke takes longer than WALL_BUDGET_SECONDS, outcome is 'timeout'."""
        conn = MagicMock()

        async def _sleeps_forever(*args: Any, **kwargs: Any) -> dict:
            await asyncio.sleep(9999)
            return _fake_agent_state()

        mock_agent = MagicMock()
        mock_agent.ainvoke = _sleeps_forever

        with (
            patch(
                "app.services.pilot_graph._build_system_prompt",
                new=AsyncMock(return_value="You are Pilot."),
            ),
            patch(
                "app.services.pilot_graph._make_agent",
                return_value=mock_agent,
            ),
            patch(
                "app.services.pilot_graph._audit_log",
                new=AsyncMock(),
            ),
            patch(
                "app.services.pilot_graph.adapt_tools",
                return_value=[],
            ),
            # Shrink the budget so the test runs fast
            patch("app.services.pilot_graph.WALL_BUDGET_SECONDS", 0.01),
        ):
            from app.services import pilot_graph

            # reload to pick up the patched constant within this scope
            result = await pilot_graph.run_turn(conn=conn, user_id=1, message="hello")

        assert result.outcome == "timeout"

    @pytest.mark.asyncio
    async def test_gemini_unavailable_falls_back_to_ollama(self) -> None:
        """On GeminiUnavailable with provider='auto', retry with Ollama model."""
        from app.services.gemini_service import GeminiUnavailable

        conn = MagicMock()
        call_count = 0

        async def _first_raises_then_succeeds(*args: Any, **kwargs: Any) -> dict:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise GeminiUnavailable("quota")
            return _fake_agent_state("Ollama reply")

        mock_agent = MagicMock()
        mock_agent.ainvoke = _first_raises_then_succeeds

        with (
            patch(
                "app.services.pilot_graph._build_system_prompt",
                new=AsyncMock(return_value="You are Pilot."),
            ),
            patch(
                "app.services.pilot_graph._make_agent",
                return_value=mock_agent,
            ),
            patch(
                "app.services.pilot_graph._audit_log",
                new=AsyncMock(),
            ),
            patch(
                "app.services.pilot_graph.adapt_tools",
                return_value=[],
            ),
            patch("app.services.pilot_graph.settings") as mock_settings,
        ):
            mock_settings.llm_provider = "auto"
            mock_settings.gemini_api_key.get_secret_value.return_value = "key"
            mock_settings.gemini_model = "gemini-2.5-flash-lite"
            mock_settings.ollama_model = "qwen3.5:2b"
            mock_settings.ollama_base_url = "http://localhost:11434"

            from app.services import pilot_graph

            result = await pilot_graph.run_turn(conn=conn, user_id=1, message="hello")

        assert call_count == 2, "ainvoke must be called twice (Gemini attempt + Ollama fallback)"
        assert "ollama" in result.outcome

    @pytest.mark.asyncio
    async def test_audit_log_called_even_on_timeout(self) -> None:
        """_audit_log must be awaited exactly once even when ainvoke times out."""
        conn = MagicMock()
        audit_mock = AsyncMock()

        async def _sleeps_forever(*args: Any, **kwargs: Any) -> dict:
            await asyncio.sleep(9999)
            return _fake_agent_state()

        mock_agent = MagicMock()
        mock_agent.ainvoke = _sleeps_forever

        with (
            patch(
                "app.services.pilot_graph._build_system_prompt",
                new=AsyncMock(return_value="You are Pilot."),
            ),
            patch(
                "app.services.pilot_graph._make_agent",
                return_value=mock_agent,
            ),
            patch(
                "app.services.pilot_graph._audit_log",
                new=audit_mock,
            ),
            patch(
                "app.services.pilot_graph.adapt_tools",
                return_value=[],
            ),
            patch("app.services.pilot_graph.WALL_BUDGET_SECONDS", 0.01),
        ):
            from app.services import pilot_graph

            await pilot_graph.run_turn(conn=conn, user_id=1, message="hello")

        audit_mock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_safety_preamble_injected_into_system_prompt(self) -> None:
        """When safety check triggers, the preamble is prepended to the system prompt."""
        from langchain_core.messages import AIMessage, SystemMessage as SM

        from app.services import pilot_graph
        from app.services.pilot_safety import SafetyDecision

        conn = MagicMock()
        captured_messages: list = []

        async def _capture_messages(state: dict, config: Any = None) -> dict:
            captured_messages.extend(state.get("messages", []))
            return {"messages": [AIMessage(content="Stay safe.")]}

        fake_safety = SafetyDecision(triggered=True, matched_pattern="test")
        mock_agent = MagicMock()
        mock_agent.ainvoke = AsyncMock(side_effect=_capture_messages)

        with (
            patch(
                "app.services.pilot_graph._safety_check",
                return_value=fake_safety,
            ),
            patch(
                "app.services.pilot_graph._build_system_prompt",
                new=AsyncMock(return_value="You are Pilot."),
            ),
            patch(
                "app.services.pilot_graph._make_agent",
                return_value=mock_agent,
            ),
            patch(
                "app.services.pilot_graph._audit_log",
                new=AsyncMock(),
            ),
            patch(
                "app.services.pilot_graph.adapt_tools",
                return_value=[],
            ),
        ):
            result = await pilot_graph.run_turn(
                conn=conn, user_id=1, message="I want to hurt myself"
            )

        # System message should contain the safety preamble
        system_msgs = [m for m in captured_messages if isinstance(m, SM)]
        assert len(system_msgs) == 1
        preamble = fake_safety.preamble()
        assert preamble in system_msgs[0].content
