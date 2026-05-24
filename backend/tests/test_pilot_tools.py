"""Tests for the read-only Pilot agent tools."""
from __future__ import annotations

import asyncio
import datetime as dt
from typing import Awaitable, Callable

import asyncpg
import pytest

from app.config import settings
from app.services.pilot_tools import ToolContext, dispatch
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


def _ctx(conn: asyncpg.Connection, user_id: int = TEST_USER_ID) -> ToolContext:
    return ToolContext(user_id=user_id, conn=conn)


async def _seed_app(
    conn: asyncpg.Connection,
    *,
    user_id: int = TEST_USER_ID,
    company: str = "Stripe",
    role: str = "Software Engineer",
    status: str = "Applied",
    source: str = "LinkedIn",
) -> int:
    row = await conn.fetchrow(
        """
        INSERT INTO applications
            (user_id, company, role, source, applied_date, status)
        VALUES ($1, $2, $3, $4, CURRENT_DATE, $5)
        RETURNING id
        """,
        user_id, company, role, source, status,
    )
    return int(row["id"])


async def _seed_referral(
    conn: asyncpg.Connection,
    *,
    user_id: int = TEST_USER_ID,
    name: str = "Priya Sharma",
    company: str = "Stripe",
    target_role: str = "Frontend Engineer",
) -> int:
    row = await conn.fetchrow(
        """
        INSERT INTO referral_contacts
            (user_id, name, company, target_role, connection_sent_date)
        VALUES ($1, $2, $3, $4, CURRENT_DATE)
        RETURNING id
        """,
        user_id, name, company, target_role,
    )
    return int(row["id"])


# ───────────────────────────── dispatch behaviour ──────────────────────────


def test_dispatch_unknown_tool_returns_error() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        out = await dispatch("does_not_exist", {}, _ctx(conn))
        assert "error" in out
        assert "unknown tool" in out["error"]

    _with_conn(go)


def test_dispatch_handler_exception_returns_error() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        # Force an asyncpg type error on the get_stats period validation.
        out = await dispatch("get_stats", {"period": "decade"}, _ctx(conn))
        assert "error" in out

    _with_conn(go)


# ───────────────────────────── get_profile ─────────────────────────────────


def test_get_profile_returns_user_basics() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        out = await dispatch("get_profile", {}, _ctx(conn))
        assert out["id"] == TEST_USER_ID
        assert out["email"]
        assert out["first_name"]
        assert "member_since" in out

    _with_conn(go)


# ───────────────────────────── get_stats ──────────────────────────────────


def test_get_stats_zero_state() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        out = await dispatch("get_stats", {"period": "all"}, _ctx(conn))
        assert out["applications"]["total"] == 0
        assert out["referrals"]["total"] == 0
        assert out["applications"]["response_rate_pct"] is None

    _with_conn(go)


def test_get_stats_counts_after_seed() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        async with conn.transaction():
            await _seed_app(conn, company="Stripe", status="Applied")
            await _seed_app(conn, company="Anthropic", status="Interview")
            await _seed_app(conn, company="Datadog", status="Offer")
        out = await dispatch("get_stats", {"period": "all"}, _ctx(conn))
        assert out["applications"]["total"] == 3
        assert out["applications"]["interview"] == 1
        assert out["applications"]["offers"] == 1

    _with_conn(go)


# ─────────────────────────── list_applications ────────────────────────────


def test_list_applications_empty() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        out = await dispatch("list_applications", {}, _ctx(conn))
        assert out["count"] == 0
        assert out["applications"] == []

    _with_conn(go)


def test_list_applications_company_filter_is_case_insensitive() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        async with conn.transaction():
            await _seed_app(conn, company="Stripe")
            await _seed_app(conn, company="Anthropic")
        out = await dispatch(
            "list_applications", {"company": "stripe"}, _ctx(conn)
        )
        assert out["count"] == 1
        assert out["applications"][0]["company"] == "Stripe"

    _with_conn(go)


# ──────────────────────────── get_application ─────────────────────────────


