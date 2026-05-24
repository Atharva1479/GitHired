"""pilot_confirm_args

Stores the original tool args alongside the confirmation token so the
agent on the NEXT turn can re-call the destructive tool with the same
args plus the token. Without this, the chat history (text only — no
tool-call results) lost the token between turns and confirmations went
stale before the user's "yes" could be processed.

Revision ID: 0014_pilot_confirm_args
Revises: 0013_soft_delete_everywhere
Create Date: 2026-05-17 18:00:00
"""
from alembic import op

revision: str = "0014_pilot_confirm_args"
down_revision: str | None = "0013_soft_delete_everywhere"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE pilot_confirmations ADD COLUMN args JSONB")


def downgrade() -> None:
    op.execute("ALTER TABLE pilot_confirmations DROP COLUMN IF EXISTS args")
