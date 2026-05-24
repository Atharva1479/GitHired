"""add_gamify

Revision ID: 0010_add_gamify
Revises: 0009_add_google_auth
Create Date: 2026-05-16 10:00:00
"""
from alembic import op

revision: str = "0010_add_gamify"
down_revision: str | None = "0009_add_google_auth"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE user_progress (
            user_id           INT  PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            current_xp        INT  NOT NULL DEFAULT 0,
            current_level     INT  NOT NULL DEFAULT 1,
            current_streak    INT  NOT NULL DEFAULT 0,
            longest_streak    INT  NOT NULL DEFAULT 0,
            last_activity_at  DATE,
            freezes_remaining INT  NOT NULL DEFAULT 0,
            unseen_level_up   INT,
            updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE xp_events (
            id          BIGSERIAL PRIMARY KEY,
            user_id     INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            event_key   TEXT NOT NULL,
            xp_delta    INT  NOT NULL,
            ref_type    TEXT NOT NULL DEFAULT '',
            ref_id      BIGINT NOT NULL DEFAULT 0,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX xp_events_idem_uidx "
        "ON xp_events (user_id, event_key, ref_type, ref_id)"
    )
    op.execute(
        "CREATE INDEX xp_events_user_created_idx "
        "ON xp_events (user_id, created_at DESC)"
    )
    op.execute(
        """
        CREATE TABLE achievements (
            user_id     INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            code        TEXT NOT NULL,
            unlocked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            seen_at     TIMESTAMPTZ,
            PRIMARY KEY (user_id, code)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE quests (
            id            BIGSERIAL PRIMARY KEY,
            user_id       INT  NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            code          TEXT NOT NULL,
            period        TEXT NOT NULL,
            target        INT  NOT NULL,
            progress      INT  NOT NULL DEFAULT 0,
            reward_xp     INT  NOT NULL,
            expires_at    TIMESTAMPTZ NOT NULL,
            completed_at  TIMESTAMPTZ,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX quests_user_code_expiry_uidx "
        "ON quests (user_id, code, expires_at)"
    )
    op.execute(
        "CREATE INDEX quests_user_active_idx "
        "ON quests (user_id, expires_at) WHERE completed_at IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS quests")
    op.execute("DROP TABLE IF EXISTS achievements")
    op.execute("DROP TABLE IF EXISTS xp_events")
    op.execute("DROP TABLE IF EXISTS user_progress")
