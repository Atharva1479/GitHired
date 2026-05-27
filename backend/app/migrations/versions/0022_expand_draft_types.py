"""expand draft_type check constraint to include new draft types

Revision ID: 0022_expand_draft_types
Revises: 0021_soft_delete_interview_sessions
Create Date: 2026-05-27
"""
from alembic import op

revision = "0022_expand_draft_types"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE drafts DROP CONSTRAINT IF EXISTS drafts_draft_type_check")
    op.execute(
        """
        ALTER TABLE drafts ADD CONSTRAINT drafts_draft_type_check
        CHECK (draft_type IN (
            'followup_email',
            'referral_ask',
            'referral_followup',
            'weekly_summary',
            'interview_thankyou',
            'offer_negotiation',
            'cover_letter'
        ))
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE drafts DROP CONSTRAINT IF EXISTS drafts_draft_type_check")
    op.execute(
        """
        ALTER TABLE drafts ADD CONSTRAINT drafts_draft_type_check
        CHECK (draft_type IN (
            'followup_email',
            'referral_ask',
            'referral_followup',
            'weekly_summary'
        ))
        """
    )
