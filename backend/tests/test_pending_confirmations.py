"""Pending-confirmation persistence across agent turns.

Locks in the fix for the "confirmation id expired" UX bug. The
problem: tool-call results (which carry the confirm_token) are not part
of the chat-history we feed Gemini on subsequent turns, so the model
on turn 2 had no memory of the token. Fix: persist the original args
alongside the token in pilot_confirmations and surface unexpired
pending confirmations in the brief context so the model can re-call
with the exact token.
"""
from __future__ import annotations

import asyncio
import json
from typing import Awaitable, Callable

import asyncpg

from app.config import settings
from app.services.pilot_agent import _build_brief_context
from app.services.pilot_tools import (
    CONFIRM_TTL_SECONDS,
    ToolContext,
    dispatch,
)
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


def _ctx(conn: asyncpg.Connection) -> ToolContext:
    return ToolContext(user_id=TEST_USER_ID, conn=conn)


def test_issued_confirmation_stores_args_in_db() -> None:
    """The args column must hold the original args (sans confirm_token)."""

    async def go(conn: asyncpg.Connection) -> None:
        created = await dispatch(
            "add_application", {"company": "Stripe", "role": "SWE"}, _ctx(conn),
        )
        app_id = created["application"]["id"]
        confirm = await dispatch(
            "delete_application", {"id": app_id}, _ctx(conn),
        )
        token = confirm["confirm_token"]

        row = await conn.fetchrow(
            "SELECT tool_name, args FROM pilot_confirmations WHERE token = $1",
            token,
        )
        assert row is not None
        assert row["tool_name"] == "delete_application"

        args = row["args"]
        if isinstance(args, str):
            args = json.loads(args)
        assert args == {"id": app_id}, (
            "args must round-trip exactly so the brief can re-issue them"
        )

    _with_conn(go)


def test_brief_context_surfaces_pending_confirmation() -> None:
    """After issuing a confirmation the brief must mention it on next turn."""

    async def go(conn: asyncpg.Connection) -> None:
        created = await dispatch(
            "add_application", {"company": "Acme", "role": "Dev"}, _ctx(conn),
        )
        app_id = created["application"]["id"]
        confirm = await dispatch(
            "delete_application", {"id": app_id}, _ctx(conn),
        )
        token = confirm["confirm_token"]

        brief = await _build_brief_context(TEST_USER_ID, conn)
        assert "PENDING CONFIRMATIONS" in brief
        assert "delete_application" in brief
        assert token in brief
        # Make sure the args are echoed so the model can re-call exactly.
        assert f'"id": {app_id}' in brief or f'"id":{app_id}' in brief

    _with_conn(go)


def test_brief_context_omits_consumed_confirmation() -> None:
    """Once a token has been used, it must not pollute future briefs."""

    async def go(conn: asyncpg.Connection) -> None:
        created = await dispatch(
            "add_application", {"company": "Z", "role": "z"}, _ctx(conn),
        )
        app_id = created["application"]["id"]
        confirm = await dispatch(
            "delete_application", {"id": app_id}, _ctx(conn),
        )
        token = confirm["confirm_token"]
        # Consume it.
        await dispatch(
            "delete_application",
            {"id": app_id, "confirm_token": token},
            _ctx(conn),
        )

        brief = await _build_brief_context(TEST_USER_ID, conn)
        assert token not in brief
        assert "PENDING CONFIRMATIONS" not in brief

    _with_conn(go)


def test_confirm_ttl_is_at_least_five_minutes() -> None:
    """Regression: was 60s, voice flows expired before the user said yes."""
    assert CONFIRM_TTL_SECONDS >= 300


def test_brief_context_isolates_per_user() -> None:
    """User A's pending confirmation must not appear in user B's brief."""

    async def go(conn: asyncpg.Connection) -> None:
        created = await dispatch(
            "add_application", {"company": "Iso", "role": "test"}, _ctx(conn),
        )
        app_id = created["application"]["id"]
        await dispatch("delete_application", {"id": app_id}, _ctx(conn))

        # Some other user — they must not see our pending row.
        other_brief = await _build_brief_context(
            TEST_USER_ID + 9_999_999, conn,
        )
        assert "PENDING CONFIRMATIONS" not in other_brief

    _with_conn(go)
