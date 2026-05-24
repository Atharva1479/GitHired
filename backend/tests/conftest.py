"""Pytest setup.

CRITICAL: tests must never touch real user data. We create a dedicated
pytest-only user on first import and scope every cleanup DELETE to that
user's id. user_id = 1 (the seed MVP user) and any real users are
isolated from the test suite.
"""
import os
from typing import Any

import psycopg
import pytest

os.environ.setdefault("GEMINI_API_KEY", "test-key")

from app.config import settings  # noqa: E402
from app.deps import get_user_id  # noqa: E402
from app.main import app  # noqa: E402

TEST_USER_EMAIL = "pytest+jp@local"
TEST_USER_DISPLAY = "Pytest Bot"


def _ensure_test_user(dsn: str) -> int:
    """Insert (or fetch) the dedicated pytest user, return its id."""
    with psycopg.connect(dsn, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (email, password_hash, display_name)
            VALUES (%s, '!', %s)
            ON CONFLICT (email)
            DO UPDATE SET display_name = EXCLUDED.display_name
            RETURNING id
            """,
            (TEST_USER_EMAIL, TEST_USER_DISPLAY),
        )
        row = cur.fetchone()
        assert row is not None
        return int(row[0])


TEST_USER_ID: int = _ensure_test_user(str(settings.database_url))
app.dependency_overrides[get_user_id] = lambda: TEST_USER_ID


class _DB:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        with psycopg.connect(self._dsn, autocommit=True) as conn, conn.cursor() as cur:
            cur.execute(sql, params)

    def fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
        with psycopg.connect(self._dsn, autocommit=True) as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()


@pytest.fixture(scope="session")
def db() -> _DB:
    return _DB(str(settings.database_url))


@pytest.fixture(scope="session")
def test_user_id() -> int:
    return TEST_USER_ID


@pytest.fixture(autouse=True)
def _clean(db: _DB) -> None:
    """Reset state for the synthetic pytest user between tests.

    Soft-delete only — no row is ever removed from the database, matching
    the project-wide no-hard-delete policy. Scoped strictly to the
    pytest+jp@local synthetic user, so real user data is untouched.

    Partial-unique indexes (created in migration 0013) ignore rows where
    deleted_at IS NOT NULL, so previously-cleaned rows do not block new
    INSERTs for the same logical key on the next test.

    user_progress is a per-user singleton with PRIMARY KEY (user_id); we
    reset its columns rather than soft-deleting because production code
    paths resurrect it via INSERT … ON CONFLICT DO UPDATE SET deleted_at
    = NULL, which would otherwise preserve stale XP/streak across tests.
    """
    uid = TEST_USER_ID
    db.execute(
        "UPDATE referral_application_link SET deleted_at = NOW() "
        "WHERE deleted_at IS NULL AND ("
        "  application_id IN (SELECT id FROM applications WHERE user_id = %s)"
        "  OR referral_id IN (SELECT id FROM referral_contacts WHERE user_id = %s)"
        ")",
        (uid, uid),
    )
    db.execute(
        "UPDATE nudges SET deleted_at = NOW() "
        "WHERE user_id = %s AND deleted_at IS NULL", (uid,),
    )
    db.execute(
        "UPDATE drafts SET deleted_at = NOW() "
        "WHERE user_id = %s AND deleted_at IS NULL", (uid,),
    )
    db.execute(
        "UPDATE events SET deleted_at = NOW() "
        "WHERE user_id = %s AND deleted_at IS NULL", (uid,),
    )
    db.execute(
        "UPDATE referral_contacts SET deleted_at = NOW() "
        "WHERE user_id = %s AND deleted_at IS NULL", (uid,),
    )
    db.execute(
        "UPDATE applications SET deleted_at = NOW() "
        "WHERE user_id = %s AND deleted_at IS NULL", (uid,),
    )
    db.execute(
        "UPDATE xp_events SET deleted_at = NOW() "
        "WHERE user_id = %s AND deleted_at IS NULL", (uid,),
    )
    db.execute(
        "UPDATE achievements SET deleted_at = NOW() "
        "WHERE user_id = %s AND deleted_at IS NULL", (uid,),
    )
    db.execute(
        "UPDATE quests SET deleted_at = NOW() "
        "WHERE user_id = %s AND deleted_at IS NULL", (uid,),
    )
    db.execute(
        """
        UPDATE user_progress SET
            current_xp        = 0,
            current_level     = 1,
            current_streak    = 0,
            longest_streak    = 0,
            last_activity_at  = NULL,
            freezes_remaining = 0,
            unseen_level_up   = NULL,
            deleted_at        = NULL,
            updated_at        = NOW()
        WHERE user_id = %s
        """,
        (uid,),
    )
    db.execute(
        "UPDATE voice_turns SET deleted_at = NOW() "
        "WHERE user_id = %s AND deleted_at IS NULL", (uid,),
    )
    db.execute(
        "UPDATE voice_sessions SET deleted_at = NOW() "
        "WHERE user_id = %s AND deleted_at IS NULL", (uid,),
    )
    db.execute(
        "UPDATE pilot_confirmations SET deleted_at = NOW() "
        "WHERE user_id = %s AND deleted_at IS NULL", (uid,),
    )
    # M10 — study tracker. Cascade from topics up to sections so we
    # don't depend on FK CASCADE behaviour (which doesn't apply to soft
    # deletes anyway).
    db.execute(
        "UPDATE study_topics SET deleted_at = NOW() "
        "WHERE user_id = %s AND deleted_at IS NULL", (uid,),
    )
    db.execute(
        "UPDATE study_subsections SET deleted_at = NOW() "
        "WHERE user_id = %s AND deleted_at IS NULL", (uid,),
    )
    db.execute(
        "UPDATE study_sections SET deleted_at = NOW() "
        "WHERE user_id = %s AND deleted_at IS NULL", (uid,),
    )
