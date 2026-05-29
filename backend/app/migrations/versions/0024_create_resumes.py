"""create resumes table

Revision ID: 0024_create_resumes
Revises: 0023_remove_draft_types
Create Date: 2026-05-28
"""
from alembic import op

revision = "0024_create_resumes"
down_revision = "0023_remove_draft_types"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE resumes (
            id          BIGSERIAL PRIMARY KEY,
            user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name        TEXT NOT NULL,
            role_tag    TEXT NOT NULL,
            file_name   TEXT NOT NULL,
            parsed_text TEXT NOT NULL DEFAULT '',
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at  TIMESTAMPTZ
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS resumes")
