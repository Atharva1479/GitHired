"""LLM provider routing + auto-fallback tests.

Exercise the run_turn dispatch in pilot_agent for all three settings of
``LLM_PROVIDER``:
  * ``ollama``  → never touches Gemini
  * ``gemini``  → never touches Ollama, even on quota
  * ``auto``    → on Gemini quota/auth/upstream errors, transparently
                   retries the same turn through Ollama and the user
                   sees the Ollama reply

We monkeypatch the inner per-provider entry points so the tests are
hermetic — no Gemini API key needed, no Ollama server needed.
"""
from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable

import asyncpg
import pytest

from app.config import settings
from app.services import pilot_agent
from app.services.ollama_service import OllamaUnavailable
from app.services.pilot_agent import AgentTurnResult
from tests.conftest import TEST_USER_ID


def _with_conn(
    body: Callable[[asyncpg.Connection], Awaitable[None]],
) -> None:
    async def runner() -> None:
        conn = await asyncpg.connect(str(settings.database_url))
        try:
            await body(conn)
        finally:
            await conn.close()

    asyncio.run(runner())


def _stub_result(reply: str, outcome: str = "ok") -> AgentTurnResult:
    return AgentTurnResult(reply=reply, outcome=outcome)


# ── LLM_PROVIDER=ollama ──────────────────────────────────────────────


def test_provider_ollama_never_calls_gemini(monkeypatch: pytest.MonkeyPatch) -> None:
    """With LLM_PROVIDER=ollama, Gemini path must not run."""

    async def go(conn: asyncpg.Connection) -> None:
        called = {"gemini": 0, "ollama": 0}

        async def fake_gemini(*args: Any, **kwargs: Any) -> AgentTurnResult:
            called["gemini"] += 1
            return _stub_result("from gemini")

        async def fake_ollama(*args: Any, **kwargs: Any) -> AgentTurnResult:
            called["ollama"] += 1
            return _stub_result("from ollama", outcome="ok_ollama")

        monkeypatch.setattr(settings, "llm_provider", "ollama")
        monkeypatch.setattr(pilot_agent, "_gemini_run_turn", fake_gemini)
        monkeypatch.setattr(pilot_agent, "_ollama_run_turn", fake_ollama)

        result = await pilot_agent.run_turn(conn, TEST_USER_ID, "hi", [])
        assert result.reply == "from ollama"
        assert called["gemini"] == 0
        assert called["ollama"] == 1

    _with_conn(go)


# ── LLM_PROVIDER=gemini ──────────────────────────────────────────────


def test_provider_gemini_never_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    """LLM_PROVIDER=gemini surfaces quota errors instead of falling back."""

    async def go(conn: asyncpg.Connection) -> None:
        called = {"gemini": 0, "ollama": 0}

        async def fake_gemini(*args: Any, **kwargs: Any) -> AgentTurnResult:
            called["gemini"] += 1
            return _stub_result(
                "I'm out of Gemini quota right now.",
                outcome="quota_exhausted",
            )

        async def fake_ollama(*args: Any, **kwargs: Any) -> AgentTurnResult:
            called["ollama"] += 1
            return _stub_result("from ollama")

        monkeypatch.setattr(settings, "llm_provider", "gemini")
        monkeypatch.setattr(pilot_agent, "_gemini_run_turn", fake_gemini)
        monkeypatch.setattr(pilot_agent, "_ollama_run_turn", fake_ollama)

        result = await pilot_agent.run_turn(conn, TEST_USER_ID, "hi", [])
        assert result.outcome == "quota_exhausted"
        assert "quota" in result.reply.lower()
        assert called["gemini"] == 1
        assert called["ollama"] == 0, "must NOT fall back when provider=gemini"

    _with_conn(go)


def test_provider_gemini_ok_passes_through(monkeypatch: pytest.MonkeyPatch) -> None:
    """LLM_PROVIDER=gemini happy path returns the Gemini reply unchanged."""

    async def go(conn: asyncpg.Connection) -> None:
        async def fake_gemini(*args: Any, **kwargs: Any) -> AgentTurnResult:
            return _stub_result("You've sent 7 applications this week.")

        async def fake_ollama(*args: Any, **kwargs: Any) -> AgentTurnResult:
            raise AssertionError("ollama must not be called")

        monkeypatch.setattr(settings, "llm_provider", "gemini")
        monkeypatch.setattr(pilot_agent, "_gemini_run_turn", fake_gemini)
        monkeypatch.setattr(pilot_agent, "_ollama_run_turn", fake_ollama)

        result = await pilot_agent.run_turn(conn, TEST_USER_ID, "how am i?", [])
        assert result.reply == "You've sent 7 applications this week."
        assert result.outcome == "ok"

    _with_conn(go)


# ── LLM_PROVIDER=auto ────────────────────────────────────────────────


def test_provider_auto_falls_back_on_quota(monkeypatch: pytest.MonkeyPatch) -> None:
    """LLM_PROVIDER=auto retries via Ollama when Gemini reports quota."""

    async def go(conn: asyncpg.Connection) -> None:
        called = {"gemini": 0, "ollama": 0}

        async def fake_gemini(*args: Any, **kwargs: Any) -> AgentTurnResult:
            called["gemini"] += 1
            return _stub_result(
                "I'm out of Gemini quota right now.",
                outcome="quota_exhausted",
            )

        async def fake_ollama(*args: Any, **kwargs: Any) -> AgentTurnResult:
            called["ollama"] += 1
            return _stub_result(
                "I can give you general advice but can't read your data right now.",
                outcome="ok_ollama_text_only",
            )

        monkeypatch.setattr(settings, "llm_provider", "auto")
        monkeypatch.setattr(pilot_agent, "_gemini_run_turn", fake_gemini)
        monkeypatch.setattr(pilot_agent, "_ollama_run_turn", fake_ollama)

        result = await pilot_agent.run_turn(conn, TEST_USER_ID, "how am i?", [])
        # User sees the ollama reply, not the Gemini quota error.
        assert "Gemini quota" not in result.reply
        assert result.outcome == "ok_ollama_text_only"
        assert called["gemini"] == 1
        assert called["ollama"] == 1

    _with_conn(go)


