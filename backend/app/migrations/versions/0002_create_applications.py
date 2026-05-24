"""create_applications

Revision ID: 0002_create_applications
Revises: 0001_create_users
Create Date: 2026-05-15 12:10:00
"""
from alembic import op

revision: str = "0002_create_applications"
down_revision: str | None = "0001_create_users"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE applications (
            id                  BIGSERIAL PRIMARY KEY,
            user_id             BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            company             TEXT NOT NULL,
            role                TEXT NOT NULL,
            jd_url              TEXT,
            source              TEXT NOT NULL CHECK (source IN
                                    ('LinkedIn','Naukri','Referral','CompanySite','Other')),
            status              TEXT NOT NULL DEFAULT 'Applied' CHECK (status IN
                                    ('Applied','Screening','Interview','Offer','Rejected','Ghosted')),
            applied_date        DATE NOT NULL,
            last_updated        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            salary_discussed    TEXT,
            contact_name        TEXT,
            contact_linkedin    TEXT,
            fit_score           INT CHECK (fit_score BETWEEN 0 AND 100),
            notes               TEXT,
            follow_up_count     INT NOT NULL DEFAULT 0 CHECK (follow_up_count >= 0),
            last_followed_up_at TIMESTAMPTZ,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at          TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE INDEX applications_user_status_idx
            ON applications (user_id, status) WHERE deleted_at IS NULL
        """
    )
    op.execute(
        """
        CREATE INDEX applications_user_applied_date_idx
            ON applications (user_id, applied_date DESC) WHERE deleted_at IS NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE applications")
