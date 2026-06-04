"""add first_seen_at to job_cache for velocity tracking

Revision ID: 0026_job_cache_first_seen
Revises: 0025_create_job_tables
Create Date: 2026-06-04
"""
from alembic import op

revision = "0026_job_cache_first_seen"
down_revision = "0025_create_job_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE job_cache
        ADD COLUMN IF NOT EXISTS first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now()
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE job_cache DROP COLUMN IF EXISTS first_seen_at")
