"""Tests for the gamification engine."""
from __future__ import annotations

import asyncio
import datetime as dt
from typing import Awaitable, Callable

import asyncpg

from app.config import settings
from app.services import gamify
from tests.conftest import TEST_USER_ID


# ---------------------------------------------------------------------------
# Pure-function tests
# ---------------------------------------------------------------------------


def test_level_for_xp_starts_at_one() -> None:
    assert gamify.level_for_xp(0) == 1
    assert gamify.level_for_xp(99) == 1


def test_level_for_xp_crosses_thresholds() -> None:
    assert gamify.level_for_xp(100) == 2
    assert gamify.level_for_xp(gamify.LEVEL_THRESHOLDS[2]) == 3
    assert gamify.level_for_xp(gamify.LEVEL_THRESHOLDS[4]) == 5


def test_level_for_xp_caps_at_max() -> None:
    # The 1.6× growth curve means level 50 sits ~600B XP — pick a value safely
    # past the highest threshold rather than guessing a magnitude.
    huge = gamify.LEVEL_THRESHOLDS[-1] * 2
    assert gamify.level_for_xp(huge) == gamify.MAX_LEVEL


def test_xp_to_next_level_returns_progress() -> None:
    into, span = gamify.xp_to_next_level(50)
    assert into == 50
    assert span == 100


def test_compute_streak_first_event() -> None:
    streak, freezes, comeback = gamify._compute_streak(
        last=None, today=dt.date(2026, 5, 16), current_streak=0, freezes=0,
    )
    assert (streak, freezes, comeback) == (1, 0, False)


def test_compute_streak_same_day_noop() -> None:
    today = dt.date(2026, 5, 16)
    streak, _, _ = gamify._compute_streak(
        last=today, today=today, current_streak=4, freezes=0,
    )
    assert streak == 4


def test_compute_streak_consecutive_day_increments() -> None:
    streak, _, _ = gamify._compute_streak(
        last=dt.date(2026, 5, 15),
        today=dt.date(2026, 5, 16),
        current_streak=3,
        freezes=0,
    )
    assert streak == 4


def test_compute_streak_freeze_covers_one_missed_day() -> None:
    streak, freezes, comeback = gamify._compute_streak(
        last=dt.date(2026, 5, 14),
        today=dt.date(2026, 5, 16),
        current_streak=5,
        freezes=2,
    )
    assert streak == 6
    assert freezes == 1
    assert not comeback


def test_compute_streak_resets_without_freeze() -> None:
    streak, freezes, comeback = gamify._compute_streak(
        last=dt.date(2026, 5, 13),
        today=dt.date(2026, 5, 16),
        current_streak=5,
        freezes=0,
    )
    assert streak == 1
    assert freezes == 0
    assert not comeback  # 3-day gap doesn't qualify


def test_compute_streak_comeback_after_long_gap() -> None:
    streak, _, comeback = gamify._compute_streak(
        last=dt.date(2026, 5, 1),
        today=dt.date(2026, 5, 16),
        current_streak=5,
        freezes=0,
    )
    assert streak == 1
    assert comeback


def test_seeded_pick_is_deterministic() -> None:
    a = gamify._seeded_pick(gamify.DAILY_POOL, "1:2026-05-16", 3)
    b = gamify._seeded_pick(gamify.DAILY_POOL, "1:2026-05-16", 3)
    assert a == b


# ---------------------------------------------------------------------------
# DB integration tests
# ---------------------------------------------------------------------------


def _with_conn(
    body: Callable[[asyncpg.Connection], Awaitable[None]],
) -> None:
    """Run an async body with a fresh asyncpg connection on a fresh loop."""
    async def runner() -> None:
        conn = await asyncpg.connect(str(settings.database_url))
        try:
            await body(conn)
        finally:
            await conn.close()

    asyncio.run(runner())


def test_record_event_awards_xp() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        async with conn.transaction():
            r = await gamify.record_event(
                conn, TEST_USER_ID, "app.added",
                ref_type="application", ref_id=999,
            )
        assert r.xp_gained == gamify.XP_REWARDS["app.added"]
        assert r.streak == 1
        assert not r.duplicate

    _with_conn(go)


def test_record_event_idempotent() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        async with conn.transaction():
            first = await gamify.record_event(
                conn, TEST_USER_ID, "app.added",
                ref_type="application", ref_id=1000,
            )
        async with conn.transaction():
            second = await gamify.record_event(
                conn, TEST_USER_ID, "app.added",
                ref_type="application", ref_id=1000,
            )
        assert first.xp_gained == 10
        assert second.duplicate
        assert second.xp_gained == 0

        total = await conn.fetchval(
            "SELECT current_xp FROM user_progress WHERE user_id = $1",
            TEST_USER_ID,
        )
        assert total == 10

    _with_conn(go)


def test_record_event_unlocks_first_application() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        async with conn.transaction():
            r = await gamify.record_event(
                conn, TEST_USER_ID, "app.added",
                ref_type="application", ref_id=2000,
            )
        assert "first_application" in r.unlocked

    _with_conn(go)


def test_quest_progress_completes_and_awards() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        spec = gamify.QUESTS["daily_apply_3"]
        expires = dt.datetime.combine(
            dt.date.today() + dt.timedelta(days=1), dt.time.min
        )
        async with conn.transaction():
            # Insert directly so the test doesn't depend on rotation picks.
            await conn.execute(
                "INSERT INTO quests (user_id, code, period, target, reward_xp, "
                "expires_at) VALUES ($1, $2, $3, $4, $5, $6)",
                TEST_USER_ID, spec.code, spec.period, spec.target,
                spec.reward_xp, expires,
            )
            r1 = await gamify.record_event(
                conn, TEST_USER_ID, "app.added",
                ref_type="application", ref_id=3001,
            )
            r2 = await gamify.record_event(
                conn, TEST_USER_ID, "app.added",
                ref_type="application", ref_id=3002,
            )
            r3 = await gamify.record_event(
                conn, TEST_USER_ID, "app.added",
                ref_type="application", ref_id=3003,
            )
        completed = (
            r1.quest_completed + r2.quest_completed + r3.quest_completed
        )
        assert "daily_apply_3" in completed
        total = await conn.fetchval(
            "SELECT current_xp FROM user_progress WHERE user_id = $1",
            TEST_USER_ID,
        )
        assert total == 3 * gamify.XP_REWARDS["app.added"] + spec.reward_xp

    _with_conn(go)


def test_get_state_seeds_progress_row() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        async with conn.transaction():
            state = await gamify.get_state(conn, TEST_USER_ID)
        assert state.level == 1
        assert state.xp == 0
        assert state.streak == 0

    _with_conn(go)
