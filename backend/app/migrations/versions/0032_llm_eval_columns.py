"""Add model_name and latency_ms to interview eval tables.

Enables per-turn AI observability: which model answered, how long it took.
LangSmith tracing captures token counts; these columns support internal
analytics dashboards (avg score by model, latency percentiles) without
requiring LangSmith to be configured.
"""
from alembic import op

revision = "0032_llm_eval_columns"
down_revision = "0031_perf_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE interview_turns
            ADD COLUMN IF NOT EXISTS model_name TEXT,
            ADD COLUMN IF NOT EXISTS latency_ms INT NOT NULL DEFAULT 0
    """)
    op.execute("""
        ALTER TABLE interview_question_reports
            ADD COLUMN IF NOT EXISTS model_name TEXT,
            ADD COLUMN IF NOT EXISTS latency_ms INT NOT NULL DEFAULT 0
    """)


def downgrade() -> None:
    op.execute(
        "ALTER TABLE interview_turns "
        "DROP COLUMN IF EXISTS model_name, "
        "DROP COLUMN IF EXISTS latency_ms"
    )
    op.execute(
        "ALTER TABLE interview_question_reports "
        "DROP COLUMN IF EXISTS model_name, "
        "DROP COLUMN IF EXISTS latency_ms"
    )
