"""create_nudges

Revision ID: 0007_create_nudges
Revises: 0006_create_referrals
Create Date: 2026-05-15 17:00:00
"""
from alembic import op

revision: str = "0007_create_nudges"
down_revision: str | None = "0006_create_referrals"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE nudges (
            id              BIGSERIAL PRIMARY KEY,
            user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            type            TEXT NOT NULL CHECK (type IN
                                ('application_followup','application_stale',
                                 'application_interview_stale','apply_more',
                                 'referral_check','referral_unaccepted',
                                 'referral_ask','referral_followup')),
            reference_type  TEXT NOT NULL CHECK (reference_type IN ('application','referral','user')),
            reference_id    BIGINT,
            severity        TEXT NOT NULL DEFAULT 'due' CHECK (severity IN ('info','due','overdue')),
            message         TEXT NOT NULL,
            fired_on_date   DATE NOT NULL,
            read_at         TIMESTAMPTZ,
            acted_at        TIMESTAMPTZ,
            snoozed_until   DATE,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX nudges_dedup_idx
            ON nudges (user_id, type, reference_type, COALESCE(reference_id, 0), fired_on_date)
        """
    )
    op.execute(
        """
        CREATE INDEX nudges_user_open_idx
            ON nudges (user_id, fired_on_date DESC)
            WHERE read_at IS NULL AND acted_at IS NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE nudges")
