"""Job search orchestrator — Fan-Out + Scatter-Gather with tiered sources.

Architecture:
  - Tier 1 (paid/reliable): JSearch, Adzuna ×2 — timeout 6 s
  - Tier 2 (free/supplementary): Arbeitnow, ATS, SmartRecruiters, Jooble, SerpAPI — timeout 10 s
  - Remote-only boards added to Tier 2 when remote_only=True

Request flow:
  1. Exact-key cache hit (<5 ms) — serve immediately; trigger background
     refresh if age > 3 h (Stale-While-Revalidate).
  2. FTS warm-cache hit (≥15 rows) — serve from job_cache.
  3. Live fetch — fire Tier 1 + Tier 2 simultaneously as asyncio Tasks.
       • If Tier 1 returns ≥ MIN_EARLY_RETURN jobs within 6 s → return early,
         let Tier 2 finish in background and update cache.
       • Otherwise wait for Tier 2 (total budget 12 s), return combined results.
  4. All source calls are wrapped with per-source timeout + circuit breaker.
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
    serpapi_client,
    smartrecruiters_client,
    weworkremotely_client,
)
from app.services.circuit_breaker import get_breaker
from app.services.job_ranker import pick_resume, rank_jobs_by_resume

log = structlog.get_logger("job_search")

# ── Timing constants ───────────────────────────────────────────────────────────
_T1 = 6.0    # Tier-1 source timeout (paid APIs — reliable, fast)
_T2 = 10.0   # Tier-2 source timeout (free APIs — slower, less reliable)
TIER1_DEADLINE = 6.0   # wait this long for Tier-1 results
TIER2_BUDGET   = 12.0  # absolute max response time (Tier-1 + remaining)
MIN_EARLY_RETURN = 10  # return Tier-1 results early if we get at least this many
REVALIDATE_AFTER_SECONDS = 10_800  # 3 h = 75 % of 4 h TTL → trigger background refresh


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

    if gain < 20:   return "✓ Still early"
    if gain < 100:  return "↑ Rising"
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


# ── Result helpers ─────────────────────────────────────────────────────────────

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


def _dedup(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for j in raw:
        k = f"{j['source']}:{j['external_id']}"
        if k not in seen and j.get("apply_url") and j.get("title"):
            seen.add(k)
            unique.append(j)
    return unique


# ── Exact-key query result cache ──────────────────────────────────────────────

def _cache_key(query: str, location: str | None, remote_only: bool, experience: str | None) -> str:
    raw = f"{query.lower().strip()}|{(location or '').lower().strip()}|{remote_only}|{experience or ''}"
    return hashlib.md5(raw.encode()).hexdigest()


async def _read_search_cache(
    conn: asyncpg.Connection,
    query: str,
    location: str | None,
    remote_only: bool,
    experience: str | None,
    user_id: int | None,
) -> tuple[list[dict[str, Any]], datetime] | None:
    """Return (jobs, created_at) if a valid unexpired cache entry exists, else None."""
    key = _cache_key(query, location, remote_only, experience)
    row = await conn.fetchrow(
        "SELECT job_ids, created_at FROM job_search_cache WHERE query_hash=$1 AND expires_at > now()",
        key,
    )
    if not row or not row["job_ids"]:
        return None
    job_ids: list[int] = list(row["job_ids"])
    rows = await conn.fetch(
        "SELECT * FROM job_cache WHERE id = ANY($1::int[]) AND expires_at > now()",
        job_ids,
    )
    if not rows:
        return None
    rows_by_id = {r["id"]: r for r in rows}
    ordered = [rows_by_id[jid] for jid in job_ids if jid in rows_by_id]
    bookmark_map = await _build_bookmark_map(conn, user_id)
    jobs = [_enrich_row(r, bookmark_map) for r in ordered]
    return jobs, row["created_at"]


async def _write_search_cache(
    conn: asyncpg.Connection,
    query: str,
    location: str | None,
    remote_only: bool,
    experience: str | None,
    results: list[dict[str, Any]],
) -> None:
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


# ── Source task builder ────────────────────────────────────────────────────────

def _build_source_tasks(
    query: str,
    location: str | None,
    remote_only: bool,
    experience: str | None,
) -> tuple[list[tuple[str, Any, float]], list[tuple[str, Any, float]]]:
    """Return (tier1, tier2) lists of (source_name, coroutine, timeout_seconds).

    Tier 1 — paid/reliable: JSearch + Adzuna (2 pages). Fast, high quality.
    Tier 2 — free/supplementary: Arbeitnow, ATS, Jooble, SerpAPI, etc.
    """
    tier1: list[tuple[str, Any, float]] = [
        ("jsearch",   jsearch_client.search(
            query=query, location=location, remote_only=remote_only,
            experience=experience, date_posted="3days", page=1, num_pages=2,
        ), _T1),
        ("adzuna_p1", adzuna_client.search(query=query, location=location, max_days_old=3, page=1), _T1),
        ("adzuna_p2", adzuna_client.search(query=query, location=location, max_days_old=3, page=2), _T1),
    ]
    tier2: list[tuple[str, Any, float]] = [
        ("arbeitnow",       arbeitnow_client.search(query), _T2),
        ("ats",             ats_client.search(query), _T2),
        ("smartrecruiters", smartrecruiters_client.search(query), _T2),
        ("jooble",          jooble_client.search(query, location), _T2),
        ("serpapi",         serpapi_client.search(query, location), _T2),
    ]
    if remote_only:
        tier2 += [
            ("remotive",       remotive_client.search(query), _T2),
            ("jobicy",         jobicy_client.search(query), _T2),
            ("remoteok",       remoteok_client.search(query), _T2),
            ("weworkremotely", weworkremotely_client.search(query), _T2),
        ]
    return tier1, tier2


def _collect_done(futures: set[asyncio.Task]) -> list[dict[str, Any]]:
    """Extract flat job list from a set of completed asyncio Tasks."""
    jobs: list[dict[str, Any]] = []
    for fut in futures:
        if fut.cancelled():
            continue
        try:
            result = fut.result()
            if isinstance(result, list):
                jobs.extend(result)
        except Exception:
            pass
    return jobs


async def _process_and_cache(
    conn: asyncpg.Connection,
    raw_jobs: list[dict[str, Any]],
    query: str,
    location: str | None,
    remote_only: bool,
    experience: str | None,
    user_id: int | None,
) -> list[dict[str, Any]]:
    """Dedup → upsert → enrich → sort → filter → write cache. Returns final list."""
    unique = _dedup(raw_jobs)
    if not unique:
        return []
    rows = await _upsert_jobs(conn, unique)
    bookmark_map = await _build_bookmark_map(conn, user_id)
    results = [_enrich_row(r, bookmark_map) for r in rows]
    results.sort(key=lambda x: x["freshness_score"], reverse=True)
    results = _apply_filters(results, remote_only=remote_only, location=location, experience=experience)
    await _write_search_cache(conn, query, location, remote_only, experience, results)
    return results


# ── Background helpers (own DB connection) ─────────────────────────────────────

async def _finalize_tier2(
    tier2_tasks: list[asyncio.Task],
    existing_results: list[dict[str, Any]],
    query: str,
    location: str | None,
    remote_only: bool,
    experience: str | None,
    user_id: int | None,
) -> None:
    """Background: wait for Tier-2 tasks, merge with early-return results, update cache."""
    from app.database import pool as get_pool  # late import — avoids circular at module load
    try:
        done, pending = await asyncio.wait(tier2_tasks, timeout=_T2)
        for fut in pending:
            fut.cancel()
        tier2_jobs = _collect_done(done)
        if not tier2_jobs:
            return

        existing_keys = {f"{r['source']}:{r['external_id']}" for r in existing_results}
        new_jobs = [j for j in tier2_jobs if f"{j['source']}:{j['external_id']}" not in existing_keys]
        if not new_jobs:
            return

        async with get_pool().acquire() as conn:
            rows = await _upsert_jobs(conn, _dedup(new_jobs))
            bookmark_map = await _build_bookmark_map(conn, user_id)
            combined = existing_results + [_enrich_row(r, bookmark_map) for r in rows]
            combined.sort(key=lambda x: x["freshness_score"], reverse=True)
            combined = _apply_filters(combined, remote_only=remote_only, location=location, experience=experience)
            await _write_search_cache(conn, query, location, remote_only, experience, combined)
            log.info("job_search.tier2_finalized", query=query, new_jobs=len(new_jobs), total=len(combined))

    except Exception as exc:
        log.warning("job_search.tier2_finalize_error", query=query, error=str(exc))


async def _background_refresh(
    query: str,
    location: str | None,
    remote_only: bool,
    experience: str | None,
    user_id: int | None,
) -> None:
    """Stale-While-Revalidate: full live fetch in background after serving a stale cache hit."""
    from app.database import pool as get_pool
    try:
        tier1, tier2 = _build_source_tasks(query, location, remote_only, experience)
        all_source_tasks = [
            asyncio.create_task(get_breaker(name).call(coro, timeout))
            for name, coro, timeout in tier1 + tier2
        ]
        done, pending = await asyncio.wait(all_source_tasks, timeout=TIER2_BUDGET)
        for fut in pending:
            fut.cancel()
        raw_jobs = _collect_done(done)
        if not raw_jobs:
            return
        async with get_pool().acquire() as conn:
            await _process_and_cache(conn, raw_jobs, query, location, remote_only, experience, user_id)
            log.info("job_search.swr_refresh_done", query=query, total=len(raw_jobs))
    except Exception as exc:
        log.warning("job_search.swr_refresh_error", query=query, error=str(exc))


# ── Main search ────────────────────────────────────────────────────────────────

async def search_jobs(
    conn: asyncpg.Connection,
    query: str,
    location: str | None = None,
    remote_only: bool = False,
    experience: str | None = None,
    user_id: int | None = None,
) -> list[dict[str, Any]]:
    """Tiered fan-out job search with circuit breaker, per-source timeouts, and SWR cache.

    Response time targets:
      - Cache hit (fresh):  <10 ms
      - Cache hit (stale):  <10 ms  + background refresh
      - Tier-1 early return: ~6 s   (≥10 jobs from JSearch/Adzuna)
      - Full fetch:         ≤12 s   (Tier-1 + Tier-2 combined)
    """
    now = datetime.now(tz=timezone.utc)

    # ── 1. Exact-key cache ─────────────────────────────────────────────────────
    cache_result = await _read_search_cache(conn, query, location, remote_only, experience, user_id)
    if cache_result is not None:
        jobs, created_at = cache_result
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        age = (now - created_at).total_seconds()
        if age > REVALIDATE_AFTER_SECONDS:
            log.info("job_search.swr_triggered", query=query, age_hours=round(age / 3600, 1))
            asyncio.create_task(
                _background_refresh(query, location, remote_only, experience, user_id)
            )
        else:
            log.info("job_search.cache_hit", query=query, total=len(jobs))
        return jobs

    # ── 2. FTS warm cache (legacy — partial match while exact cache is cold) ───
    if not remote_only:
        fts_cached = await _query_cache(conn, query, location, user_id)
        if len(fts_cached) >= 15:
            log.info("job_search.fts_cache_hit", query=query, total=len(fts_cached))
            results = _apply_filters(fts_cached, remote_only=False, location=location, experience=experience)
            await _write_search_cache(conn, query, location, remote_only, experience, results)
            return results

    # ── 3. Live fetch — tiered scatter-gather ──────────────────────────────────
    tier1_specs, tier2_specs = _build_source_tasks(query, location, remote_only, experience)

    # Fire ALL tasks simultaneously — Tier 2 starts running NOW, not after Tier 1
    tier1_tasks = [
        asyncio.create_task(get_breaker(name).call(coro, timeout), name=f"t1:{name}")
        for name, coro, timeout in tier1_specs
    ]
    tier2_tasks = [
        asyncio.create_task(get_breaker(name).call(coro, timeout), name=f"t2:{name}")
        for name, coro, timeout in tier2_specs
    ]

    # Wait for Tier 1 (primary sources)
    tier1_done, tier1_pending = await asyncio.wait(tier1_tasks, timeout=TIER1_DEADLINE)
    for fut in tier1_pending:
        fut.cancel()  # Tier-1 stragglers — cancel, Tier-2 is already running

    tier1_jobs = _collect_done(tier1_done)
    log.info("job_search.tier1_done", query=query, jobs=len(tier1_jobs))

    if len(tier1_jobs) >= MIN_EARLY_RETURN:
        # ── Early return: enough primary results — serve now, merge Tier-2 in background
        results = await _process_and_cache(
            conn, tier1_jobs, query, location, remote_only, experience, user_id
        )
        asyncio.create_task(
            _finalize_tier2(tier2_tasks, results, query, location, remote_only, experience, user_id)
        )
        log.info("job_search.early_return", query=query, total=len(results))
        return results

    # ── Full wait: not enough from Tier 1 — wait for Tier 2 with remaining budget
    remaining = max(0.5, TIER2_BUDGET - TIER1_DEADLINE)
    tier2_done, tier2_pending = await asyncio.wait(tier2_tasks, timeout=remaining)
    for fut in tier2_pending:
        fut.cancel()

    tier2_jobs = _collect_done(tier2_done)
    all_raw = tier1_jobs + tier2_jobs

    results = await _process_and_cache(
        conn, all_raw, query, location, remote_only, experience, user_id
    )
    log.info(
        "job_search.completed",
        query=query,
        total=len(results),
        raw=len(all_raw),
        tier1=len(tier1_jobs),
        tier2=len(tier2_jobs),
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
