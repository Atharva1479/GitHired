"""soft delete interview sessions

Revision ID: 0021_soft_delete_interview_sessions
Revises: 0020_create_interview_tables
Create Date: 2026-05-24
"""
from alembic import op

revision = "0021"
down_revision = "0020_create_interview_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE interview_sessions ADD COLUMN deleted_at TIMESTAMPTZ"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE interview_sessions DROP COLUMN IF EXISTS deleted_at"
    )
