"""create_referrals

Revision ID: 0006_create_referrals
Revises: 0005_add_jd_text
Create Date: 2026-05-15 16:00:00
"""
from alembic import op

revision: str = "0006_create_referrals"
down_revision: str | None = "0005_add_jd_text"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE referral_contacts (
            id                      BIGSERIAL PRIMARY KEY,
            user_id                 BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name                    TEXT NOT NULL,
            company                 TEXT NOT NULL,
            role_at_company         TEXT,
            linkedin_url            TEXT,
            target_role             TEXT NOT NULL,
            mutual_context          TEXT,
            connection_sent_date    DATE NOT NULL,
            connection_status       TEXT NOT NULL DEFAULT 'Request Sent' CHECK (connection_status IN
                                        ('Request Sent','Accepted','Msg Sent','Replied','Referred','Dropped')),
            referral_msg_sent_date  DATE,
            reply_date              DATE,
            outcome                 TEXT CHECK (outcome IS NULL OR outcome IN
                                        ('Referred','NoResponse','Declined')),
            notes                   TEXT,
            last_updated            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at              TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE INDEX referrals_user_status_idx
            ON referral_contacts (user_id, connection_status) WHERE deleted_at IS NULL
        """
    )
    op.execute(
        """
        CREATE INDEX referrals_user_company_idx
            ON referral_contacts (user_id, company) WHERE deleted_at IS NULL
        """
    )
    op.execute(
        """
        CREATE TABLE referral_application_link (
            referral_id     BIGINT NOT NULL REFERENCES referral_contacts(id) ON DELETE CASCADE,
            application_id  BIGINT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
            linked_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (referral_id, application_id)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE referral_application_link")
    op.execute("DROP TABLE referral_contacts")
