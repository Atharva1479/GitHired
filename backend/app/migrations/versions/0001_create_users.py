"""create_users

Revision ID: 0001_create_users
Revises:
Create Date: 2026-05-15 12:00:00
"""
from alembic import op

revision: str = "0001_create_users"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")
    op.execute(
        """
        CREATE TABLE users (
            id            BIGSERIAL PRIMARY KEY,
            email         CITEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            display_name  TEXT NOT NULL,
            timezone      TEXT NOT NULL DEFAULT 'UTC',
            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at    TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        INSERT INTO users (email, password_hash, display_name)
        VALUES ('mvp@local', '!', 'MVP User')
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE users")
