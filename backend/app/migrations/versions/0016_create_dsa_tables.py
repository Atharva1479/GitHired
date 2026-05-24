"""create_dsa_tables

DSA Progress Tracker — two tables:
  dsa_problems  — one row per solved problem (soft-deletable, user-scoped)
  dsa_analyses  — AI analysis results for a problem (append-only, no deletes)

Revision ID: 0016_create_dsa_tables
Revises: 0015_create_study_tables
Create Date: 2026-05-21 10:00:00
"""
from alembic import op

revision: str = "0016_create_dsa_tables"
down_revision: str | None = "0015_create_study_tables"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE dsa_problems (
            id            BIGSERIAL PRIMARY KEY,
            user_id       BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            topic         TEXT NOT NULL,
            difficulty    TEXT NOT NULL DEFAULT 'medium'
                              CHECK (difficulty IN ('easy', 'medium', 'hard')),
            title         TEXT NOT NULL,
            source_url    TEXT,
            description   TEXT,
            user_solution TEXT,
            solved_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_updated  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at    TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE INDEX dsa_problems_user_topic_idx
            ON dsa_problems (user_id, topic)
            WHERE deleted_at IS NULL
        """
    )
    op.execute(
        """
        CREATE INDEX dsa_problems_user_created_idx
            ON dsa_problems (user_id, created_at DESC)
            WHERE deleted_at IS NULL
        """
    )

    op.execute(
        """
        CREATE TABLE dsa_analyses (
            id                 BIGSERIAL PRIMARY KEY,
            problem_id         BIGINT NOT NULL REFERENCES dsa_problems(id) ON DELETE CASCADE,
            user_id            BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            time_complexity    TEXT NOT NULL,
            space_complexity   TEXT NOT NULL,
            approach_summary   TEXT NOT NULL,
            feedback           TEXT NOT NULL,
            optimized_solution TEXT NOT NULL,
            model              TEXT NOT NULL DEFAULT 'gemini',
            created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX dsa_analyses_problem_idx
            ON dsa_analyses (problem_id, created_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX dsa_analyses_user_idx
            ON dsa_analyses (user_id, created_at DESC)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS dsa_analyses")
    op.execute("DROP TABLE IF EXISTS dsa_problems")
