"""Database layer for job discovery: saved searches and bookmarks."""
from __future__ import annotations

from datetime import datetime
from typing import Any

import asyncpg


# ── Saved searches ────────────────────────────────────────────────────────────

async def list_searches(
    conn: asyncpg.Connection,
    user_id: int,
) -> list[asyncpg.Record]:
    return await conn.fetch(
        "SELECT * FROM job_searches WHERE user_id = $1 ORDER BY created_at DESC",
        user_id,
    )


async def create_search(
    conn: asyncpg.Connection,
    user_id: int,
    name: str,
    query: str,
    location: str | None,
    remote_only: bool,
    experience: str | None,
    freshness_hours: int,
) -> asyncpg.Record:
    return await conn.fetchrow(
        """
        INSERT INTO job_searches
          (user_id, name, query, location, remote_only, experience, freshness_hours)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING *
        """,
        user_id, name, query, location, remote_only, experience, freshness_hours,
    )


async def delete_search(
    conn: asyncpg.Connection,
    search_id: int,
    user_id: int,
) -> bool:
    result = await conn.execute(
        "DELETE FROM job_searches WHERE id = $1 AND user_id = $2",
        search_id, user_id,
    )
    return result == "DELETE 1"


async def update_search_alerted(
    conn: asyncpg.Connection,
    search_id: int,
) -> None:
    await conn.execute(
        "UPDATE job_searches SET last_alerted_at = now() WHERE id = $1",
        search_id,
    )


async def list_active_searches_all_users(
    conn: asyncpg.Connection,
) -> list[asyncpg.Record]:
    return await conn.fetch(
        "SELECT * FROM job_searches WHERE is_active = true"
    )


# ── Bookmarks ─────────────────────────────────────────────────────────────────

async def upsert_bookmark(
    conn: asyncpg.Connection,
    user_id: int,
    job_cache_id: int,
    title: str,
    company: str,
    apply_url: str,
    posted_at: datetime | None,
    source: str,
    external_id: str,
    status: str = "bookmarked",
    application_id: int | None = None,
) -> asyncpg.Record:
    return await conn.fetchrow(
        """
        INSERT INTO job_bookmarks
          (user_id, job_cache_id, title, company, apply_url, posted_at,
           source, external_id, status, application_id)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
        ON CONFLICT (user_id, source, external_id) DO UPDATE SET
          status         = EXCLUDED.status,
          application_id = COALESCE(EXCLUDED.application_id, job_bookmarks.application_id)
        RETURNING *
        """,
        user_id, job_cache_id, title, company, apply_url, posted_at,
        source, external_id, status, application_id,
    )


async def list_bookmarks(
    conn: asyncpg.Connection,
    user_id: int,
    status: str | None = None,
) -> list[asyncpg.Record]:
    if status:
        return await conn.fetch(
            "SELECT * FROM job_bookmarks WHERE user_id=$1 AND status=$2 ORDER BY created_at DESC",
            user_id, status,
        )
    return await conn.fetch(
        "SELECT * FROM job_bookmarks WHERE user_id=$1 ORDER BY created_at DESC",
        user_id,
    )


async def get_bookmark(
    conn: asyncpg.Connection,
    bookmark_id: int,
    user_id: int,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        "SELECT * FROM job_bookmarks WHERE id=$1 AND user_id=$2",
        bookmark_id, user_id,
    )
