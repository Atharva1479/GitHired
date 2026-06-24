from typing import Any

import asyncpg


async def get_by_id(db: asyncpg.Connection, user_id: int) -> dict[str, Any] | None:
    row = await db.fetchrow(
        "SELECT id, email, display_name, picture_url, google_sub, "
        "auto_brief_enabled "
        "FROM users WHERE id = $1 AND deleted_at IS NULL",
        user_id,
    )
    return dict(row) if row else None


async def set_auto_brief(
    db: asyncpg.Connection, user_id: int, enabled: bool,
) -> bool:
    """Update the user's auto-brief opt-in. Returns the new value."""
    row = await db.fetchrow(
        "UPDATE users SET auto_brief_enabled = $2 "
        "WHERE id = $1 AND deleted_at IS NULL "
        "RETURNING auto_brief_enabled",
        user_id, enabled,
    )
    if row is None:
        return enabled
    return bool(row["auto_brief_enabled"])


async def upsert_google_user(
    db: asyncpg.Connection,
    *,
    google_sub: str,
    email: str,
    name: str,
    picture_url: str | None,
) -> dict[str, Any]:
    """
    Returns (user, claimed_unclaimed_seed).

    Strategy:
      1. If a user already has this google_sub -> return them (refresh profile fields).
      2. Else try to claim the seed user (id=1) if its google_sub IS NULL — this
         attaches the existing single-user MVP data to the first real signup.
      3. Else insert a fresh user.
    """
    existing = await db.fetchrow(
        "SELECT id FROM users WHERE google_sub = $1 AND deleted_at IS NULL",
        google_sub,
    )
    if existing:
        row = await db.fetchrow(
            "UPDATE users SET email = $2, display_name = $3, picture_url = $4 "
            "WHERE id = $1 "
            "RETURNING id, email, display_name, picture_url, google_sub",
            existing["id"],
            email,
            name,
            picture_url,
        )
        return dict(row) if row is not None else {}

    claimed = await db.fetchrow(
        "UPDATE users "
        "SET google_sub = $1, email = $2, display_name = $3, picture_url = $4 "
        "WHERE google_sub IS NULL AND deleted_at IS NULL "
        "AND id = (SELECT id FROM users WHERE google_sub IS NULL "
        "          AND deleted_at IS NULL ORDER BY id LIMIT 1) "
        "RETURNING id, email, display_name, picture_url, google_sub",
        google_sub,
        email,
        name,
        picture_url,
    )
    if claimed:
        return dict(claimed)

    # ON CONFLICT handles the race where two concurrent callbacks for the same
    # google_sub both slip past the SELECT above and both attempt the INSERT.
    row = await db.fetchrow(
        "INSERT INTO users (email, display_name, google_sub, picture_url) "
        "VALUES ($1, $2, $3, $4) "
        "ON CONFLICT (google_sub) WHERE google_sub IS NOT NULL "
        "DO UPDATE SET email = EXCLUDED.email, display_name = EXCLUDED.display_name, "
        "picture_url = EXCLUDED.picture_url "
        "RETURNING id, email, display_name, picture_url, google_sub",
        email,
        name,
        google_sub,
        picture_url,
    )
    return dict(row) if row is not None else {}


async def get_user_settings(db: asyncpg.Connection, user_id: int) -> dict[str, Any]:
    row = await db.fetchrow(
        """
        SELECT
            ai_provider,
            ollama_model,
            elevenlabs_voice_id,
            digest_opt_in,
            nudge_hour,
            weekly_apps_goal,
            wake_word_enabled,
            auto_brief_enabled
        FROM users
        WHERE id = $1 AND deleted_at IS NULL
        """,
        user_id,
    )
    if row is None:
        return {}
    return dict(row)


async def update_user_settings(
    db: asyncpg.Connection,
    user_id: int,
    *,
    ai_provider: str | None = None,
    ollama_model: str | None = None,
    elevenlabs_voice_id: str | None = None,
    digest_opt_in: bool | None = None,
    nudge_hour: int | None = None,
    weekly_apps_goal: int | None = None,
    wake_word_enabled: bool | None = None,
    auto_brief_enabled: bool | None = None,
) -> dict[str, Any]:
    """Partial update: only fields that are not None are written. Returns the full settings row after update."""
    sets: list[str] = []
    params: list[Any] = [user_id]

    def _add(col: str, val: Any) -> None:
        if val is not None:
            params.append(val)
            sets.append(f"{col} = ${len(params)}")

    _add("ai_provider", ai_provider)
    _add("ollama_model", ollama_model)
    _add("elevenlabs_voice_id", elevenlabs_voice_id)
    _add("digest_opt_in", digest_opt_in)
    _add("nudge_hour", nudge_hour)
    _add("weekly_apps_goal", weekly_apps_goal)
    _add("wake_word_enabled", wake_word_enabled)
    _add("auto_brief_enabled", auto_brief_enabled)

    if sets:
        await db.execute(
            f"UPDATE users SET {', '.join(sets)} WHERE id = $1 AND deleted_at IS NULL",
            *params,
        )
    return await get_user_settings(db, user_id)
