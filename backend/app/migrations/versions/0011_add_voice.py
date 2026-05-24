"""add_voice

Revision ID: 0011_add_voice
Revises: 0010_add_gamify
Create Date: 2026-05-16 14:00:00
"""
from alembic import op

revision: str = "0011_add_voice"
down_revision: str | None = "0010_add_gamify"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE voice_sessions (
            id         BIGSERIAL PRIMARY KEY,
            user_id    INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            ended_at   TIMESTAMPTZ,
            turn_count INT NOT NULL DEFAULT 0,
            cost_usd   NUMERIC(10,6) NOT NULL DEFAULT 0
        )
        """
    )
    op.execute(
        "CREATE INDEX voice_sessions_user_started_idx "
        "ON voice_sessions (user_id, started_at DESC)"
    )
    op.execute(
        """
        CREATE TABLE voice_turns (
            id          BIGSERIAL PRIMARY KEY,
            session_id  BIGINT NOT NULL REFERENCES voice_sessions(id) ON DELETE CASCADE,
            user_id     INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role        TEXT NOT NULL,
            content     TEXT NOT NULL,
            tokens_in   INT NOT NULL DEFAULT 0,
            tokens_out  INT NOT NULL DEFAULT 0,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX voice_turns_session_idx "
        "ON voice_turns (session_id, created_at)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS voice_turns")
    op.execute("DROP TABLE IF EXISTS voice_sessions")
