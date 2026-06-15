"""add GIN full-text search index to job_cache for cache-first queries

Revision ID: 0028_job_cache_fts_index
Revises: 0027_interview_agent_mode
Create Date: 2026-06-15
"""
from alembic import op

revision = "0028_job_cache_fts_index"
down_revision = "0027_interview_agent_mode"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_job_cache_fts
        ON job_cache
        USING gin(to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(description, '')))
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_job_cache_fts")
