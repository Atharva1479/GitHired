"""add_dry_run_explanation

Adds dry_run_explanation column to dsa_analyses for AI-generated
step-by-step walkthrough of the optimized solution.

Revision ID: 0017_add_dry_run_explanation
Revises: 0016_create_dsa_tables
Create Date: 2026-05-22 10:00:00
"""
from alembic import op

revision: str = "0017_add_dry_run_explanation"
down_revision: str | None = "0016_create_dsa_tables"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE dsa_analyses ADD COLUMN IF NOT EXISTS dry_run_explanation TEXT NOT NULL DEFAULT ''"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE dsa_analyses DROP COLUMN IF EXISTS dry_run_explanation")
