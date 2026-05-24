"""create_interview_tables

AI voice interview feature — four tables:
  interview_sessions         — one per interview attempt, user-scoped
  interview_turns            — one Q&A exchange per row, ordered by question_index
  interview_question_reports — per-question AI evaluation (ideal answer, score, feedback)
  interview_reports          — overall score + skill breakdown + summary

Revision ID: 0020_create_interview_tables
Revises: 0019_add_user_settings
Create Date: 2026-05-24 12:00:00
"""
from alembic import op

revision: str = "0020_create_interview_tables"
down_revision: str | None = "0019_add_user_settings"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE interview_sessions (
            id              BIGSERIAL PRIMARY KEY,
            user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            topic           TEXT NOT NULL,
            role            TEXT NOT NULL,
            years_exp       TEXT NOT NULL,
            duration_min    INT NOT NULL,
            total_questions INT NOT NULL,
            status          TEXT NOT NULL DEFAULT 'active',
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            ended_at        TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE INDEX interview_sessions_user_idx
            ON interview_sessions (user_id, created_at DESC)
        """
    )
    op.execute(
        """
        CREATE TABLE interview_turns (
            id              BIGSERIAL PRIMARY KEY,
            session_id      BIGINT NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
            question_index  INT NOT NULL,
            question        TEXT NOT NULL,
            user_answer     TEXT NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE interview_question_reports (
            id              BIGSERIAL PRIMARY KEY,
            session_id      BIGINT NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
            question_index  INT NOT NULL,
            question        TEXT NOT NULL,
            user_answer     TEXT NOT NULL,
            ideal_answer    TEXT NOT NULL,
            score           INT NOT NULL,
            feedback        TEXT NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE interview_reports (
            id              BIGSERIAL PRIMARY KEY,
            session_id      BIGINT NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE UNIQUE,
            overall_score   INT NOT NULL,
            skill_breakdown JSONB NOT NULL DEFAULT '{}',
            summary         TEXT NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS interview_reports")
    op.execute("DROP TABLE IF EXISTS interview_question_reports")
    op.execute("DROP TABLE IF EXISTS interview_turns")
    op.execute("DROP TABLE IF EXISTS interview_sessions")
