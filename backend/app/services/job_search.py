"""Job search orchestrator.

Queries all configured sources in parallel, deduplicates, caches results in
PostgreSQL, re-ranks by semantic similarity to the user's best-matching resume,
and returns the enriched list.

Sources:
  - JSearch (RapidAPI, paid key)      — 2 pages in one call
  - Adzuna (free key)                 — 2 pages in parallel
  - Arbeitnow (free, no auth)         — keyword search
  - Remotive (free, no auth)          — keyword search
  - Jobicy (free, no auth)            — tag search
  - RemoteOK (free, no auth)          — tag search
  - WeWorkRemotely (RSS, no auth)     — category feed + keyword filter
  - Greenhouse / Lever / Ashby (ATS)  — company watchlist + keyword filter
  - SmartRecruiters (free, no auth)   — verified company boards (freshworks, synechron)

Cache-first: returns from job_cache when ≥15 unexpired FTS-matched rows exist.
Freshness filtering is client-side — the full 3-day window is always returned.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any

import asyncpg
import structlog

from app.config import settings
from app.services import (
    adzuna_client,
    arbeitnow_client,
    ats_client,
    jobicy_client,
    jooble_client,
    jsearch_client,
    remoteok_client,
    remotive_client,
    smartrecruiters_client,
    weworkremotely_client,
)
from app.services.job_ranker import pick_resume, rank_jobs_by_resume

log = structlog.get_logger("job_search")


# ── Freshness helpers ──────────────────────────────────────────────────────────

def _freshness(posted_at: datetime | None) -> dict[str, Any]:
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
    if hours_old is None or first_seen_at is None:
        return None
    if first_seen_at.tzinfo is None:
        first_seen_at = first_seen_at.replace(tzinfo=timezone.utc)
    cache_age_h = (datetime.now(tz=timezone.utc) - first_seen_at).total_seconds() / 3600
    if cache_age_h < 3:
        return None

    def _est(h: float) -> float:
        if h < 6:   return 20
        if h < 24:  return 90
        if h < 48:  return 275
        if h < 72:  return 550
        return 850

    hours_old_at_first_seen = max(0.0, hours_old - cache_age_h)
    gain = _est(hours_old) - _est(hours_old_at_first_seen)

    if gain < 20:
        return "✓ Still early"
    if gain < 100:
        return "↑ Rising"
    return "↑↑ Getting competitive"


# ── DB helpers ─────────────────────────────────────────────────────────────────

def _enrich_row(row: asyncpg.Record, bookmark_map: dict[str, str]) -> dict[str, Any]:
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
        "is_remote": bool(row.get("is_remote") or False),
        "salary_min": row.get("salary_min"),
        "salary_max": row.get("salary_max"),
        "salary_currency": row.get("salary_currency"),
        "tags": list(row.get("tags") or []),
        **f,
        "velocity_label": _velocity_label(f["hours_old"], row.get("first_seen_at")),
        "bookmark_status": bookmark_map.get(bm_key),
        "semantic_score": None,
    }


async def _build_bookmark_map(conn: asyncpg.Connection, user_id: int | None) -> dict[str, str]:
    if user_id is None:
        return {}
    rows = await conn.fetch(
        "SELECT source, external_id, status FROM job_bookmarks WHERE user_id = $1",
        user_id,
    )
    return {f"{r['source']}:{r['external_id']}": r["status"] for r in rows}


async def _upsert_jobs(
    conn: asyncpg.Connection,
    jobs: list[dict[str, Any]],
) -> list[asyncpg.Record]:
    if not jobs:
        return []
    now = datetime.now(tz=timezone.utc)
    expires_at = now + timedelta(hours=settings.job_cache_ttl_hours)
    rows: list[asyncpg.Record] = []
    for j in jobs:
        raw_json = json.dumps(j.get("raw_data") or {}, default=str)
        row = await conn.fetchrow(
            """
            INSERT INTO job_cache
              (source, external_id, title, company, location, description,
               apply_url, posted_at, employment_type, skills,
               is_remote, salary_min, salary_max, salary_currency, tags,
               raw_data, fetched_at, expires_at, first_seen_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16::jsonb,$17,$18,$19)
            ON CONFLICT (source, external_id) DO UPDATE SET
              title          = EXCLUDED.title,
              company        = EXCLUDED.company,
              location       = EXCLUDED.location,
              description    = EXCLUDED.description,
              apply_url      = EXCLUDED.apply_url,
              posted_at      = EXCLUDED.posted_at,
              employment_type= EXCLUDED.employment_type,
              skills         = EXCLUDED.skills,
              is_remote      = EXCLUDED.is_remote,
              salary_min     = EXCLUDED.salary_min,
              salary_max     = EXCLUDED.salary_max,
              salary_currency= EXCLUDED.salary_currency,
              tags           = EXCLUDED.tags,
              raw_data       = EXCLUDED.raw_data,
              fetched_at     = EXCLUDED.fetched_at,
              expires_at     = EXCLUDED.expires_at
            RETURNING *
            """,
            j["source"], j["external_id"], j["title"], j["company"],
            j.get("location"), j.get("description"), j.get("apply_url", ""),
            j.get("posted_at"), j.get("employment_type"),
            j.get("skills") or [],
            bool(j.get("is_remote", False)),
            j.get("salary_min"), j.get("salary_max"), j.get("salary_currency"),
            j.get("tags") or [],
            raw_json, now, expires_at, now,
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


# ── Result post-filters ───────────────────────────────────────────────────────

_SENIOR_TERMS = {"senior", " lead ", "principal", "staff ", " sr.", "sr "}
_JUNIOR_TERMS = {"junior", "entry level", "fresher", "trainee", "associate engineer"}


def _apply_filters(
    results: list[dict[str, Any]],
    remote_only: bool,
    location: str | None,
    experience: str | None,
) -> list[dict[str, Any]]:
    if remote_only:
        results = [r for r in results if r.get("is_remote")]

    if location:
        loc_lower = location.lower()
        results = [
            r for r in results
            if r.get("is_remote") or loc_lower in (r.get("location") or "").lower()
        ]

    if experience == "entry":
        results = [
            r for r in results
            if not any(t in (" " + (r.get("title") or "").lower() + " ") for t in _SENIOR_TERMS)
        ]
    elif experience == "senior":
        results = [
            r for r in results
            if not any(t in (r.get("title") or "").lower() for t in _JUNIOR_TERMS)
        ]

    return results


# ── Exact-key query result cache ──────────────────────────────────────────────

def _cache_key(query: str, location: str | None, remote_only: bool, experience: str | None) -> str:
    """MD5 of normalised search parameters — used as the exact cache lookup key."""
    raw = f"{query.lower().strip()}|{(location or '').lower().strip()}|{remote_only}|{experience or ''}"
    return hashlib.md5(raw.encode()).hexdigest()


async def _read_search_cache(
    conn: asyncpg.Connection,
    query: str,
    location: str | None,
    remote_only: bool,
    experience: str | None,
    user_id: int | None,
) -> list[dict[str, Any]] | None:
    """Return cached job list if a valid (unexpired) entry exists, else None."""
    key = _cache_key(query, location, remote_only, experience)
    row = await conn.fetchrow(
        "SELECT job_ids FROM job_search_cache WHERE query_hash=$1 AND expires_at > now()",
        key,
    )
    if not row or not row["job_ids"]:
        return None
    job_ids: list[int] = list(row["job_ids"])
    # Fetch from job_cache in the cached order (preserve freshness sort)
    rows = await conn.fetch(
        "SELECT * FROM job_cache WHERE id = ANY($1::int[]) AND expires_at > now()",
        job_ids,
    )
    if not rows:
        return None
    # Re-sort to match the original cached order
    rows_by_id = {r["id"]: r for r in rows}
    ordered = [rows_by_id[jid] for jid in job_ids if jid in rows_by_id]
    bookmark_map = await _build_bookmark_map(conn, user_id)
    return [_enrich_row(r, bookmark_map) for r in ordered]


async def _write_search_cache(
    conn: asyncpg.Connection,
    query: str,
    location: str | None,
    remote_only: bool,
    experience: str | None,
    results: list[dict[str, Any]],
) -> None:
    """Upsert the result set's job IDs into job_search_cache with 4h TTL."""
    key = _cache_key(query, location, remote_only, experience)
    job_ids = [r["id"] for r in results if r.get("id")]
    expires_at = datetime.now(tz=timezone.utc) + timedelta(hours=settings.job_cache_ttl_hours)
    await conn.execute(
        """
        INSERT INTO job_search_cache
          (query_hash, query, location, remote_only, experience, job_ids, expires_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (
            query_hash,
            COALESCE(location, ''),
            remote_only,
            COALESCE(experience, '')
        ) DO UPDATE SET
            job_ids    = EXCLUDED.job_ids,
            expires_at = EXCLUDED.expires_at,
            created_at = now()
        """,
        key, query, location, remote_only, experience, job_ids, expires_at,
    )


