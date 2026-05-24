"""create_events

Revision ID: 0003_create_events
Revises: 0002_create_applications
Create Date: 2026-05-15 12:20:00
"""
from alembic import op

revision: str = "0003_create_events"
down_revision: str | None = "0002_create_applications"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE events (
            id          BIGSERIAL PRIMARY KEY,
            user_id     BIGINT REFERENCES users(id) ON DELETE SET NULL,
            event_type  TEXT NOT NULL,
            payload     JSONB NOT NULL DEFAULT '{}'::jsonb,
            occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX events_user_time_idx ON events (user_id, occurred_at DESC)"
    )
    op.execute(
        "CREATE INDEX events_type_time_idx ON events (event_type, occurred_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE events")
