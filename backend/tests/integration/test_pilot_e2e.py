"""Integration smoke tests for the LangGraph Pilot agent.

Requires: running Ollama with the configured model.
Run with: pytest tests/integration/test_pilot_e2e.py -m integration -v

These tests are skipped by default so they don't block CI.
They verify the full stack: pilot_agent.run_turn → pilot_graph → LangGraph
→ tool adapters → pilot_tools.dispatch → (mocked) DB.
"""
from __future__ import annotations

import asyncpg
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.pilot_agent import AgentTurnResult, run_turn


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pilot_text_reply() -> None:
    """Test that pilot can generate a text reply without calling tools."""
    conn = MagicMock(spec=asyncpg.Connection)

    with patch(
        "app.services.pilot_graph._build_system_prompt",
        new_callable=AsyncMock,
        return_value="You are Pilot.",
    ), patch(
        "app.services.pilot_graph._audit_log",
        new_callable=AsyncMock,
    ), patch(
        "app.services.pilot_graph.adapt_tools",
        return_value=[],
    ):
        result = await run_turn(
            conn, user_id=1, message="Hi, just say hello back."
        )

    assert isinstance(result, AgentTurnResult)
    assert len(result.reply) > 0
    assert result.outcome in ("ok", "ok_ollama")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pilot_tool_call_list_applications() -> None:
    """Test that pilot can call a real tool (list_applications)."""
    conn = MagicMock(spec=asyncpg.Connection)
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchval = AsyncMock(return_value=0)
    conn.fetchrow = AsyncMock(return_value=None)

    with patch(
        "app.services.pilot_graph._build_system_prompt",
        new_callable=AsyncMock,
        return_value="You are Pilot.",
    ), patch(
        "app.services.pilot_graph._audit_log",
        new_callable=AsyncMock,
    ), patch(
        "app.services.pilot_tools._issue_confirmation",
        new_callable=AsyncMock,
    ):
        result = await run_turn(
            conn, user_id=1, message="How many applications do I have?"
        )

    assert isinstance(result, AgentTurnResult)
    assert result.outcome in ("ok", "ok_ollama")
