"""Add performance indexes: events partial index + job_cache trigram index.

events: partial index on (user_id, event_type, occurred_at DESC) filtered to
status-change events so pilot context queries avoid full table scans.

job_cache: trigram index on location so ILIKE '%text%' searches use the index
instead of forcing a sequential scan.
"""
from alembic import op

revision = "0031_perf_indexes"
down_revision = "0030_job_search_cache"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Pilot context query: WHERE user_id = $1 AND event_type = '...' AND occurred_at >= ...
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_events_pilot_context
        ON events (user_id, event_type, occurred_at DESC)
        WHERE deleted_at IS NULL AND event_type = 'application.status_changed'
    """)

    # job_cache location ILIKE '%text%' — leading wildcard needs trigram
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_job_cache_location_trgm
        ON job_cache USING gin (location gin_trgm_ops)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_job_cache_location_trgm")
    op.execute("DROP INDEX IF EXISTS idx_events_pilot_context")
