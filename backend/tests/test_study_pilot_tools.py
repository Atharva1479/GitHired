"""Phase 5 — study pilot-tool tests.

Covers: read tools, write tools, by-name lookup ambiguity, and
confirmation-required tools (delete_*, generate_*).

Follows the _with_conn pattern from test_study_repository.py — each test
opens a direct asyncpg connection so we exercise the full dispatch() stack
without going through FastAPI routing.
"""
from __future__ import annotations

import asyncio
from typing import Awaitable, Callable

import asyncpg

from app.config import settings
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


async def _dispatch(conn, tool_name, **kwargs):
    ctx = ToolContext(user_id=TEST_USER_ID, conn=conn)
    return await dispatch(tool_name, kwargs, ctx)


async def _make_section(conn, section_name="Backend") -> int:
    r = await _dispatch(conn, "add_study_section", name=section_name)
    assert r.get("ok"), f"add_study_section failed: {r}"
    return r["section"]["id"]


async def _make_subsection(conn, section_id, subsection_name="Spring Boot") -> int:
    r = await _dispatch(conn, "add_study_subsection",
                        section_id=section_id, name=subsection_name)
    assert r.get("ok"), f"add_study_subsection failed: {r}"
    return r["subsection"]["id"]


async def _make_topic(conn, subsection_id, topic_title="Dependency Injection") -> int:
    r = await _dispatch(conn, "add_study_topic",
                        subsection_id=subsection_id, title=topic_title)
    assert r.get("ok"), f"add_study_topic failed: {r}"
    return r["topic"]["id"]


# ── read tools ────────────────────────────────────────────────────────


def test_list_study_plan_empty():
    async def go(conn):
        r = await _dispatch(conn, "list_study_plan")
        assert "sections" in r
        assert r["sections"] == []

    _with_conn(go)


def test_list_study_plan_returns_tree():
    async def go(conn):
        sec_id = await _make_section(conn, "Language: Java")
        sub_id = await _make_subsection(conn, sec_id, "Core Java")
        await _make_topic(conn, sub_id, "Generics")

        r = await _dispatch(conn, "list_study_plan")
        assert len(r["sections"]) == 1
        sec = r["sections"][0]
        assert sec["name"] == "Language: Java"
        assert len(sec["subsections"]) == 1
        assert sec["subsections"][0]["topics"][0]["title"] == "Generics"

    _with_conn(go)


def test_get_study_progress_empty():
    async def go(conn):
        r = await _dispatch(conn, "get_study_progress")
        assert r["total_topics"] == 0
        assert r["due_for_review"] == 0

    _with_conn(go)


def test_get_study_progress_counts():
    async def go(conn):
        sec_id = await _make_section(conn, "DB")
        sub_id = await _make_subsection(conn, sec_id, "SQL")
        t_id = await _make_topic(conn, sub_id, "Indexes")

        await _dispatch(conn, "mark_topic_revised", topic_id=t_id)

        r = await _dispatch(conn, "get_study_progress")
        assert r["total_topics"] == 1
        assert r["done"] == 1
        assert r["revisions_this_week"] == 1

    _with_conn(go)


def test_list_due_topics_none_initially():
    async def go(conn):
        r = await _dispatch(conn, "list_due_topics")
        assert r["count"] == 0

    _with_conn(go)


# ── write tools — add ────────────────────────────────────────────────


def test_add_study_section():
    async def go(conn):
        r = await _dispatch(conn, "add_study_section", name="Frontend")
        assert r["ok"] is True
        assert r["section"]["name"] == "Frontend"
        assert r["section"]["id"] > 0

    _with_conn(go)


def test_add_study_section_missing_name():
    async def go(conn):
        r = await _dispatch(conn, "add_study_section", name="")
        assert "error" in r

    _with_conn(go)


def test_add_study_subsection_by_section_id():
    async def go(conn):
        sec_id = await _make_section(conn)
        r = await _dispatch(conn, "add_study_subsection",
                            section_id=sec_id, name="Microservices")
        assert r["ok"] is True
        assert r["subsection"]["section_id"] == sec_id

    _with_conn(go)


def test_add_study_subsection_by_section_name():
    async def go(conn):
        await _make_section(conn, "Backend")
        r = await _dispatch(conn, "add_study_subsection",
                            section_name="backend", name="REST APIs")
        assert r["ok"] is True
        assert r["subsection"]["name"] == "REST APIs"

    _with_conn(go)


def test_add_study_topic_by_subsection_id():
    async def go(conn):
        sec_id = await _make_section(conn)
        sub_id = await _make_subsection(conn, sec_id)
        r = await _dispatch(conn, "add_study_topic",
                            subsection_id=sub_id, title="Bean lifecycle")
        assert r["ok"] is True
        assert r["topic"]["status"] == "todo"

    _with_conn(go)


