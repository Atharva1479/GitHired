"""Direct ATS board crawler — Greenhouse, Lever, Ashby.

Each ATS has a public JSON endpoint per company slug (no auth required).
Results are cached per-slug for 24h (company boards change slowly).
A semaphore caps concurrency at 10 to avoid hammering ATS servers.
"""
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

import httpx
import structlog

log = structlog.get_logger("ats_client")

_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_CACHE_TTL = 86400  # 24 hours
_SEM_SIZE = 10
_SEM = asyncio.Semaphore(_SEM_SIZE)

# ── Company watchlist ──────────────────────────────────────────────────────────
# Add/remove slugs as needed. Find a company's slug by visiting their careers
# page URL — it's usually in the path: boards.greenhouse.io/{slug}

WATCHLIST: dict[str, list[str]] = {
    "greenhouse": [
        # ── Global remote-friendly (verified 2026-06-16) ──────────────────────
        "stripe", "databricks", "brex", "twilio", "gitlab",
        "coinbase", "dropbox",

        # ── Bangalore — Product ───────────────────────────────────────────────
        "browserstack",   # Bangalore — dev tools (product)
        "postman",        # Bangalore — API platform (product)
        "phonepe",        # Bangalore — fintech (product)
        "slice",          # Bangalore — neobank (product)
        "groww",          # Bangalore — stock trading (product)

        # ── Gurgaon ───────────────────────────────────────────────────────────
        "naukri",         # Gurgaon — job platform / Info Edge

        # ── Pan-India / Service ───────────────────────────────────────────────
        "thoughtworks",   # Bangalore/Pune/Hyderabad — consulting + product eng
    ],
    "lever": [
        # ── Bangalore — Product ───────────────────────────────────────────────
        "meesho",         # Bangalore — e-commerce (product)
        "cred",           # Bangalore — fintech (product)

        # ── Gurgaon ───────────────────────────────────────────────────────────
        "paytm",          # Gurgaon / Noida — fintech (product)
    ],
    "ashby": [
        # ── Global startups (return 200; may have 0 roles when not hiring) ────
        "linear", "vercel", "supabase", "loom", "railway",
        "cursor", "perplexity",
    ],
}

# Derived circuit-breaker timeout: total slugs spread across _SEM_SIZE concurrent
# connections, 4s per request, plus 10s buffer. Automatically grows when WATCHLIST grows.
_total_slugs = sum(len(slugs) for slugs in WATCHLIST.values())
CIRCUIT_BREAKER_TIMEOUT: float = max(20.0, (_total_slugs / _SEM_SIZE) * 4.0 + 10.0)

# NOTE — Why many Indian companies are missing from this list:
# TCS, Wipro, Infosys, HCL, Cognizant, Capgemini → use Workday / their own portals
# Mastercard, Visa, Adobe, Cisco India → use parent-company Workday (not public ATS)
# Flipkart, Swiggy, Zomato, Ola, Razorpay → use their own portals or SmartRecruiters
# Freshworks, Chargebee → on Greenhouse but slugs are 404 (likely on a sub-domain ATS)
# MakeMyTrip, PolicyBazaar → internal portals
# Persistent, Zensar, KPIT → Workday / internal
# To add a company: go to their careers page, check the URL — if it's boards.greenhouse.io/{slug},
# api.lever.co/v0/postings/{slug}, or api.ashbyhq.com/posting-api/job-board/{slug}, add it here.


# ── Date parsers ───────────────────────────────────────────────────────────────

def _from_ms(ms: int | None) -> datetime | None:
    if not ms:
        return None
    try:
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    except Exception:
        return None


def _from_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


# ── Greenhouse ─────────────────────────────────────────────────────────────────

def _normalise_greenhouse(raw: dict[str, Any], slug: str) -> dict[str, Any]:
    location = (raw.get("location") or {}).get("name") or ""
    return {
        "source": "greenhouse",
        "external_id": f"{slug}_{raw['id']}",
        "title": raw.get("title", ""),
        "company": slug.replace("-", " ").title(),
        "location": location,
        "description": "",
        "apply_url": raw.get("absolute_url", ""),
        "posted_at": _from_iso(raw.get("updated_at")),
        "employment_type": None,
        "is_remote": "remote" in location.lower(),
        "salary_min": None,
        "salary_max": None,
        "salary_currency": None,
        "tags": [],
        "skills": [],
        "raw_data": raw,
    }


