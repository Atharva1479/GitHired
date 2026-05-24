"""soft_delete_everywhere

Adds deleted_at TIMESTAMPTZ to every table that lacks it and rebuilds
uniqueness-affecting indexes as partial (WHERE deleted_at IS NULL) so
soft-deleted rows no longer block new inserts with the same keys.

Tables already on soft delete (untouched here): users, applications,
referral_contacts.

Tables receiving deleted_at: events, nudges, drafts, xp_events,
achievements, quests, user_progress, voice_sessions, voice_turns,
referral_application_link.

pilot_confirmations also gets deleted_at so the one-shot consume can be
implemented as UPDATE deleted_at = NOW() RETURNING token (instead of a
DELETE — strict no-hard-delete policy).

Revision ID: 0013_soft_delete_everywhere
Revises: 0012_add_pilot_writes
Create Date: 2026-05-16 22:00:00
"""
from alembic import op

revision: str = "0013_soft_delete_everywhere"
down_revision: str | None = "0012_add_pilot_writes"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # ── events ──────────────────────────────────────────────────────────
    op.execute("ALTER TABLE events ADD COLUMN deleted_at TIMESTAMPTZ")

    # ── nudges ──────────────────────────────────────────────────────────
    op.execute("ALTER TABLE nudges ADD COLUMN deleted_at TIMESTAMPTZ")
    op.execute("DROP INDEX IF EXISTS nudges_dedup_idx")
    op.execute(
        """
        CREATE UNIQUE INDEX nudges_dedup_idx
            ON nudges (user_id, type, reference_type,
                       COALESCE(reference_id, 0), fired_on_date)
            WHERE deleted_at IS NULL
        """
    )
    op.execute("DROP INDEX IF EXISTS nudges_user_open_idx")
    op.execute(
        """
        CREATE INDEX nudges_user_open_idx
            ON nudges (user_id, fired_on_date DESC)
            WHERE read_at IS NULL
              AND acted_at IS NULL
              AND deleted_at IS NULL
        """
    )

    # ── drafts ──────────────────────────────────────────────────────────
    op.execute("ALTER TABLE drafts ADD COLUMN deleted_at TIMESTAMPTZ")
    op.execute("DROP VIEW IF EXISTS v_user_daily_drafts")
    op.execute(
        """
        CREATE VIEW v_user_daily_drafts AS
        SELECT
            user_id,
            DATE_TRUNC('day', created_at)::date AS day,
            COUNT(*) AS draft_count
        FROM drafts
        WHERE deleted_at IS NULL
        GROUP BY user_id, DATE_TRUNC('day', created_at)
        """
    )

    # ── xp_events ───────────────────────────────────────────────────────
    op.execute("ALTER TABLE xp_events ADD COLUMN deleted_at TIMESTAMPTZ")
    op.execute("DROP INDEX IF EXISTS xp_events_idem_uidx")
    op.execute(
        """
        CREATE UNIQUE INDEX xp_events_idem_uidx
            ON xp_events (user_id, event_key, ref_type, ref_id)
            WHERE deleted_at IS NULL
        """
    )

    # ── achievements (composite PK kept — INSERTs use ON CONFLICT DO
    #    UPDATE SET deleted_at = NULL to resurrect) ─────────────────────
    op.execute("ALTER TABLE achievements ADD COLUMN deleted_at TIMESTAMPTZ")

    # ── quests ──────────────────────────────────────────────────────────
    op.execute("ALTER TABLE quests ADD COLUMN deleted_at TIMESTAMPTZ")
    op.execute("DROP INDEX IF EXISTS quests_user_code_expiry_uidx")
    op.execute(
        """
        CREATE UNIQUE INDEX quests_user_code_expiry_uidx
            ON quests (user_id, code, expires_at)
            WHERE deleted_at IS NULL
        """
    )
    op.execute("DROP INDEX IF EXISTS quests_user_active_idx")
    op.execute(
        """
        CREATE INDEX quests_user_active_idx
            ON quests (user_id, expires_at)
            WHERE completed_at IS NULL AND deleted_at IS NULL
        """
    )

    # ── user_progress (singleton per user — PK is user_id; INSERTs use
    #    ON CONFLICT (user_id) DO UPDATE SET deleted_at = NULL) ─────────
    op.execute("ALTER TABLE user_progress ADD COLUMN deleted_at TIMESTAMPTZ")

    # ── voice_sessions ──────────────────────────────────────────────────
    op.execute("ALTER TABLE voice_sessions ADD COLUMN deleted_at TIMESTAMPTZ")
    op.execute("DROP INDEX IF EXISTS voice_sessions_user_started_idx")
    op.execute(
        """
        CREATE INDEX voice_sessions_user_started_idx
            ON voice_sessions (user_id, started_at DESC)
            WHERE deleted_at IS NULL
        """
    )

    # ── voice_turns ─────────────────────────────────────────────────────
    op.execute("ALTER TABLE voice_turns ADD COLUMN deleted_at TIMESTAMPTZ")
    op.execute("DROP INDEX IF EXISTS voice_turns_session_idx")
    op.execute(
        """
        CREATE INDEX voice_turns_session_idx
            ON voice_turns (session_id, created_at)
            WHERE deleted_at IS NULL
        """
    )

    # ── referral_application_link (composite PK kept — INSERTs use
    #    ON CONFLICT DO UPDATE SET deleted_at = NULL to resurrect) ─────
    op.execute(
        "ALTER TABLE referral_application_link "
        "ADD COLUMN deleted_at TIMESTAMPTZ"
    )

    # ── pilot_confirmations (transient auth tokens — consume is now
    #    UPDATE deleted_at = NOW() RETURNING token; an expiry sweep
    #    can prune old rows asynchronously) ──────────────────────────────
    op.execute(
        "ALTER TABLE pilot_confirmations ADD COLUMN deleted_at TIMESTAMPTZ"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE pilot_confirmations DROP COLUMN IF EXISTS deleted_at")
    op.execute(
        "ALTER TABLE referral_application_link DROP COLUMN IF EXISTS deleted_at"
    )

    op.execute("DROP INDEX IF EXISTS voice_turns_session_idx")
    op.execute(
        "CREATE INDEX voice_turns_session_idx "
        "ON voice_turns (session_id, created_at)"
    )
    op.execute("ALTER TABLE voice_turns DROP COLUMN IF EXISTS deleted_at")

    op.execute("DROP INDEX IF EXISTS voice_sessions_user_started_idx")
    op.execute(
        "CREATE INDEX voice_sessions_user_started_idx "
        "ON voice_sessions (user_id, started_at DESC)"
    )
    op.execute("ALTER TABLE voice_sessions DROP COLUMN IF EXISTS deleted_at")

    op.execute("ALTER TABLE user_progress DROP COLUMN IF EXISTS deleted_at")

    op.execute("DROP INDEX IF EXISTS quests_user_active_idx")
    op.execute(
        "CREATE INDEX quests_user_active_idx "
        "ON quests (user_id, expires_at) WHERE completed_at IS NULL"
    )
    op.execute("DROP INDEX IF EXISTS quests_user_code_expiry_uidx")
    op.execute(
        "CREATE UNIQUE INDEX quests_user_code_expiry_uidx "
        "ON quests (user_id, code, expires_at)"
    )
    op.execute("ALTER TABLE quests DROP COLUMN IF EXISTS deleted_at")

    op.execute("ALTER TABLE achievements DROP COLUMN IF EXISTS deleted_at")

    op.execute("DROP INDEX IF EXISTS xp_events_idem_uidx")
    op.execute(
        "CREATE UNIQUE INDEX xp_events_idem_uidx "
        "ON xp_events (user_id, event_key, ref_type, ref_id)"
    )
    op.execute("ALTER TABLE xp_events DROP COLUMN IF EXISTS deleted_at")

    op.execute("DROP VIEW IF EXISTS v_user_daily_drafts")
    op.execute(
        """
        CREATE VIEW v_user_daily_drafts AS
        SELECT user_id, DATE_TRUNC('day', created_at)::date AS day,
               COUNT(*) AS draft_count
        FROM drafts
        GROUP BY user_id, DATE_TRUNC('day', created_at)
        """
    )
    op.execute("ALTER TABLE drafts DROP COLUMN IF EXISTS deleted_at")

    op.execute("DROP INDEX IF EXISTS nudges_user_open_idx")
    op.execute(
        """
        CREATE INDEX nudges_user_open_idx
            ON nudges (user_id, fired_on_date DESC)
            WHERE read_at IS NULL AND acted_at IS NULL
        """
    )
    op.execute("DROP INDEX IF EXISTS nudges_dedup_idx")
    op.execute(
        """
        CREATE UNIQUE INDEX nudges_dedup_idx
            ON nudges (user_id, type, reference_type,
                       COALESCE(reference_id, 0), fired_on_date)
        """
    )
    op.execute("ALTER TABLE nudges DROP COLUMN IF EXISTS deleted_at")

    op.execute("ALTER TABLE events DROP COLUMN IF EXISTS deleted_at")
