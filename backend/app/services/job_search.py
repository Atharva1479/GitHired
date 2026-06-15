"""Job search orchestrator.

Queries JSearch + Adzuna in parallel, deduplicates, caches results in
PostgreSQL, and enriches each job with freshness + competition scores.

Always fetches the last 3 days across two pages per API (3 concurrent
requests: JSearch num_pages=2, Adzuna page 1, Adzuna page 2).
Cache-first: skips API calls when >=15 unexpired FTS-matched rows exist.
Freshness filtering is client-side — the full 3-day set is returned.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Any

import asyncpg
import structlog

from app.config import settings
from app.services import adzuna_client, jsearch_client

log = structlog.get_logger("job_search")


def _freshness(posted_at: datetime | None) -> dict[str, Any]:
    """Compute competition metadata from posting time."""
    if posted_at is None:
        return {
            "hours_old": None,
            "freshness_score": 40,
            "freshness_label": "Unknown Age",
            "freshness_color": "zinc",
            "est_applicants": "Unknown",
        }

    now = datetime.now(tz=timezone.utc)
    if posted_at.tzinfo is None:
        posted_at = posted_at.replace(tzinfo=timezone.utc)
    hours_old = max(0.0, (now - posted_at).total_seconds() / 3600)

    if hours_old < 6:
        score, label, color, est = 95, "🔥 Just Posted", "emerald", "< 30"
    elif hours_old < 24:
        score, label, color, est = 78, "⚡ Fresh", "green", "30–150"
    elif hours_old < 48:
        score, label, color, est = 55, "🟡 Recent", "amber", "150–400"
    elif hours_old < 72:
        score, label, color, est = 35, "🟠 Competitive", "orange", "400–700"
    else:
        score, label, color, est = 15, "🔴 High Competition", "red", "700+"

    return {
        "hours_old": round(hours_old, 1),
        "freshness_score": score,
        "freshness_label": label,
        "freshness_color": color,
        "est_applicants": est,
    }


def _velocity_label(hours_old: float | None, first_seen_at: datetime | None) -> str | None:
    """Estimate how competition has grown since we first discovered this job.

    Only meaningful when the job has been in our cache for 3+ hours.
    """
    if hours_old is None or first_seen_at is None:
        return None
    if first_seen_at.tzinfo is None:
        first_seen_at = first_seen_at.replace(tzinfo=timezone.utc)
    cache_age_h = (datetime.now(tz=timezone.utc) - first_seen_at).total_seconds() / 3600
    if cache_age_h < 3:
        return None  # Too fresh to measure meaningful change

    # Approx applicants when first seen vs now using the same tiers
    def _est(h: float) -> float:
        if h < 6:   return 20
        if h < 24:  return 90
        if h < 48:  return 275
        if h < 72:  return 550
        return 850

    hours_old_at_first_seen = max(0.0, hours_old - cache_age_h)
    then_est = _est(hours_old_at_first_seen)
    now_est  = _est(hours_old)
    gain     = now_est - then_est

    if gain < 20:
        return "✓ Still early"
    if gain < 100:
        return "↑ Rising"
    return "↑↑ Getting competitive"


def _cache_key(source: str, external_id: str) -> str:
    return f"{source}:{external_id}"


def _enrich_row(
    row: asyncpg.Record,
    bookmark_map: dict[str, str],
) -> dict[str, Any]:
    """Build result dict from a job_cache row + bookmark lookup."""
    f = _freshness(row["posted_at"])
    bm_key = f"{row['source']}:{row['external_id']}"
    return {
        "id": row["id"],
        "source": row["source"],
        "external_id": row["external_id"],
        "title": row["title"],
        "company": row["company"],
        "location": row["location"],
        "description": row["description"],
        "apply_url": row["apply_url"],
        "posted_at": row["posted_at"],
        "employment_type": row["employment_type"],
        "skills": list(row["skills"] or []),
        **f,
        "velocity_label": _velocity_label(f["hours_old"], row.get("first_seen_at")),
        "bookmark_status": bookmark_map.get(bm_key),
    }


async def _build_bookmark_map(
    conn: asyncpg.Connection,
    user_id: int | None,
) -> dict[str, str]:
    if user_id is None:
        return {}
    bm_rows = await conn.fetch(
        "SELECT source, external_id, status FROM job_bookmarks WHERE user_id = $1",
        user_id,
    )
    return {f"{bm['source']}:{bm['external_id']}": bm["status"] for bm in bm_rows}


async def _upsert_jobs(
    conn: asyncpg.Connection,
    jobs: list[dict[str, Any]],
) -> list[asyncpg.Record]:
    """Upsert jobs into job_cache and return the full rows."""
    if not jobs:
        return []
    ttl = timedelta(hours=settings.job_cache_ttl_hours)
    now = datetime.now(tz=timezone.utc)
    expires_at = now + ttl

    rows: list[asyncpg.Record] = []
    for j in jobs:
        raw_json = json.dumps(j["raw_data"], default=str)
        skills_arr = j.get("skills") or []
        row = await conn.fetchrow(
            """
            INSERT INTO job_cache
              (source, external_id, title, company, location, description,
               apply_url, posted_at, employment_type, skills, raw_data,
               fetched_at, expires_at, first_seen_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11::jsonb,$12,$13,$14)
            ON CONFLICT (source, external_id) DO UPDATE SET
              title          = EXCLUDED.title,
              company        = EXCLUDED.company,
              location       = EXCLUDED.location,
              description    = EXCLUDED.description,
              apply_url      = EXCLUDED.apply_url,
              posted_at      = EXCLUDED.posted_at,
              employment_type= EXCLUDED.employment_type,
              skills         = EXCLUDED.skills,
              raw_data       = EXCLUDED.raw_data,
              fetched_at     = EXCLUDED.fetched_at,
              expires_at     = EXCLUDED.expires_at
              -- first_seen_at intentionally NOT updated (preserves first discovery time)
            RETURNING *
            """,
            j["source"], j["external_id"], j["title"], j["company"],
            j.get("location"), j.get("description"), j["apply_url"],
            j.get("posted_at"), j.get("employment_type"),
            skills_arr, raw_json, now, expires_at, now,
        )
        if row:
            rows.append(row)
    return rows


async def _query_cache(
    conn: asyncpg.Connection,
    query: str,
    location: str | None,
    user_id: int | None,
) -> list[dict[str, Any]]:
    """Return enriched jobs from job_cache using FTS — skips API calls on warm cache.

    Returns up to 60 unexpired rows matching the query via PostgreSQL full-text search.
    """
    rows = await conn.fetch(
        """
        SELECT *
        FROM job_cache
        WHERE expires_at > now()
          AND (
            to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(description, ''))
            @@ plainto_tsquery('english', $1)
          )
          AND ($2::text IS NULL OR location ILIKE '%' || $2 || '%')
        ORDER BY posted_at DESC NULLS LAST
        LIMIT 60
        """,
        query, location,
    )
    if not rows:
        return []
    bookmark_map = await _build_bookmark_map(conn, user_id)
    results = [_enrich_row(r, bookmark_map) for r in rows]
    results.sort(key=lambda x: x["freshness_score"], reverse=True)
    return results


async def search_jobs(
    conn: asyncpg.Connection,
    query: str,
    location: str | None = None,
    remote_only: bool = False,
    experience: str | None = None,
    user_id: int | None = None,
) -> list[dict[str, Any]]:
    """Fetch jobs for last 3 days (2 pages per API), cache, and return sorted list.

    Cache-first: returns from job_cache when >=15 FTS-matched rows are unexpired.
    Remote-only searches always hit the API (no is_remote column in cache).
    No server-side freshness post-filter — the full 3-day set is returned so the
    frontend can filter client-side without triggering a new request.
    """
    if not remote_only:
        cached = await _query_cache(conn, query, location, user_id)
        if len(cached) >= 15:
            log.info("job_search.cache_hit", query=query, total=len(cached))
            return cached

    # Fetch 3-day window: JSearch (num_pages=2) + Adzuna pages 1 and 2 in parallel.
    jsearch_raw, adzuna_p1, adzuna_p2 = await asyncio.gather(
        jsearch_client.search(
            query=query,
            location=location,
            remote_only=remote_only,
            experience=experience,
            date_posted="3days",
            page=1,
            num_pages=2,
        ),
        adzuna_client.search(query=query, location=location, max_days_old=3, page=1),
        adzuna_client.search(query=query, location=location, max_days_old=3, page=2),
        return_exceptions=True,
    )

    all_raw: list[dict[str, Any]] = []
    for batch in (jsearch_raw, adzuna_p1, adzuna_p2):
        if isinstance(batch, list):
            all_raw.extend(batch)

    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for j in all_raw:
        key = _cache_key(j["source"], j["external_id"])
        if key not in seen:
            seen.add(key)
            unique.append(j)

    cached_rows = await _upsert_jobs(conn, unique)
    bookmark_map = await _build_bookmark_map(conn, user_id)

    results = [_enrich_row(row, bookmark_map) for row in cached_rows]
    results.sort(key=lambda x: x["freshness_score"], reverse=True)

    log.info(
        "job_search.completed",
        query=query, total=len(results), raw=len(all_raw),
    )
    return results


async def get_similar_jobs(
    conn: asyncpg.Connection,
    job_cache_id: int,
    user_id: int | None = None,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Find similar fresh jobs from the cache using full-text title matching."""
    source_row = await conn.fetchrow(
        "SELECT title, skills FROM job_cache WHERE id = $1", job_cache_id
    )
    if not source_row:
        return []

    rows = await conn.fetch(
        """
        SELECT * FROM job_cache
        WHERE id != $1
          AND expires_at > now()
          AND to_tsvector('english', title) @@ plainto_tsquery('english', $2)
        ORDER BY posted_at DESC NULLS LAST
        LIMIT $3
        """,
        job_cache_id, source_row["title"], limit,
    )

    bookmark_map = await _build_bookmark_map(conn, user_id)
    return [_enrich_row(row, bookmark_map) for row in rows]
