"""create_study_tables

M10 Phase 1: the revision + new-learning tracker.

Three tables, each soft-delete aware, all rows scoped by user_id. Topics
carry both ``kind`` (learn vs revise) and ``status`` (todo / in_progress
/ done / mastered) so the user can mix curricula they're learning from
scratch with topics they're brushing up before interviews. ``tags`` is
a PostgreSQL TEXT[] indexed with GIN for fast filtering.

Revision ID: 0015_create_study_tables
Revises: 0014_pilot_confirm_args
Create Date: 2026-05-17 11:00:00
"""
from alembic import op

revision: str = "0015_create_study_tables"
down_revision: str | None = "0014_pilot_confirm_args"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # ── study_sections ────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE study_sections (
            id            BIGSERIAL PRIMARY KEY,
            user_id       BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name          TEXT NOT NULL,
            icon          TEXT,
            position      INT  NOT NULL DEFAULT 0,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_updated  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at    TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE INDEX study_sections_user_pos_idx
            ON study_sections (user_id, position)
            WHERE deleted_at IS NULL
        """
    )

    # ── study_subsections ─────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE study_subsections (
            id            BIGSERIAL PRIMARY KEY,
            section_id    BIGINT NOT NULL REFERENCES study_sections(id) ON DELETE CASCADE,
            user_id       BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name          TEXT NOT NULL,
            position      INT  NOT NULL DEFAULT 0,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_updated  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at    TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE INDEX study_subsections_section_pos_idx
            ON study_subsections (section_id, position)
            WHERE deleted_at IS NULL
        """
    )
    op.execute(
        """
        CREATE INDEX study_subsections_user_idx
            ON study_subsections (user_id)
            WHERE deleted_at IS NULL
        """
    )

    # ── study_topics ──────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE study_topics (
            id              BIGSERIAL PRIMARY KEY,
            subsection_id   BIGINT NOT NULL REFERENCES study_subsections(id) ON DELETE CASCADE,
            user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title           TEXT NOT NULL,
            notes           TEXT,
            kind            TEXT NOT NULL DEFAULT 'learn'
                              CHECK (kind IN ('learn','revise')),
            status          TEXT NOT NULL DEFAULT 'todo'
                              CHECK (status IN ('todo','in_progress','done','mastered')),
            tags            TEXT[] NOT NULL DEFAULT '{}',
            revision_count  INT NOT NULL DEFAULT 0 CHECK (revision_count >= 0),
            last_revised_at TIMESTAMPTZ,
            position        INT NOT NULL DEFAULT 0,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_updated    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at      TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE INDEX study_topics_subsection_pos_idx
            ON study_topics (subsection_id, position)
            WHERE deleted_at IS NULL
        """
    )
    op.execute(
        """
        CREATE INDEX study_topics_user_status_idx
            ON study_topics (user_id, status)
            WHERE deleted_at IS NULL
        """
    )
    # Surface stale "due for review" topics fast.
    op.execute(
        """
        CREATE INDEX study_topics_user_stale_idx
            ON study_topics (user_id, last_revised_at)
            WHERE deleted_at IS NULL
              AND status IN ('done','mastered')
        """
    )
    # GIN index for tag-filter queries (e.g. WHERE tags && ARRAY['interview']).
    op.execute(
        """
        CREATE INDEX study_topics_tags_gin_idx
            ON study_topics USING GIN (tags)
            WHERE deleted_at IS NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS study_topics")
    op.execute("DROP TABLE IF EXISTS study_subsections")
    op.execute("DROP TABLE IF EXISTS study_sections")
