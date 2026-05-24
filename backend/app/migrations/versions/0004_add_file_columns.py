"""add_file_columns_to_applications

Revision ID: 0004_add_file_columns
Revises: 0003_create_events
Create Date: 2026-05-15 14:00:00
"""
from alembic import op

revision: str = "0004_add_file_columns"
down_revision: str | None = "0003_create_events"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE applications
            ADD COLUMN jd_file_name           TEXT,
            ADD COLUMN resume_file_name       TEXT,
            ADD COLUMN cover_letter_file_name TEXT
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE applications
            DROP COLUMN jd_file_name,
            DROP COLUMN resume_file_name,
            DROP COLUMN cover_letter_file_name
        """
    )