async def _fetch_greenhouse(slug: str) -> list[dict[str, Any]]:
    cache_key = f"gh:{slug}"
    cached = _CACHE.get(cache_key)
    if cached and (time.time() - cached[0]) < _CACHE_TTL:
        return cached[1]
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    async with _SEM:
        try:
            async with httpx.AsyncClient(timeout=12) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            log.debug("ats.greenhouse_failed", slug=slug, error=str(exc))
            return []
    jobs = [_normalise_greenhouse(j, slug) for j in (data.get("jobs") or []) if j.get("absolute_url")]
    _CACHE[cache_key] = (time.time(), jobs)
    return jobs


# ── Lever ──────────────────────────────────────────────────────────────────────

def _normalise_lever(raw: dict[str, Any], slug: str) -> dict[str, Any]:
    cats = raw.get("categories") or {}
    location = cats.get("location") or cats.get("allLocations") or ""
    if isinstance(location, list):
        location = ", ".join(location)
    return {
        "source": "lever",
        "external_id": f"{slug}_{raw.get('id', '')}",
        "title": raw.get("text", ""),
        "company": slug.replace("-", " ").title(),
        "location": location,
        "description": (raw.get("descriptionPlain") or "")[:2000],
        "apply_url": raw.get("hostedUrl", ""),
        "posted_at": _from_ms(raw.get("createdAt")),
        "employment_type": raw.get("commitment"),
        "is_remote": "remote" in (location or "").lower(),
        "salary_min": None,
        "salary_max": None,
        "salary_currency": None,
        "tags": [],
        "skills": [],
        "raw_data": raw,
    }


async def _fetch_lever(slug: str) -> list[dict[str, Any]]:
    cache_key = f"lv:{slug}"
    cached = _CACHE.get(cache_key)
    if cached and (time.time() - cached[0]) < _CACHE_TTL:
        return cached[1]
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    async with _SEM:
        try:
            async with httpx.AsyncClient(timeout=12) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            log.debug("ats.lever_failed", slug=slug, error=str(exc))
            return []
    jobs = [_normalise_lever(j, slug) for j in (data if isinstance(data, list) else []) if j.get("hostedUrl")]
    _CACHE[cache_key] = (time.time(), jobs)
    return jobs


# ── Ashby ──────────────────────────────────────────────────────────────────────

def _normalise_ashby(raw: dict[str, Any], slug: str) -> dict[str, Any]:
    location = raw.get("jobLocation") or raw.get("locationName") or ""
    return {
        "source": "ashby",
        "external_id": f"{slug}_{raw.get('id', '')}",
        "title": raw.get("title", ""),
        "company": slug.replace("-", " ").title(),
        "location": location,
        "description": (raw.get("descriptionPlain") or "")[:2000],
        "apply_url": raw.get("externalLink") or raw.get("jobUrl") or "",
        "posted_at": _from_iso(raw.get("publishedDate")),
        "employment_type": raw.get("employmentType"),
        "is_remote": "remote" in (location or "").lower(),
        "salary_min": None,
        "salary_max": None,
        "salary_currency": None,
        "tags": [],
        "skills": [],
        "raw_data": raw,
    }


async def _fetch_ashby(slug: str) -> list[dict[str, Any]]:
    cache_key = f"ab:{slug}"
    cached = _CACHE.get(cache_key)
    if cached and (time.time() - cached[0]) < _CACHE_TTL:
        return cached[1]
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    async with _SEM:
        try:
            async with httpx.AsyncClient(timeout=12) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            log.debug("ats.ashby_failed", slug=slug, error=str(exc))
            return []
    jobs = [_normalise_ashby(j, slug) for j in (data.get("jobPostings") or []) if j.get("title")]
    _CACHE[cache_key] = (time.time(), jobs)
    return jobs


# ── Public search entry point ──────────────────────────────────────────────────

async def search(query: str) -> list[dict[str, Any]]:
    """Crawl all watchlist ATS boards and filter results by query keywords."""
    keywords = {w.lower() for w in query.split() if len(w) > 2}

    tasks: list[Any] = []
    for slug in WATCHLIST.get("greenhouse", []):
        tasks.append(_fetch_greenhouse(slug))
    for slug in WATCHLIST.get("lever", []):
        tasks.append(_fetch_lever(slug))
    for slug in WATCHLIST.get("ashby", []):
        tasks.append(_fetch_ashby(slug))

    batches = await asyncio.gather(*tasks, return_exceptions=True)

    results: list[dict[str, Any]] = []
    for batch in batches:
        if not isinstance(batch, list):
            continue
        for job in batch:
            title_lower = (job.get("title") or "").lower()
            if any(kw in title_lower for kw in keywords):
                results.append(job)

    log.info("ats.search_done", query=query, total=len(results))
    return results
