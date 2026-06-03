"""create job discovery tables

Revision ID: 0025_create_job_tables
Revises: 0024_create_resumes
Create Date: 2026-06-03
"""
from alembic import op

revision = "0025_create_job_tables"
down_revision = "0024_create_resumes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Cached external job listings (TTL-based, shared across users)
    op.execute("""
        CREATE TABLE job_cache (
            id              BIGSERIAL PRIMARY KEY,
            source          TEXT NOT NULL,
            external_id     TEXT NOT NULL,
            title           TEXT NOT NULL,
            company         TEXT NOT NULL,
            location        TEXT,
            description     TEXT,
            apply_url       TEXT NOT NULL,
            posted_at       TIMESTAMPTZ,
            employment_type TEXT,
            skills          TEXT[] NOT NULL DEFAULT '{}',
            raw_data        JSONB NOT NULL DEFAULT '{}',
            fetched_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            expires_at      TIMESTAMPTZ NOT NULL,
            UNIQUE(source, external_id)
        )
    """)
    op.execute("CREATE INDEX idx_job_cache_expires ON job_cache (expires_at)")
    op.execute("CREATE INDEX idx_job_cache_posted ON job_cache (posted_at DESC)")

    # Per-user saved search criteria (drives daily alerts)
    op.execute("""
        CREATE TABLE job_searches (
            id              BIGSERIAL PRIMARY KEY,
            user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name            TEXT NOT NULL,
            query           TEXT NOT NULL,
            location        TEXT,
            remote_only     BOOLEAN NOT NULL DEFAULT false,
            experience      TEXT,
            freshness_hours INT NOT NULL DEFAULT 24,
            is_active       BOOLEAN NOT NULL DEFAULT true,
            last_alerted_at TIMESTAMPTZ,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_job_searches_user ON job_searches (user_id)")

    # Per-user bookmarks / apply history for discovered jobs
    op.execute("""
        CREATE TABLE job_bookmarks (
            id              BIGSERIAL PRIMARY KEY,
            user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            job_cache_id    BIGINT REFERENCES job_cache(id) ON DELETE SET NULL,
            title           TEXT NOT NULL,
            company         TEXT NOT NULL,
            apply_url       TEXT NOT NULL,
            posted_at       TIMESTAMPTZ,
            source          TEXT NOT NULL,
            external_id     TEXT NOT NULL,
            status          TEXT NOT NULL DEFAULT 'bookmarked',
            application_id  BIGINT REFERENCES applications(id) ON DELETE SET NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE(user_id, source, external_id)
        )
    """)
    op.execute("CREATE INDEX idx_job_bookmarks_user ON job_bookmarks (user_id, status)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS job_bookmarks")
    op.execute("DROP TABLE IF EXISTS job_searches")
    op.execute("DROP TABLE IF EXISTS job_cache")
