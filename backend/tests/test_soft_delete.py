"""Soft-delete contract tests.

These tests verify the project-wide policy that records are NEVER hard-
deleted: every "delete" operation sets deleted_at and the row physically
persists in the database. Reads must filter the row out via
`deleted_at IS NULL`; INSERTs against tables with composite PKs must
resurrect on conflict.

Covered:
- Application delete via the voice agent (soft delete, row persists)
- Referral delete via the voice agent (soft delete, row persists)
- Referral ↔ Application link unlink (soft delete, row persists)
- Link resurrection: re-linking after unlink reuses the existing row
- pilot_confirmations one-shot consume is implemented via UPDATE, not
  DELETE, and the consumed row stays in the table for audit
- Repository deletes (the API path) set deleted_at
"""
from __future__ import annotations

import asyncio
from typing import Awaitable, Callable

import asyncpg

from app.config import settings
from app.repositories import applications as apps_repo
from app.repositories import referrals as refs_repo
from app.services.pilot_tools import ToolContext, dispatch
from tests.conftest import TEST_USER_ID


def _with_conn(body: Callable[[asyncpg.Connection], Awaitable[None]]) -> None:
    async def runner() -> None:
        conn = await asyncpg.connect(str(settings.database_url))
        try:
            await body(conn)
        finally:
            await conn.close()

    asyncio.run(runner())


def _ctx(conn: asyncpg.Connection, user_id: int = TEST_USER_ID) -> ToolContext:
    return ToolContext(user_id=user_id, conn=conn)


# ──────────────────── applications ────────────────────────────────────


def test_delete_application_via_voice_agent_is_soft_delete() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        created = await dispatch(
            "add_application", {"company": "Acme", "role": "SWE"}, _ctx(conn),
        )
        app_id = created["application"]["id"]

        confirm = await dispatch(
            "delete_application", {"id": app_id}, _ctx(conn),
        )
        result = await dispatch(
            "delete_application",
            {"id": app_id, "confirm_token": confirm["confirm_token"]},
            _ctx(conn),
        )
        assert result.get("ok") is True

        # Row must still exist with deleted_at set — NOT physically removed.
        row = await conn.fetchrow(
            "SELECT deleted_at FROM applications WHERE id = $1", app_id,
        )
        assert row is not None, "application row was hard-deleted"
        assert row["deleted_at"] is not None, "deleted_at not set"

        # And it must not appear in normal reads.
        visible = await conn.fetchval(
            "SELECT 1 FROM applications "
            "WHERE id = $1 AND deleted_at IS NULL",
            app_id,
        )
        assert visible is None

    _with_conn(go)


def test_apps_repo_delete_is_soft() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        from app.models import ApplicationCreate

        created = await apps_repo.create_application(
            conn, TEST_USER_ID,
            ApplicationCreate(  # type: ignore[arg-type]
                company="Repo", role="Dev",
                source="Other",
                applied_date=__import__("datetime").date.today(),
            ),
        )
        await apps_repo.soft_delete_application(conn, created.id, TEST_USER_ID)

        row = await conn.fetchrow(
            "SELECT deleted_at FROM applications WHERE id = $1", created.id,
        )
        assert row is not None
        assert row["deleted_at"] is not None

    _with_conn(go)


# ──────────────────── referrals ────────────────────────────────────────


def test_delete_referral_via_voice_agent_is_soft_delete() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        created = await dispatch(
            "add_referral",
            {"name": "Priya", "company": "Acme", "target_role": "SWE"},
            _ctx(conn),
        )
        ref_id = created["referral"]["id"]

        confirm = await dispatch(
            "delete_referral", {"id": ref_id}, _ctx(conn),
        )
        result = await dispatch(
            "delete_referral",
            {"id": ref_id, "confirm_token": confirm["confirm_token"]},
            _ctx(conn),
        )
        assert result.get("ok") is True

        row = await conn.fetchrow(
            "SELECT deleted_at FROM referral_contacts WHERE id = $1", ref_id,
        )
        assert row is not None
        assert row["deleted_at"] is not None

    _with_conn(go)


# ──────────────────── referral ↔ application link ───────────────────


