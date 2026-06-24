"""Integration tests for the nudge engine batch insert.

Tests the key invariants of the refactored batch nudge insert:
- run_all_checks returns the count of newly inserted nudges
- Running twice (same day) does not insert duplicates (ON CONFLICT DO NOTHING)
- The batch insert path reaches the DB correctly
"""
from __future__ import annotations

import asyncio
import datetime as dt
from typing import Awaitable, Callable

import asyncpg

from app.config import settings
from app.services.nudge_engine import run_all_checks
from tests.conftest import TEST_USER_ID


def _with_conn(body: Callable[[asyncpg.Connection], Awaitable[None]]) -> None:
    async def runner() -> None:
        conn = await asyncpg.connect(str(settings.database_url))
        try:
            await body(conn)
        finally:
            await conn.close()

    asyncio.run(runner())


def _seed_application(conn: asyncpg.Connection, company: str, applied_days_ago: int) -> asyncio.Future:
    today = dt.date.today()
    applied_date = today - dt.timedelta(days=applied_days_ago)
    return conn.execute(
        """
        INSERT INTO applications (user_id, company, role, status, applied_date, source)
        VALUES ($1, $2, 'Engineer', 'Applied', $3, 'Direct')
        """,
        TEST_USER_ID, company, applied_date,
    )


# ── run_all_checks behaviour ──────────────────────────────────────────────────


def test_run_all_checks_returns_int_count() -> None:
    """run_all_checks returns the number of newly inserted nudges (int)."""
    async def go(conn: asyncpg.Connection) -> None:
        count = await run_all_checks(conn, TEST_USER_ID, dt.date.today())
        assert isinstance(count, int)
        assert count >= 0

    _with_conn(go)


def test_batch_insert_is_idempotent() -> None:
    """Running run_all_checks twice on the same day inserts 0 duplicates the second time."""
    async def go(conn: asyncpg.Connection) -> None:
        # Seed an application old enough to trigger follow-up rule (R1 requires >= 7 days)
        await _seed_application(conn, "IdempotentCo", applied_days_ago=8)

        today = dt.date.today()
        first = await run_all_checks(conn, TEST_USER_ID, today)
        assert first >= 1, "Expected at least one nudge on first run"

        # Second run — same day, ON CONFLICT DO NOTHING should suppress all
        second = await run_all_checks(conn, TEST_USER_ID, today)
        assert second == 0, f"Expected 0 new nudges on second run (got {second})"

    _with_conn(go)


def test_no_nudges_when_no_applications() -> None:
    """With no applications, run_all_checks may only emit the weekly-volume nudge."""
    async def go(conn: asyncpg.Connection) -> None:
        count = await run_all_checks(conn, TEST_USER_ID, dt.date.today())
        # Only R4 (apply_more) fires when weekly_count < 5 with zero apps
        assert count <= 1

    _with_conn(go)


def test_stale_application_triggers_nudge() -> None:
    """An application Applied 10 days ago triggers at least one nudge."""
    async def go(conn: asyncpg.Connection) -> None:
        await _seed_application(conn, "StaleCorp", applied_days_ago=10)
        count = await run_all_checks(conn, TEST_USER_ID, dt.date.today())
        # R1 (follow-up >= 7d) and possibly R2 (stale >= 14d) fire
        assert count >= 1

    _with_conn(go)


def test_nudges_visible_via_api() -> None:
    """Nudges created by run_all_checks are retrievable via the HTTP API."""
    from fastapi.testclient import TestClient
    from app.main import app

    async def seed(conn: asyncpg.Connection) -> None:
        await _seed_application(conn, "ApiVisibleCo", applied_days_ago=8)
        await run_all_checks(conn, TEST_USER_ID, dt.date.today())

    _with_conn(seed)

    with TestClient(app) as client:
        r = client.get("/api/nudges/today")
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        companies = [n.get("message", "") for n in items]
        assert any("ApiVisibleCo" in m for m in companies)
