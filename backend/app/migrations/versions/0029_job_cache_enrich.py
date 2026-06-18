"""add salary, is_remote, tags columns to job_cache

Revision ID: 0029_job_cache_enrich
Revises: 0028_job_cache_fts_index
Create Date: 2026-06-16
"""
from alembic import op

revision = "0029_job_cache_enrich"
down_revision = "0028_job_cache_fts_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE job_cache
          ADD COLUMN IF NOT EXISTS salary_min      INTEGER,
          ADD COLUMN IF NOT EXISTS salary_max      INTEGER,
          ADD COLUMN IF NOT EXISTS salary_currency TEXT,
          ADD COLUMN IF NOT EXISTS is_remote       BOOLEAN NOT NULL DEFAULT false,
          ADD COLUMN IF NOT EXISTS tags            TEXT[]  NOT NULL DEFAULT '{}'
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE job_cache DROP COLUMN IF EXISTS salary_min")
    op.execute("ALTER TABLE job_cache DROP COLUMN IF EXISTS salary_max")
    op.execute("ALTER TABLE job_cache DROP COLUMN IF EXISTS salary_currency")
    op.execute("ALTER TABLE job_cache DROP COLUMN IF EXISTS is_remote")
    op.execute("ALTER TABLE job_cache DROP COLUMN IF EXISTS tags")
