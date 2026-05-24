"""add_jd_text_to_applications

Revision ID: 0005_add_jd_text
Revises: 0004_add_file_columns
Create Date: 2026-05-15 15:00:00
"""
from alembic import op

revision: str = "0005_add_jd_text"
down_revision: str | None = "0004_add_file_columns"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE applications ADD COLUMN jd_text TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE applications DROP COLUMN jd_text")
