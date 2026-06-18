"""SmartRecruiters public postings client.

Uses the public API: GET /v1/companies/{slug}/postings
No auth required — only PUBLIC status postings are returned.

Results cached per-company for 6 hours.
"""
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

import httpx
import structlog

log = structlog.get_logger("smartrecruiters_client")

_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_CACHE_TTL = 21_600  # 6 hours
_SEM = asyncio.Semaphore(5)
_BASE = "https://api.smartrecruiters.com/v1/companies"

# ── Verified company slugs ─────────────────────────────────────────────────────
# Confirmed live 2026-06. Add new slugs only after verifying via the API.
_COMPANIES: list[tuple[str, str]] = [
    ("freshworks",  "Freshworks"),
    ("synechron",   "Synechron"),
]


def _parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def _normalise(item: dict[str, Any], display_name: str, slug: str) -> dict[str, Any]:
    loc = item.get("location") or {}
    city = loc.get("city") or ""
    country = loc.get("country") or ""
    location = ", ".join(p for p in (city, country) if p)
    job_id = item.get("id", "")
    return {
        "source": "smartrecruiters",
        "external_id": f"{slug}_{job_id}",
        "title": item.get("name", ""),
        "company": display_name,
        "location": location,
        "description": "",
        "apply_url": item.get("ref", "") or f"https://jobs.smartrecruiters.com/{slug}/{job_id}",
        "posted_at": _parse_dt(item.get("releasedDate")),
        "employment_type": (item.get("typeOfEmployment") or {}).get("label"),
        "is_remote": loc.get("remote", False),
        "salary_min": None,
        "salary_max": None,
        "salary_currency": None,
        "tags": [d.get("label", "") for d in (item.get("department") or []) if d.get("label")],
        "skills": [],
        "raw_data": item,
    }


async def _fetch_company(slug: str, display_name: str, query: str) -> list[dict[str, Any]]:
    cache_key = f"sr:{slug}"
    cached = _CACHE.get(cache_key)
    if cached and (time.time() - cached[0]) < _CACHE_TTL:
        raw = cached[1]
    else:
        async with _SEM:
            try:
                async with httpx.AsyncClient(timeout=12) as client:
                    resp = await client.get(
                        f"{_BASE}/{slug}/postings",
                        params={"status": "PUBLIC", "limit": 100},
                    )
                    if resp.status_code != 200:
                        log.debug("sr.non_200", company=slug, status=resp.status_code)
                        return []
                    raw = resp.json().get("content") or []
            except Exception as exc:
                log.debug("sr.fetch_error", company=slug, error=str(exc))
                return []
        _CACHE[cache_key] = (time.time(), raw)

    keywords = {w.lower() for w in query.split() if len(w) > 2}
    results = []
    for item in raw:
        title = (item.get("name") or "").lower()
        if any(kw in title for kw in keywords):
            results.append(_normalise(item, display_name, slug))
    return results


async def search(query: str) -> list[dict[str, Any]]:
    """Fetch matching jobs from all verified SmartRecruiters company boards."""
    batches = await asyncio.gather(
        *[_fetch_company(slug, name, query) for slug, name in _COMPANIES],
        return_exceptions=True,
    )
    results: list[dict[str, Any]] = []
    for batch in batches:
        if isinstance(batch, list):
            results.extend(batch)
    log.info("smartrecruiters.search_done", query=query, total=len(results))
    return results
