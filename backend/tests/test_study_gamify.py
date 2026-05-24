"""M10 Phase 2 — gamify integration tests for the study tracker.

Covers:
  • XP awarded on first vs subsequent revisions
  • Idempotency of XP events (same ref_id cannot double-award)
  • Mastery event fires when topic reaches mastered status
  • Subsection completion cascade via the HTTP endpoint
  • Section completion cascade via the HTTP endpoint
  • Achievement unlocks: first_revision, first_mastered,
    subsection_master, section_master, syllabus_set
  • Quest progress for daily_revise_3

Uses the TestClient + the X-Gamify header pattern so the full
router path (repo → gamify → attach) is exercised end-to-end.
"""
from __future__ import annotations

import json
import datetime as dt

import asyncio
import asyncpg
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.models import (
    StudySectionCreate,
    StudySubsectionCreate,
    StudyTopicCreate,
)
from app.repositories import study as repo
from app.services import gamify
from tests.conftest import TEST_USER_ID


# ── helpers ─────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _gam(resp) -> dict:
    """Parse X-Gamify header; returns {} if absent (no-op result)."""
    raw = resp.headers.get("X-Gamify", "")
    return json.loads(raw) if raw else {}


def _seed_section(client: TestClient, name: str = "Backend") -> dict:
    return client.post("/api/study/sections", json={"name": name}).json()


def _seed_subsection(client: TestClient, section_id: int, name: str = "Spring Boot") -> dict:
    return client.post(
        f"/api/study/sections/{section_id}/subsections",
        json={"name": name},
    ).json()


def _seed_topic(client: TestClient, subsection_id: int, title: str = "DI") -> dict:
    return client.post(
        f"/api/study/subsections/{subsection_id}/topics",
        json={"title": title},
    ).json()


def _revise(client: TestClient, topic_id: int):
    return client.post(f"/api/study/topics/{topic_id}/revise")


# ── XP: first revision ───────────────────────────────────────────────


def test_first_revision_awards_5_xp(client: TestClient) -> None:
    sec = _seed_section(client)
    sub = _seed_subsection(client, sec["id"])
    topic = _seed_topic(client, sub["id"])

    r = _revise(client, topic["id"])
    assert r.status_code == 200
    gam = _gam(r)
    assert gam.get("xp_gained", 0) >= 5, f"expected ≥5 XP on first revision, got {gam}"


# ── XP: subsequent revision ──────────────────────────────────────────


def test_second_revision_awards_2_xp(client: TestClient) -> None:
    sec = _seed_section(client)
    sub = _seed_subsection(client, sec["id"])
    topic = _seed_topic(client, sub["id"])

    _revise(client, topic["id"])
    # Unmark so we can revise again.
    client.post(f"/api/study/topics/{topic['id']}/unmark")
    r = _revise(client, topic["id"])
    gam = _gam(r)
    # Second revision key awards 2 XP (plus any quest bonuses ≥ 2).
    assert gam.get("xp_gained", 0) >= 2


# ── idempotency ──────────────────────────────────────────────────────


def test_revise_xp_is_idempotent_per_count() -> None:
    """Same (topic_id, revision_count) pair cannot award XP twice."""
    async def go() -> None:
        conn = await asyncpg.connect(str(settings.database_url))
        try:
            async with conn.transaction():
                # First call awards XP.
                r1 = await gamify.record_event(
                    conn, TEST_USER_ID, "study.topic_revised_first",
                    ref_type="study_topic", ref_id=999_000_001,
                )
                assert not r1.duplicate
                assert r1.xp_gained == 5

                # Identical ref_id: must be a no-op duplicate.
                r2 = await gamify.record_event(
                    conn, TEST_USER_ID, "study.topic_revised_first",
                    ref_type="study_topic", ref_id=999_000_001,
                )
                assert r2.duplicate
                assert r2.xp_gained == 0
        finally:
            await conn.close()

    asyncio.run(go())


# ── mastery XP ───────────────────────────────────────────────────────


def test_mastery_awards_15_xp(client: TestClient) -> None:
    """topic.mastered fires when revision_count ≥ 3 and topic is old enough."""
    sec = _seed_section(client)
    sub = _seed_subsection(client, sec["id"])
    topic = _seed_topic(client, sub["id"])

    # Backdate the topic so the age threshold is satisfied.
    async def backdate() -> None:
        conn = await asyncpg.connect(str(settings.database_url))
        try:
            await conn.execute(
                "UPDATE study_topics SET created_at = NOW() - INTERVAL '30 days' "
                "WHERE id = $1",
                topic["id"],
            )
        finally:
            await conn.close()

    asyncio.run(backdate())

    for _ in range(2):
        _revise(client, topic["id"])
        client.post(f"/api/study/topics/{topic['id']}/unmark")

    r = _revise(client, topic["id"])
    assert r.status_code == 200
    body = r.json()
    assert body["new_status"] == "mastered"
    gam = _gam(r)
    # Mastery event wins the envelope merge (15 XP).
    assert gam.get("xp_gained", 0) >= 15


# ── completion cascade: subsection ──────────────────────────────────


