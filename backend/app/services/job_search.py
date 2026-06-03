"""Job search orchestrator.

Queries JSearch + Adzuna in parallel, deduplicates, caches results in
PostgreSQL, and enriches each job with freshness + competition scores.
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


def _cache_key(source: str, external_id: str) -> str:
    return f"{source}:{external_id}"


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
               fetched_at, expires_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11::jsonb,$12,$13)
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
            RETURNING *
            """,
            j["source"], j["external_id"], j["title"], j["company"],
            j.get("location"), j.get("description"), j["apply_url"],
            j.get("posted_at"), j.get("employment_type"),
            skills_arr, raw_json, now, expires_at,
        )
        if row:
            rows.append(row)
    return rows


async def search_jobs(
    conn: asyncpg.Connection,
    query: str,
    location: str | None = None,
    remote_only: bool = False,
    experience: str | None = None,
    freshness_hours: int = 24,
    user_id: int | None = None,
    page: int = 1,
) -> list[dict[str, Any]]:
    """Query both APIs, cache results, enrich with freshness, return sorted list."""
    if freshness_hours <= 24:
        jsearch_date = "today"
    elif freshness_hours <= 72:
        jsearch_date = "3days"
    else:
        jsearch_date = "week"

    jsearch_results, adzuna_results = await asyncio.gather(
        jsearch_client.search(
            query=query,
            location=location,
            remote_only=remote_only,
            experience=experience,
            date_posted=jsearch_date,
            page=page,
        ),
        adzuna_client.search(
            query=query,
            location=location,
            max_days_old=max(1, freshness_hours // 24),
            page=page,
        ),
    )

    all_raw = jsearch_results + adzuna_results

    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for j in all_raw:
        key = _cache_key(j["source"], j["external_id"])
        if key not in seen:
            seen.add(key)
            unique.append(j)

    cached_rows = await _upsert_jobs(conn, unique)

    bookmark_map: dict[str, str] = {}
    if user_id is not None:
        bm_rows = await conn.fetch(
            "SELECT source, external_id, status FROM job_bookmarks WHERE user_id = $1",
            user_id,
        )
        for bm in bm_rows:
            bookmark_map[f"{bm['source']}:{bm['external_id']}"] = bm["status"]

    results: list[dict[str, Any]] = []
    for row in cached_rows:
        f = _freshness(row["posted_at"])
        bm_key = f"{row['source']}:{row['external_id']}"
        results.append({
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
            "bookmark_status": bookmark_map.get(bm_key),
        })

    results.sort(key=lambda x: x["freshness_score"], reverse=True)

    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=freshness_hours)
    def _within_cutoff(posted_at: datetime | None) -> bool:
        if posted_at is None:
            return True
        if posted_at.tzinfo is None:
            posted_at = posted_at.replace(tzinfo=timezone.utc)
        return posted_at >= cutoff

    results = [r for r in results if _within_cutoff(r["posted_at"])]

    log.info(
        "job_search.completed",
        query=query, total=len(results),
        jsearch=len(jsearch_results), adzuna=len(adzuna_results),
    )
    return results
