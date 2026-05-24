"""create_drafts

Revision ID: 0008_create_drafts
Revises: 0007_create_nudges
Create Date: 2026-05-15 18:00:00
"""
from alembic import op

revision: str = "0008_create_drafts"
down_revision: str | None = "0007_create_nudges"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE drafts (
            id            BIGSERIAL PRIMARY KEY,
            user_id       BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            entity_type   TEXT NOT NULL CHECK (entity_type IN ('application','referral')),
            entity_id     BIGINT NOT NULL,
            draft_type    TEXT NOT NULL CHECK (draft_type IN
                              ('followup_email','referral_ask','referral_followup','weekly_summary')),
            content       TEXT NOT NULL,
            model         TEXT NOT NULL,
            prompt_tokens INT,
            output_tokens INT,
            fallback      BOOLEAN NOT NULL DEFAULT FALSE,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX drafts_lookup_idx
            ON drafts (user_id, entity_type, entity_id, draft_type, created_at DESC)
        """
    )
    op.execute(
        """
        CREATE VIEW v_user_daily_drafts AS
        SELECT
            user_id,
            DATE_TRUNC('day', created_at)::date AS day,
            COUNT(*) AS draft_count
        FROM drafts
        GROUP BY user_id, DATE_TRUNC('day', created_at)
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_user_daily_drafts")
    op.execute("DROP TABLE drafts")