# ── Main search ────────────────────────────────────────────────────────────────

async def search_jobs(
    conn: asyncpg.Connection,
    query: str,
    location: str | None = None,
    remote_only: bool = False,
    experience: str | None = None,
    user_id: int | None = None,
) -> list[dict[str, Any]]:
    """Fetch jobs from all sources, cache, and return sorted by freshness.

    Exact-key cache: hashes (query, location, remote_only, experience) → job_ids[] with 4h TTL.
    Repeat searches return in <5ms. Remote-only boards skipped for location searches.
    """
    # 1. Exact-key cache hit — return immediately
    cached = await _read_search_cache(conn, query, location, remote_only, experience, user_id)
    if cached is not None:
        log.info("job_search.cache_hit", query=query, total=len(cached))
        return _apply_filters(cached, remote_only=remote_only, location=location, experience=experience)

    # 2. FTS warm cache (legacy path for partial matches while exact cache is cold)
    if not remote_only:
        fts_cached = await _query_cache(conn, query, location, user_id)
        if len(fts_cached) >= 15:
            log.info("job_search.fts_cache_hit", query=query, total=len(fts_cached))
            results = _apply_filters(fts_cached, remote_only=False, location=location, experience=experience)
            await _write_search_cache(conn, query, location, remote_only, experience, results)
            return results

    # Sources that support location-based filtering — always queried
    tasks = [
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
        arbeitnow_client.search(query),
        ats_client.search(query),
        smartrecruiters_client.search(query),
        jooble_client.search(query, location),
    ]

    # Remote-only boards — only when user explicitly requests remote jobs
    if remote_only:
        tasks += [
            remotive_client.search(query),
            jobicy_client.search(query),
            remoteok_client.search(query),
            weworkremotely_client.search(query),
        ]

    batches = await asyncio.gather(*tasks, return_exceptions=True)

    all_raw: list[dict[str, Any]] = []
    for batch in batches:
        if isinstance(batch, list):
            all_raw.extend(batch)

    # Dedup by (source, external_id)
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for j in all_raw:
        key = f"{j['source']}:{j['external_id']}"
        if key not in seen and j.get("apply_url") and j.get("title"):
            seen.add(key)
            unique.append(j)

    cached_rows = await _upsert_jobs(conn, unique)
    bookmark_map = await _build_bookmark_map(conn, user_id)

    results = [_enrich_row(row, bookmark_map) for row in cached_rows]
    results.sort(key=lambda x: x["freshness_score"], reverse=True)

    results = _apply_filters(results, remote_only=remote_only, location=location, experience=experience)

    # Write to exact-key cache for future requests
    await _write_search_cache(conn, query, location, remote_only, experience, results)

    log.info(
        "job_search.completed",
        query=query,
        total=len(results),
        raw=len(all_raw),
        unique=len(unique),
    )
    return results


# ── Similar jobs ───────────────────────────────────────────────────────────────

async def get_similar_jobs(
    conn: asyncpg.Connection,
    job_cache_id: int,
    user_id: int | None = None,
    limit: int = 3,
) -> list[dict[str, Any]]:
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
