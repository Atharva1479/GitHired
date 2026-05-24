"""Tests for the Phase 2 Pilot write tools + confirmation rail."""
from __future__ import annotations

import asyncio
import datetime as dt
from typing import Awaitable, Callable

import asyncpg

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


async def _row_exists(
    conn: asyncpg.Connection, table: str, app_id: int, user_id: int = TEST_USER_ID,
) -> bool:
    val = await conn.fetchval(
        f"SELECT 1 FROM {table} WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL",
        app_id, user_id,
    )
    return val is not None


# ───────────────────────────── add_application ────────────────────────────


def test_add_application_creates_row_with_defaults() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        out = await dispatch(
            "add_application",
            {"company": "Stripe", "role": "Software Engineer"},
            _ctx(conn),
        )
        assert out["ok"] is True
        app_id = out["application"]["id"]
        row = await conn.fetchrow(
            "SELECT company, role, source, applied_date FROM applications "
            "WHERE id = $1",
            app_id,
        )
        assert row["company"] == "Stripe"
        assert row["source"] == "Other"  # default
        assert row["applied_date"] == dt.date.today()  # default

    _with_conn(go)


def test_add_application_rejects_missing_required_fields() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        out = await dispatch(
            "add_application", {"company": "Stripe"}, _ctx(conn)
        )
        assert "error" in out

    _with_conn(go)


def test_add_application_rewards_xp() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        await dispatch(
            "add_application",
            {"company": "Stripe", "role": "SWE"},
            _ctx(conn),
        )
        xp = await conn.fetchval(
            "SELECT current_xp FROM user_progress WHERE user_id = $1",
            TEST_USER_ID,
        )
        assert xp == 10  # XP_REWARDS["app.added"]

    _with_conn(go)


# ───────────────────────────── update_application ──────────────────────────


def test_update_application_non_destructive_status_move_no_confirm() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        created = await dispatch(
            "add_application",
            {"company": "Stripe", "role": "SWE"},
            _ctx(conn),
        )
        app_id = created["application"]["id"]
        out = await dispatch(
            "move_application_status",
            {"id": app_id, "new_status": "Screening"},
            _ctx(conn),
        )
        assert out.get("ok") is True
        assert out["application"]["status"] == "Screening"

    _with_conn(go)


def test_update_application_to_rejected_requires_confirmation() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        created = await dispatch(
            "add_application",
            {"company": "Stripe", "role": "SWE"},
            _ctx(conn),
        )
        app_id = created["application"]["id"]
        out = await dispatch(
            "move_application_status",
            {"id": app_id, "new_status": "Rejected"},
            _ctx(conn),
        )
        assert out.get("needs_confirmation") is True
        assert "confirm_token" in out

        # Status should NOT have changed yet.
        row = await conn.fetchrow(
            "SELECT status FROM applications WHERE id = $1", app_id,
        )
        assert row["status"] == "Applied"

    _with_conn(go)


def test_confirmation_token_consumed_completes_action() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        created = await dispatch(
            "add_application",
            {"company": "Stripe", "role": "SWE"},
            _ctx(conn),
        )
        app_id = created["application"]["id"]

        first = await dispatch(
            "move_application_status",
            {"id": app_id, "new_status": "Rejected"},
            _ctx(conn),
        )
        token = first["confirm_token"]

        second = await dispatch(
            "move_application_status",
            {"id": app_id, "new_status": "Rejected", "confirm_token": token},
            _ctx(conn),
        )
        assert second.get("ok") is True
        assert second["application"]["status"] == "Rejected"

    _with_conn(go)


def test_confirmation_token_is_one_shot() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        created = await dispatch(
            "add_application", {"company": "X", "role": "Y"}, _ctx(conn)
        )
        app_id = created["application"]["id"]
        first = await dispatch(
            "delete_application", {"id": app_id}, _ctx(conn)
        )
        token = first["confirm_token"]
        # Use the token once.
        ok = await dispatch(
            "delete_application",
            {"id": app_id, "confirm_token": token},
            _ctx(conn),
        )
        assert ok.get("ok") is True

        # Token must not work a second time.
        replay = await dispatch(
            "delete_application",
            {"id": app_id, "confirm_token": token},
            _ctx(conn),
        )
        assert "error" in replay

    _with_conn(go)


