"""Repository-level tests for M10 study tracker.

Covers CRUD at all three levels, the revise() side effects, the
nested-tree assembly in list_plan(), cross-user isolation, soft-delete
cascade, and tag round-tripping.

Style mirrors test_pilot_writes.py — direct asyncpg connection inside
each test via the _with_conn helper, scoped to TEST_USER_ID.
"""
from __future__ import annotations

import asyncio
from typing import Awaitable, Callable

import asyncpg

from app.config import settings
from app.exceptions import NotFound
from app.models import (
    StudySectionCreate,
    StudySectionUpdate,
    StudySubsectionCreate,
    StudyTopicCreate,
    StudyTopicUpdate,
)
from app.repositories import study as repo
from tests.conftest import TEST_USER_ID


def _with_conn(body: Callable[[asyncpg.Connection], Awaitable[None]]) -> None:
    async def runner() -> None:
        conn = await asyncpg.connect(str(settings.database_url))
        try:
            await body(conn)
        finally:
            await conn.close()

    asyncio.run(runner())


async def _seed_chain(
    conn: asyncpg.Connection,
) -> tuple[int, int, int]:
    """Create a section + subsection + topic. Returns their ids."""
    sec = await repo.create_section(
        conn, TEST_USER_ID, StudySectionCreate(name="Backend"),
    )
    sub = await repo.create_subsection(
        conn, sec.id, TEST_USER_ID, StudySubsectionCreate(name="Spring Boot"),
    )
    topic = await repo.create_topic(
        conn, sub.id, TEST_USER_ID,
        StudyTopicCreate(title="Dependency Injection"),
    )
    return sec.id, sub.id, topic.id


# ── sections ─────────────────────────────────────────────────────────


def test_create_section_appends_at_end() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        a = await repo.create_section(
            conn, TEST_USER_ID, StudySectionCreate(name="Backend"),
        )
        b = await repo.create_section(
            conn, TEST_USER_ID, StudySectionCreate(name="Frontend"),
        )
        assert b.position == a.position + 1

    _with_conn(go)


def test_update_section_changes_name() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        sec = await repo.create_section(
            conn, TEST_USER_ID, StudySectionCreate(name="Java"),
        )
        updated = await repo.update_section(
            conn, sec.id, TEST_USER_ID, StudySectionUpdate(name="Java SE"),
        )
        assert updated.name == "Java SE"

    _with_conn(go)


def test_delete_section_cascades_softly() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        sec_id, sub_id, topic_id = await _seed_chain(conn)
        await repo.soft_delete_section(conn, sec_id, TEST_USER_ID)
        # The physical rows must still exist with deleted_at set.
        for table, row_id in (
            ("study_sections", sec_id),
            ("study_subsections", sub_id),
            ("study_topics", topic_id),
        ):
            row = await conn.fetchrow(
                f"SELECT deleted_at FROM {table} WHERE id = $1", row_id,
            )
            assert row is not None
            assert row["deleted_at"] is not None
        # And neither layer is visible to normal reads.
        try:
            await repo.get_section(conn, sec_id, TEST_USER_ID)
            raise AssertionError("section should be hidden")
        except NotFound:
            pass

    _with_conn(go)


# ── subsections ──────────────────────────────────────────────────────


def test_subsection_requires_user_owned_section() -> None:
    """Cross-section spoofing must raise NotFound."""

    async def go(conn: asyncpg.Connection) -> None:
        sec = await repo.create_section(
            conn, TEST_USER_ID, StudySectionCreate(name="X"),
        )
        try:
            await repo.create_subsection(
                conn,
                section_id=sec.id,
                # Different user — should reject because the section isn't theirs.
                user_id=TEST_USER_ID + 9_999_999,
                data=StudySubsectionCreate(name="never"),
            )
            raise AssertionError("must NotFound on cross-user section ref")
        except NotFound:
            pass

    _with_conn(go)


# ── topics ───────────────────────────────────────────────────────────


def test_create_topic_with_tags_round_trips() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        _, sub_id, _ = await _seed_chain(conn)
        topic = await repo.create_topic(
            conn, sub_id, TEST_USER_ID,
            StudyTopicCreate(
                title="Spring DI",
                notes="scopes, qualifiers",
                kind="revise",
                tags=["interview-critical", "spring"],
            ),
        )
        assert topic.kind == "revise"
        assert topic.tags == ["interview-critical", "spring"]
        # Re-fetch confirms the array survived the DB round-trip.
        fetched = await repo.get_topic(conn, topic.id, TEST_USER_ID)
        assert fetched.tags == ["interview-critical", "spring"]

    _with_conn(go)


def test_topic_defaults_to_learn_todo() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        _, sub_id, topic_id = await _seed_chain(conn)
        t = await repo.get_topic(conn, topic_id, TEST_USER_ID)
        assert t.kind == "learn"
        assert t.status == "todo"
        assert t.revision_count == 0
        assert t.last_revised_at is None

    _with_conn(go)