def test_subsection_completion_awards_xp_and_achievement(client: TestClient) -> None:
    sec = _seed_section(client)
    sub = _seed_subsection(client, sec["id"])
    t1 = _seed_topic(client, sub["id"], "T1")
    t2 = _seed_topic(client, sub["id"], "T2")

    _revise(client, t1["id"])
    r = _revise(client, t2["id"])
    assert r.status_code == 200

    gam = _gam(r)
    # subsection_completed = 25 XP on top of the topic XP (section also
    # completes here since there is only one subsection, so 100 XP fires too).
    assert gam.get("xp_gained", 0) >= 25, f"expected subsection XP, got {gam}"
    unlocked = gam.get("unlocked", [])
    assert "subsection_master" in unlocked or "section_master" in unlocked, (
        f"expected subsection or section achievement, got {unlocked}"
    )


# ── completion cascade: section ──────────────────────────────────────


def test_section_completion_awards_xp_and_achievement(client: TestClient) -> None:
    sec = _seed_section(client)
    sub1 = _seed_subsection(client, sec["id"], "Sub1")
    sub2 = _seed_subsection(client, sec["id"], "Sub2")
    t1 = _seed_topic(client, sub1["id"], "T1")
    t2 = _seed_topic(client, sub2["id"], "T2")

    _revise(client, t1["id"])   # sub1 complete
    r = _revise(client, t2["id"])   # sub2 complete → section complete
    assert r.status_code == 200

    gam = _gam(r)
    assert gam.get("xp_gained", 0) >= 100, f"expected section XP, got {gam}"
    assert "section_master" in gam.get("unlocked", [])


# ── completion idempotency ────────────────────────────────────────────


def test_subsection_completion_is_idempotent(client: TestClient) -> None:
    """Revising the same topic a second time must not re-fire subsection XP."""
    sec = _seed_section(client)
    sub = _seed_subsection(client, sec["id"])
    topic = _seed_topic(client, sub["id"], "Solo")

    _revise(client, topic["id"])   # fires subsection_completed

    # Unmark then re-revise: subsection still complete but XP event duplicate.
    client.post(f"/api/study/topics/{topic['id']}/unmark")
    r = _revise(client, topic["id"])
    gam = _gam(r)
    # subsection_completed is a duplicate → only topic XP in envelope.
    assert gam.get("xp_gained", 0) < 25, (
        "subsection_completed should be idempotent, but extra XP fired"
    )


# ── achievements ─────────────────────────────────────────────────────


def test_first_revision_achievement_unlocks(client: TestClient) -> None:
    sec = _seed_section(client)
    sub = _seed_subsection(client, sec["id"])
    topic = _seed_topic(client, sub["id"])

    r = _revise(client, topic["id"])
    gam = _gam(r)
    assert "first_revision" in gam.get("unlocked", [])


def test_syllabus_set_achievement_on_first_section(client: TestClient) -> None:
    r = client.post("/api/study/sections", json={"name": "My Plan"})
    assert r.status_code == 201
    gam = _gam(r)
    assert "syllabus_set" in gam.get("unlocked", [])


def test_first_mastered_achievement_unlocks(client: TestClient) -> None:
    sec = _seed_section(client)
    sub = _seed_subsection(client, sec["id"])
    topic = _seed_topic(client, sub["id"])

    async def backdate() -> None:
        conn = await asyncpg.connect(str(settings.database_url))
        try:
            await conn.execute(
                "UPDATE study_topics SET created_at = NOW() - INTERVAL '30 days' "
                "WHERE id = $1",
                topic["id"],
            )
        finally:
            await conn.close()

    asyncio.run(backdate())

    for _ in range(2):
        _revise(client, topic["id"])
        client.post(f"/api/study/topics/{topic['id']}/unmark")

    r = _revise(client, topic["id"])
    gam = _gam(r)
    assert "first_mastered" in gam.get("unlocked", [])


# ── quest progress ────────────────────────────────────────────────────


def test_daily_revise_3_quest_completes(client: TestClient) -> None:
    """Revising 3 different topics in one day completes daily_revise_3."""
    from app.services import gamify as gam_svc
    import datetime as dt

    async def seed_quest() -> None:
        conn = await asyncpg.connect(str(settings.database_url))
        try:
            today = dt.date.today()
            midnight = dt.datetime.combine(
                today + dt.timedelta(days=1), dt.time.min
            )
            spec = gam_svc.QUESTS["daily_revise_3"]
            await conn.execute(
                """
                INSERT INTO quests (user_id, code, period, target, reward_xp, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (user_id, code, expires_at)
                    WHERE deleted_at IS NULL DO NOTHING
                """,
                TEST_USER_ID, spec.code, spec.period,
                spec.target, spec.reward_xp, midnight,
            )
        finally:
            await conn.close()

    asyncio.run(seed_quest())

    sec = _seed_section(client)
    sub = _seed_subsection(client, sec["id"])
    topics = [_seed_topic(client, sub["id"], f"Q{i}") for i in range(3)]

    for t in topics[:2]:
        r = _revise(client, t["id"])
        gam = _gam(r)
        assert "daily_revise_3" not in gam.get("quest_completed", [])

    r = _revise(client, topics[2]["id"])
    gam = _gam(r)
    assert "daily_revise_3" in gam.get("quest_completed", [])