def test_get_application_by_id() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        async with conn.transaction():
            app_id = await _seed_app(conn, company="Stripe")
        out = await dispatch("get_application", {"id": app_id}, _ctx(conn))
        assert "application" in out
        assert out["application"]["company"] == "Stripe"
        assert "follow_up_count" in out["application"]

    _with_conn(go)


def test_get_application_ambiguous_when_multiple_match() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        async with conn.transaction():
            await _seed_app(conn, company="Stripe", role="Frontend Engineer")
            await _seed_app(conn, company="Stripe", role="Backend Engineer")
        out = await dispatch(
            "get_application", {"company": "Stripe"}, _ctx(conn)
        )
        assert out.get("ambiguous") is True
        assert len(out["candidates"]) == 2

    _with_conn(go)


def test_get_application_not_found() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        out = await dispatch(
            "get_application", {"company": "NobodyCorp"}, _ctx(conn)
        )
        assert out.get("error") == "not_found"

    _with_conn(go)


def test_get_application_requires_id_or_company() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        out = await dispatch("get_application", {}, _ctx(conn))
        assert "error" in out

    _with_conn(go)


# ───────────────────────── cross-user isolation ───────────────────────────


def test_tools_filter_by_session_user_id() -> None:
    """Data seeded for user A must never appear when queried as user B."""

    async def go(conn: asyncpg.Connection) -> None:
        async with conn.transaction():
            await _seed_app(conn, company="Stripe")

        # Queried as TEST_USER_ID — visible.
        own = await dispatch("list_applications", {}, _ctx(conn))
        assert own["count"] == 1

        # Queried as a different user_id — invisible. We use an id that has
        # no real data; the tool should still safely return zero, not leak.
        other = await dispatch(
            "list_applications", {}, _ctx(conn, user_id=TEST_USER_ID + 9_999_999)
        )
        assert other["count"] == 0

    _with_conn(go)


# ─────────────────────────────── referrals ────────────────────────────────


def test_list_referrals_and_get_referral_by_id() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        async with conn.transaction():
            ref_id = await _seed_referral(conn, name="Priya Sharma")

        listing = await dispatch("list_referrals", {}, _ctx(conn))
        assert listing["count"] == 1

        one = await dispatch("get_referral", {"id": ref_id}, _ctx(conn))
        assert one["referral"]["name"] == "Priya Sharma"

    _with_conn(go)


def test_get_referral_ambiguous_by_name() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        async with conn.transaction():
            await _seed_referral(conn, name="Priya Sharma", company="Stripe")
            await _seed_referral(conn, name="Priya Singh", company="Anthropic")
        out = await dispatch("get_referral", {"name": "Priya"}, _ctx(conn))
        assert out.get("ambiguous") is True
        assert len(out["candidates"]) == 2

    _with_conn(go)


# ───────────────────────────── misc tools ─────────────────────────────────


def test_get_xp_state_returns_full_shape() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        out = await dispatch("get_xp_state", {}, _ctx(conn))
        assert "level" in out
        assert "streak_days" in out
        assert "daily_quests" in out
        assert isinstance(out["daily_quests"], list)

    _with_conn(go)


def test_list_recent_activity_empty_when_no_events() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        out = await dispatch("list_recent_activity", {"days": 7}, _ctx(conn))
        assert out["count"] == 0
        assert out["events"] == []

    _with_conn(go)


def test_list_pending_nudges_empty() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        out = await dispatch("list_pending_nudges", {}, _ctx(conn))
        assert out["count"] == 0

    _with_conn(go)


def test_list_drafts_empty() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        out = await dispatch("list_drafts", {}, _ctx(conn))
        assert out["count"] == 0

    _with_conn(go)


def test_list_achievements_filter() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        all_ = await dispatch("list_achievements", {}, _ctx(conn))
        locked = await dispatch("list_achievements", {"unlocked": False}, _ctx(conn))
        unlocked = await dispatch("list_achievements", {"unlocked": True}, _ctx(conn))
        # Every achievement is locked for a fresh user.
        assert all_["count"] > 0
        assert locked["count"] == all_["count"]
        assert unlocked["count"] == 0

    _with_conn(go)