def test_update_topic_status_directly() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        _, _, topic_id = await _seed_chain(conn)
        out = await repo.update_topic(
            conn, topic_id, TEST_USER_ID,
            StudyTopicUpdate(status="in_progress"),
        )
        assert out.status == "in_progress"

    _with_conn(go)


# ── revise() side effects ────────────────────────────────────────────


def test_revise_marks_done_and_increments_counter() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        _, _, topic_id = await _seed_chain(conn)
        out = await repo.revise_topic(conn, topic_id, TEST_USER_ID)
        assert out.status == "done"
        assert out.revision_count == 1
        assert out.last_revised_at is not None

    _with_conn(go)


def test_revise_three_times_does_not_master_when_topic_is_new() -> None:
    """Mastery requires both revision_count >= 3 AND age >= 7 days.

    A freshly created topic revised three times remains 'done' — we
    intentionally don't let a user farm mastery on a topic they just
    learned 30 seconds ago.
    """

    async def go(conn: asyncpg.Connection) -> None:
        _, _, topic_id = await _seed_chain(conn)
        await repo.revise_topic(conn, topic_id, TEST_USER_ID)
        await repo.revise_topic(conn, topic_id, TEST_USER_ID)
        out = await repo.revise_topic(conn, topic_id, TEST_USER_ID)
        assert out.revision_count == 3
        assert out.status == "done"  # not mastered — too new

    _with_conn(go)


def test_revise_three_times_on_old_topic_promotes_to_mastered() -> None:
    """Same flow but on a topic backdated past the mastery age threshold."""

    async def go(conn: asyncpg.Connection) -> None:
        _, _, topic_id = await _seed_chain(conn)
        # Backdate the topic's created_at so the mastery age branch fires.
        await conn.execute(
            "UPDATE study_topics SET created_at = NOW() - INTERVAL '30 days' "
            "WHERE id = $1",
            topic_id,
        )
        await repo.revise_topic(conn, topic_id, TEST_USER_ID)
        await repo.revise_topic(conn, topic_id, TEST_USER_ID)
        out = await repo.revise_topic(conn, topic_id, TEST_USER_ID)
        assert out.status == "mastered"

    _with_conn(go)


def test_unmark_resets_status_but_preserves_counter() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        _, _, topic_id = await _seed_chain(conn)
        await repo.revise_topic(conn, topic_id, TEST_USER_ID)
        out = await repo.unmark_topic(conn, topic_id, TEST_USER_ID)
        assert out.status == "todo"
        assert out.revision_count == 1  # history preserved

    _with_conn(go)


# ── tree assembly + progress ─────────────────────────────────────────


def test_list_plan_assembles_nested_tree() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        sec = await repo.create_section(
            conn, TEST_USER_ID, StudySectionCreate(name="Backend"),
        )
        sub = await repo.create_subsection(
            conn, sec.id, TEST_USER_ID, StudySubsectionCreate(name="Spring"),
        )
        await repo.create_topic(
            conn, sub.id, TEST_USER_ID, StudyTopicCreate(title="A"),
        )
        await repo.create_topic(
            conn, sub.id, TEST_USER_ID, StudyTopicCreate(title="B"),
        )
        plan = await repo.list_plan(conn, TEST_USER_ID)
        assert len(plan.sections) == 1
        assert plan.sections[0].name == "Backend"
        assert len(plan.sections[0].subsections) == 1
        assert len(plan.sections[0].subsections[0].topics) == 2
        # Positions preserved.
        titles = [t.title for t in plan.sections[0].subsections[0].topics]
        assert titles == ["A", "B"]

    _with_conn(go)


def test_progress_counts_each_status() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        _, sub_id, _ = await _seed_chain(conn)
        # Add 2 more topics and revise one.
        t2 = await repo.create_topic(
            conn, sub_id, TEST_USER_ID, StudyTopicCreate(title="T2"),
        )
        await repo.create_topic(
            conn, sub_id, TEST_USER_ID, StudyTopicCreate(title="T3"),
        )
        await repo.revise_topic(conn, t2.id, TEST_USER_ID)
        p = await repo.progress(conn, TEST_USER_ID)
        assert p["total_topics"] == 3
        assert p["todo"] == 2
        assert p["done"] == 1
        assert p["mastered"] == 0
        assert p["revisions_this_week"] >= 1

    _with_conn(go)


# ── cross-user isolation ─────────────────────────────────────────────


def test_other_user_cannot_see_my_plan() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        await _seed_chain(conn)
        other_plan = await repo.list_plan(conn, TEST_USER_ID + 9_999_999)
        assert other_plan.sections == []

    _with_conn(go)


def test_other_user_cannot_revise_my_topic() -> None:
    async def go(conn: asyncpg.Connection) -> None:
        _, _, topic_id = await _seed_chain(conn)
        try:
            await repo.revise_topic(
                conn, topic_id, TEST_USER_ID + 9_999_999,
            )
            raise AssertionError("must NotFound across users")
        except NotFound:
            pass

    _with_conn(go)