def test_unlink_referral_is_soft_delete_and_row_persists() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        app = await dispatch(
            "add_application", {"company": "S", "role": "X"}, _ctx(conn),
        )
        ref = await dispatch(
            "add_referral",
            {"name": "P", "company": "S", "target_role": "X"},
            _ctx(conn),
        )
        ref_id = ref["referral"]["id"]
        app_id = app["application"]["id"]

        await dispatch(
            "link_referral_to_application",
            {"referral_id": ref_id, "application_id": app_id},
            _ctx(conn),
        )
        await dispatch(
            "unlink_referral_from_application",
            {"referral_id": ref_id, "application_id": app_id},
            _ctx(conn),
        )

        # The link row must physically still be there, just with deleted_at.
        row = await conn.fetchrow(
            "SELECT deleted_at FROM referral_application_link "
            "WHERE referral_id = $1 AND application_id = $2",
            ref_id, app_id,
        )
        assert row is not None, "link row was hard-deleted"
        assert row["deleted_at"] is not None, "deleted_at not set"

        # Linked-applications query must skip it.
        linked = await refs_repo.list_linked_applications(
            conn, ref_id, TEST_USER_ID,
        )
        assert linked == []

    _with_conn(go)


def test_relink_after_unlink_resurrects_existing_row() -> None:
    """Re-link must UPDATE the soft-deleted row, not create a duplicate."""

    async def go(conn: asyncpg.Connection) -> None:
        app = await dispatch(
            "add_application", {"company": "S", "role": "X"}, _ctx(conn),
        )
        ref = await dispatch(
            "add_referral",
            {"name": "P", "company": "S", "target_role": "X"},
            _ctx(conn),
        )
        ref_id = ref["referral"]["id"]
        app_id = app["application"]["id"]

        await dispatch(
            "link_referral_to_application",
            {"referral_id": ref_id, "application_id": app_id},
            _ctx(conn),
        )
        await dispatch(
            "unlink_referral_from_application",
            {"referral_id": ref_id, "application_id": app_id},
            _ctx(conn),
        )
        # Re-link.
        await dispatch(
            "link_referral_to_application",
            {"referral_id": ref_id, "application_id": app_id},
            _ctx(conn),
        )

        # Only one physical row for the (referral, application) pair.
        cnt = await conn.fetchval(
            "SELECT COUNT(*) FROM referral_application_link "
            "WHERE referral_id = $1 AND application_id = $2",
            ref_id, app_id,
        )
        assert cnt == 1

        # And it must be live (deleted_at cleared).
        live = await conn.fetchval(
            "SELECT deleted_at FROM referral_application_link "
            "WHERE referral_id = $1 AND application_id = $2",
            ref_id, app_id,
        )
        assert live is None

        # list_linked_applications must see it again.
        linked = await refs_repo.list_linked_applications(
            conn, ref_id, TEST_USER_ID,
        )
        assert len(linked) == 1
        assert linked[0].id == app_id

    _with_conn(go)


# ──────────────────── pilot_confirmations ───────────────────────────


def test_pilot_confirmation_consume_is_soft_delete() -> None:
    """Token rows persist after consume — never hard-deleted."""

    async def go(conn: asyncpg.Connection) -> None:
        created = await dispatch(
            "add_application", {"company": "Acme", "role": "SWE"}, _ctx(conn),
        )
        app_id = created["application"]["id"]

        issued = await dispatch(
            "delete_application", {"id": app_id}, _ctx(conn),
        )
        token = issued["confirm_token"]

        # Token row exists, undeleted.
        before = await conn.fetchrow(
            "SELECT deleted_at FROM pilot_confirmations WHERE token = $1",
            token,
        )
        assert before is not None
        assert before["deleted_at"] is None

        # Consume.
        await dispatch(
            "delete_application",
            {"id": app_id, "confirm_token": token},
            _ctx(conn),
        )

        # Row still exists, deleted_at set.
        after = await conn.fetchrow(
            "SELECT deleted_at FROM pilot_confirmations WHERE token = $1",
            token,
        )
        assert after is not None, "confirmation row was hard-deleted"
        assert after["deleted_at"] is not None, "deleted_at not set"

    _with_conn(go)
