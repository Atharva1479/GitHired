"""add_user_settings

Adds per-user preference columns to the users table.

Revision ID: 0019_add_user_settings
Revises: 0018_add_optimized_explanation
Create Date: 2026-05-22 12:00:00
"""
from alembic import op

revision: str = "0019_add_user_settings"
down_revision: str | None = "0018_add_optimized_explanation"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
        "ai_provider TEXT NOT NULL DEFAULT 'auto'"
    )
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
        "ollama_model TEXT"
    )
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
        "elevenlabs_voice_id TEXT"
    )
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
        "digest_opt_in BOOLEAN NOT NULL DEFAULT TRUE"
    )
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
        "nudge_hour INT"
    )
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
        "weekly_apps_goal INT NOT NULL DEFAULT 5"
    )
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
        "wake_word_enabled BOOLEAN NOT NULL DEFAULT TRUE"
    )


def downgrade() -> None:
    for col in (
        "wake_word_enabled",
        "weekly_apps_goal",
        "nudge_hour",
        "digest_opt_in",
        "elevenlabs_voice_id",
        "ollama_model",
        "ai_provider",
    ):
        op.execute(f"ALTER TABLE users DROP COLUMN IF EXISTS {col}")