def test_add_study_topic_by_names():
    async def go(conn):
        sec_id = await _make_section(conn, "Backend")
        await _make_subsection(conn, sec_id, "Spring Boot")
        r = await _dispatch(conn, "add_study_topic",
                            section_name="Backend",
                            subsection_name="Spring Boot",
                            title="Actuator endpoints")
        assert r["ok"] is True
        assert r["topic"]["title"] == "Actuator endpoints"

    _with_conn(go)


# ── mark_topic_revised ────────────────────────────────────────────────


def test_mark_topic_revised_by_id():
    async def go(conn):
        sec_id = await _make_section(conn)
        sub_id = await _make_subsection(conn, sec_id)
        t_id = await _make_topic(conn, sub_id, "Auto-configuration")

        r = await _dispatch(conn, "mark_topic_revised", topic_id=t_id)
        assert r["ok"] is True
        assert r["topic"]["status"] == "done"
        assert r["topic"]["revision_count"] == 1
        assert r["xp_gained"] > 0

    _with_conn(go)


def test_mark_topic_revised_by_title():
    async def go(conn):
        sec_id = await _make_section(conn)
        sub_id = await _make_subsection(conn, sec_id)
        await _make_topic(conn, sub_id, "Profiles and environments")

        r = await _dispatch(conn, "mark_topic_revised", title="Profiles")
        assert r["ok"] is True
        assert r["topic"]["revision_count"] == 1

    _with_conn(go)


def test_unmark_study_topic():
    async def go(conn):
        sec_id = await _make_section(conn)
        sub_id = await _make_subsection(conn, sec_id)
        t_id = await _make_topic(conn, sub_id, "Bean scopes")

        await _dispatch(conn, "mark_topic_revised", topic_id=t_id)
        r = await _dispatch(conn, "unmark_study_topic", topic_id=t_id)
        assert r["ok"] is True
        assert r["topic"]["status"] == "todo"

    _with_conn(go)


# ── ambiguity ────────────────────────────────────────────────────────


def test_ambiguous_section_name():
    async def go(conn):
        await _make_section(conn, "Backend: Java")
        await _make_section(conn, "Backend: Python")

        r = await _dispatch(conn, "add_study_subsection",
                            section_name="Backend", name="REST")
        assert r.get("ambiguous") is True
        assert len(r["candidates"]) == 2
        assert "hint" in r

    _with_conn(go)


def test_ambiguous_topic_title():
    async def go(conn):
        sec_id = await _make_section(conn)
        sub_id = await _make_subsection(conn, sec_id)
        await _make_topic(conn, sub_id, "Dependency Injection — basics")
        await _make_topic(conn, sub_id, "Dependency Injection — advanced")

        r = await _dispatch(conn, "mark_topic_revised",
                            title="Dependency Injection")
        assert r.get("ambiguous") is True
        assert len(r["candidates"]) == 2

    _with_conn(go)


# ── confirmation-required tools ───────────────────────────────────────


def test_delete_study_section_needs_confirmation():
    async def go(conn):
        sec_id = await _make_section(conn)
        r = await _dispatch(conn, "delete_study_section", id=sec_id)
        assert r.get("needs_confirmation") is True
        assert "summary" in r
        assert "confirm_token" in r

    _with_conn(go)


def test_delete_study_section_confirmed():
    async def go(conn):
        sec_id = await _make_section(conn, "ToDelete")
        r1 = await _dispatch(conn, "delete_study_section", id=sec_id)
        token = r1["confirm_token"]
        r2 = await _dispatch(conn, "delete_study_section",
                             id=sec_id, confirm_token=token)
        assert r2.get("ok") is True
        row = await conn.fetchrow(
            "SELECT deleted_at FROM study_sections WHERE id=$1", sec_id
        )
        assert row["deleted_at"] is not None

    _with_conn(go)


def test_delete_study_topic_needs_confirmation():
    async def go(conn):
        sec_id = await _make_section(conn)
        sub_id = await _make_subsection(conn, sec_id)
        t_id = await _make_topic(conn, sub_id)
        r = await _dispatch(conn, "delete_study_topic", id=t_id)
        assert r.get("needs_confirmation") is True

    _with_conn(go)


def test_generate_study_plan_needs_confirmation():
    async def go(conn):
        r = await _dispatch(conn, "generate_study_plan",
                            role="Java Backend Developer")
        assert r.get("needs_confirmation") is True
        assert "summary" in r
        assert "Java Backend Developer" in r["summary"]

    _with_conn(go)


def test_generate_topics_needs_confirmation():
    async def go(conn):
        sec_id = await _make_section(conn)
        sub_id = await _make_subsection(conn, sec_id, "Spring Boot")
        r = await _dispatch(conn, "generate_topics_for_subsection",
                            subsection_id=sub_id, count=5)
        assert r.get("needs_confirmation") is True
        assert "Spring Boot" in r["summary"]

    _with_conn(go)
