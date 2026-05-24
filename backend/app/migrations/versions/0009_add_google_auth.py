"""add_google_auth

Revision ID: 0009_add_google_auth
Revises: 0008_create_drafts
Create Date: 2026-05-15 18:00:00
"""
from alembic import op

revision: str = "0009_add_google_auth"
down_revision: str | None = "0008_create_drafts"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL")
    op.execute("ALTER TABLE users ADD COLUMN google_sub TEXT")
    op.execute("ALTER TABLE users ADD COLUMN picture_url TEXT")
    op.execute(
        "CREATE UNIQUE INDEX users_google_sub_uidx "
        "ON users (google_sub) WHERE google_sub IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS users_google_sub_uidx")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS picture_url")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS google_sub")