def test_confirmation_token_rejects_mismatched_args() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        a = await dispatch(
            "add_application", {"company": "A", "role": "x"}, _ctx(conn)
        )
        b = await dispatch(
            "add_application", {"company": "B", "role": "y"}, _ctx(conn)
        )
        a_id, b_id = a["application"]["id"], b["application"]["id"]

        # Issue token for deleting A.
        first = await dispatch(
            "delete_application", {"id": a_id}, _ctx(conn)
        )
        token = first["confirm_token"]

        # Try to use that token to delete B — different args → must fail.
        attack = await dispatch(
            "delete_application",
            {"id": b_id, "confirm_token": token},
            _ctx(conn),
        )
        assert "error" in attack

        # B must still exist.
        still_there = await conn.fetchval(
            "SELECT 1 FROM applications WHERE id = $1 AND deleted_at IS NULL",
            b_id,
        )
        assert still_there is not None

    _with_conn(go)


def test_confirmation_token_rejects_cross_user_use() -> None:
    """A token issued for user A must not delete user B's row."""

    async def go(conn: asyncpg.Connection) -> None:
        # Seed an app for TEST_USER_ID.
        own = await dispatch(
            "add_application", {"company": "Z", "role": "z"}, _ctx(conn)
        )
        own_id = own["application"]["id"]

        # Issue a confirm token via TEST_USER_ID context.
        first = await dispatch(
            "delete_application", {"id": own_id}, _ctx(conn)
        )
        token = first["confirm_token"]

        # Now switch to a DIFFERENT user_id and try to use the same token.
        other_ctx = _ctx(conn, user_id=TEST_USER_ID + 9_999_999)
        attack = await dispatch(
            "delete_application",
            {"id": own_id, "confirm_token": token},
            other_ctx,
        )
        assert "error" in attack

        # The original user can still use their token.
        legit = await dispatch(
            "delete_application",
            {"id": own_id, "confirm_token": token},
            _ctx(conn),
        )
        assert legit.get("ok") is True

    _with_conn(go)


# ───────────────────────────── delete_application ─────────────────────────


def test_delete_application_requires_confirmation() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        created = await dispatch(
            "add_application", {"company": "X", "role": "Y"}, _ctx(conn),
        )
        app_id = created["application"]["id"]
        out = await dispatch("delete_application", {"id": app_id}, _ctx(conn))
        assert out.get("needs_confirmation") is True

    _with_conn(go)


# ───────────────────────────── add_note ──────────────────────────────────


def test_add_note_appends_with_date_stamp() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        created = await dispatch(
            "add_application", {"company": "X", "role": "Y"}, _ctx(conn)
        )
        app_id = created["application"]["id"]
        await dispatch(
            "add_note_to_application",
            {"id": app_id, "text": "Recruiter said reply by Friday."},
            _ctx(conn),
        )
        notes = await conn.fetchval(
            "SELECT notes FROM applications WHERE id = $1", app_id,
        )
        assert "Recruiter said reply by Friday" in notes
        assert dt.date.today().isoformat() in notes

    _with_conn(go)


# ───────────────────────────── referrals ──────────────────────────────────


def test_add_referral_creates_row() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        out = await dispatch(
            "add_referral",
            {"name": "Priya Sharma", "company": "Stripe", "target_role": "SWE"},
            _ctx(conn),
        )
        assert out["ok"] is True
        assert out["referral"]["connection_status"] == "Request Sent"

    _with_conn(go)


def test_delete_referral_requires_confirmation() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        created = await dispatch(
            "add_referral",
            {"name": "P", "company": "S", "target_role": "R"},
            _ctx(conn),
        )
        ref_id = created["referral"]["id"]
        out = await dispatch("delete_referral", {"id": ref_id}, _ctx(conn))
        assert out.get("needs_confirmation") is True

    _with_conn(go)


def test_mark_referral_accepted_moves_status() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        created = await dispatch(
            "add_referral",
            {"name": "P", "company": "S", "target_role": "R"},
            _ctx(conn),
        )
        ref_id = created["referral"]["id"]
        out = await dispatch(
            "mark_referral_accepted", {"id": ref_id}, _ctx(conn)
        )
        assert out["ok"] is True
        assert out["referral"]["connection_status"] == "Accepted"

    _with_conn(go)


def test_link_and_unlink_referral_to_application() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        app = await dispatch(
            "add_application", {"company": "S", "role": "X"}, _ctx(conn)
        )
        ref = await dispatch(
            "add_referral",
            {"name": "P", "company": "S", "target_role": "X"},
            _ctx(conn),
        )
        out = await dispatch(
            "link_referral_to_application",
            {
                "referral_id": ref["referral"]["id"],
                "application_id": app["application"]["id"],
            },
            _ctx(conn),
        )
        assert out["ok"] is True

        unlink = await dispatch(
            "unlink_referral_from_application",
            {
                "referral_id": ref["referral"]["id"],
                "application_id": app["application"]["id"],
            },
            _ctx(conn),
        )
        assert unlink["ok"] is True

    _with_conn(go)
