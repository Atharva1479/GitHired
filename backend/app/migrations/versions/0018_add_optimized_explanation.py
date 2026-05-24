"""add_optimized_explanation

Adds optimized_explanation column to dsa_analyses — plain-English
explanation of why the optimized solution works and what makes it better.

Revision ID: 0018_add_optimized_explanation
Revises: 0017_add_dry_run_explanation
Create Date: 2026-05-22 11:00:00
"""
from alembic import op

revision: str = "0018_add_optimized_explanation"
down_revision: str | None = "0017_add_dry_run_explanation"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE dsa_analyses ADD COLUMN IF NOT EXISTS optimized_explanation TEXT NOT NULL DEFAULT ''"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE dsa_analyses DROP COLUMN IF EXISTS optimized_explanation")