def test_provider_auto_falls_back_on_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    """Auth errors trigger the same fallback path (e.g., bad/expired API key)."""

    async def go(conn: asyncpg.Connection) -> None:
        called = {"ollama": 0}

        async def fake_gemini(*args: Any, **kwargs: Any) -> AgentTurnResult:
            return _stub_result("API key rejected", outcome="auth_error")

        async def fake_ollama(*args: Any, **kwargs: Any) -> AgentTurnResult:
            called["ollama"] += 1
            return _stub_result("ollama answer", outcome="ok_ollama")

        monkeypatch.setattr(settings, "llm_provider", "auto")
        monkeypatch.setattr(pilot_agent, "_gemini_run_turn", fake_gemini)
        monkeypatch.setattr(pilot_agent, "_ollama_run_turn", fake_ollama)

        result = await pilot_agent.run_turn(conn, TEST_USER_ID, "hi", [])
        assert result.reply == "ollama answer"
        assert called["ollama"] == 1

    _with_conn(go)


def test_provider_auto_falls_back_on_upstream_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """503 / network errors are fallback-worthy too."""

    async def go(conn: asyncpg.Connection) -> None:
        called = {"ollama": 0}

        async def fake_gemini(*args: Any, **kwargs: Any) -> AgentTurnResult:
            return _stub_result("Gemini down", outcome="upstream_unavailable")

        async def fake_ollama(*args: Any, **kwargs: Any) -> AgentTurnResult:
            called["ollama"] += 1
            return _stub_result("local answer", outcome="ok_ollama")

        monkeypatch.setattr(settings, "llm_provider", "auto")
        monkeypatch.setattr(pilot_agent, "_gemini_run_turn", fake_gemini)
        monkeypatch.setattr(pilot_agent, "_ollama_run_turn", fake_ollama)

        result = await pilot_agent.run_turn(conn, TEST_USER_ID, "hi", [])
        assert result.reply == "local answer"
        assert called["ollama"] == 1

    _with_conn(go)


def test_provider_auto_does_NOT_fall_back_on_generic_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Generic ``outcome="error"`` is NOT in the fallback set — we surface
    the original error so a real bug doesn't get silently masked by a
    weaker local model."""

    async def go(conn: asyncpg.Connection) -> None:
        called = {"ollama": 0}

        async def fake_gemini(*args: Any, **kwargs: Any) -> AgentTurnResult:
            return _stub_result("Hit an unexpected error", outcome="error")

        async def fake_ollama(*args: Any, **kwargs: Any) -> AgentTurnResult:
            called["ollama"] += 1
            return _stub_result("should not be reached", outcome="ok_ollama")

        monkeypatch.setattr(settings, "llm_provider", "auto")
        monkeypatch.setattr(pilot_agent, "_gemini_run_turn", fake_gemini)
        monkeypatch.setattr(pilot_agent, "_ollama_run_turn", fake_ollama)

        result = await pilot_agent.run_turn(conn, TEST_USER_ID, "hi", [])
        assert result.outcome == "error"
        assert called["ollama"] == 0

    _with_conn(go)


def test_provider_auto_no_fallback_when_gemini_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Happy path: Gemini answers, Ollama never runs."""

    async def go(conn: asyncpg.Connection) -> None:
        called = {"ollama": 0}

        async def fake_gemini(*args: Any, **kwargs: Any) -> AgentTurnResult:
            return _stub_result("here is your answer")

        async def fake_ollama(*args: Any, **kwargs: Any) -> AgentTurnResult:
            called["ollama"] += 1
            return _stub_result("should not run")

        monkeypatch.setattr(settings, "llm_provider", "auto")
        monkeypatch.setattr(pilot_agent, "_gemini_run_turn", fake_gemini)
        monkeypatch.setattr(pilot_agent, "_ollama_run_turn", fake_ollama)

        result = await pilot_agent.run_turn(conn, TEST_USER_ID, "hi", [])
        assert result.reply == "here is your answer"
        assert called["ollama"] == 0

    _with_conn(go)


# ── Ollama client surface ────────────────────────────────────────────


def test_ollama_unavailable_message_is_clean() -> None:
    """The OllamaUnavailable exception string must be safe to surface
    to a user — no traceback bits, no httpx repr."""
    exc = OllamaUnavailable(
        "Ollama server not reachable. Is it running on http://localhost:11434?"
    )
    s = str(exc)
    assert "Traceback" not in s
    assert "httpx" not in s.lower()
    assert "localhost" in s


def test_fallback_outcomes_set_is_well_defined() -> None:
    """Lock in the exact set of outcomes that trigger Ollama fallback.

    If we add a new error category, we should consciously decide whether
    it qualifies as fallback-worthy. This test fails on accidental drift.
    """
    assert pilot_agent._FALLBACK_OUTCOMES == {
        "quota_exhausted",
        "rate_limited",
        "auth_error",
        "upstream_unavailable",
    }
