"""Add job_search_cache table for exact-key query result caching."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, INTEGER

revision = "0030_job_search_cache"
down_revision = "0029_job_cache_enrich"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE job_search_cache (
            id          SERIAL PRIMARY KEY,
            query_hash  TEXT        NOT NULL,
            query       TEXT        NOT NULL,
            location    TEXT,
            remote_only BOOLEAN     NOT NULL DEFAULT false,
            experience  TEXT,
            job_ids     INTEGER[]   NOT NULL DEFAULT '{}',
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            expires_at  TIMESTAMPTZ NOT NULL
        )
    """)
    op.execute("""
        CREATE UNIQUE INDEX ix_job_search_cache_key
        ON job_search_cache (
            query_hash,
            COALESCE(location, ''),
            remote_only,
            COALESCE(experience, '')
        )
    """)
    op.execute("""
        CREATE INDEX ix_job_search_cache_expires
        ON job_search_cache (expires_at)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS job_search_cache")
