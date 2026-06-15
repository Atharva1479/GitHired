"""add agent_mode columns to interview tables

Revision ID: 0027_interview_agent_mode
Revises: 0026_job_cache_first_seen
Create Date: 2026-06-15
"""
from alembic import op

revision = "0027_interview_agent_mode"
down_revision = "0026_job_cache_first_seen"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE interview_sessions
          ADD COLUMN IF NOT EXISTS agent_mode      BOOLEAN NOT NULL DEFAULT false,
          ADD COLUMN IF NOT EXISTS agent_thread_id TEXT
    """)
    op.execute("""
        ALTER TABLE interview_turns
          ADD COLUMN IF NOT EXISTS turn_type       TEXT NOT NULL DEFAULT 'primary',
          ADD COLUMN IF NOT EXISTS parent_turn_id  BIGINT REFERENCES interview_turns(id),
          ADD COLUMN IF NOT EXISTS followup_depth  SMALLINT NOT NULL DEFAULT 0,
          ADD COLUMN IF NOT EXISTS agent_decision  TEXT
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE interview_turns
          DROP COLUMN IF EXISTS agent_decision,
          DROP COLUMN IF EXISTS followup_depth,
          DROP COLUMN IF EXISTS parent_turn_id,
          DROP COLUMN IF EXISTS turn_type
    """)
    op.execute("""
        ALTER TABLE interview_sessions
          DROP COLUMN IF EXISTS agent_thread_id,
          DROP COLUMN IF EXISTS agent_mode
    """)
