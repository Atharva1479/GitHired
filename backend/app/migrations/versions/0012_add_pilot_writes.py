"""add_pilot_writes

Revision ID: 0012_add_pilot_writes
Revises: 0011_add_voice
Create Date: 2026-05-16 18:00:00
"""
from alembic import op

revision: str = "0012_add_pilot_writes"
down_revision: str | None = "0011_add_voice"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE pilot_confirmations (
            token       TEXT PRIMARY KEY,
            user_id     INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            tool_name   TEXT NOT NULL,
            args_hash   TEXT NOT NULL,
            expires_at  TIMESTAMPTZ NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX pilot_confirmations_expiry_idx "
        "ON pilot_confirmations (expires_at)"
    )
    op.execute(
        "ALTER TABLE users "
        "ADD COLUMN auto_brief_enabled BOOLEAN NOT NULL DEFAULT FALSE"
    )
    op.execute("ALTER TABLE voice_turns ADD COLUMN tool_calls JSONB")


def downgrade() -> None:
    op.execute("ALTER TABLE voice_turns DROP COLUMN IF EXISTS tool_calls")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS auto_brief_enabled")
    op.execute("DROP TABLE IF EXISTS pilot_confirmations")
