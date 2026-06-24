"""Adzuna job search API client (free tier — 250 req/day).

Country support: in (India), gb, us, au, ca, de, fr, etc.
Docs: https://developer.adzuna.com/
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx
import structlog

from app.config import settings

log = structlog.get_logger("adzuna_client")

_BASE = "https://api.adzuna.com/v1/api/jobs"
_COUNTRY = "in"  # India


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _normalise(raw: dict[str, Any]) -> dict[str, Any]:
    title = raw.get("title", "")
    location = (raw.get("location") or {}).get("display_name") or ""
    salary_min = raw.get("salary_min")
    salary_max = raw.get("salary_max")
    return {
        "source": "adzuna",
        "external_id": str(raw.get("id", "")),
        "title": title,
        "company": (raw.get("company") or {}).get("display_name", "Unknown"),
        "location": location,
        "description": (raw.get("description") or "")[:2000],
        "apply_url": raw.get("redirect_url", ""),
        "posted_at": _parse_dt(raw.get("created")),
        "employment_type": raw.get("contract_type"),
        "is_remote": "remote" in title.lower() or "remote" in location.lower(),
        "salary_min": int(salary_min) if salary_min else None,
        "salary_max": int(salary_max) if salary_max else None,
        "salary_currency": "INR",
        "tags": [],
        "skills": [],
        "raw_data": raw,
    }


async def search(
    query: str,
    location: str | None = None,
    max_days_old: int = 1,
    page: int = 1,
    results_per_page: int = 20,
) -> list[dict[str, Any]]:
    """Search Adzuna India and return normalised job dicts.

    Returns [] if ADZUNA_APP_ID / ADZUNA_API_KEY are not configured.
    """
    if not (settings.adzuna_app_id and settings.adzuna_api_key):
        log.debug("adzuna.skipped", reason="no credentials")
        return []

    params: dict[str, Any] = {
        "app_id": settings.adzuna_app_id,
        "app_key": settings.adzuna_api_key.get_secret_value(),
        "results_per_page": results_per_page,
        "what": query,
        "max_days_old": max_days_old,
        "content-type": "application/json",
    }
    if location:
        params["where"] = location

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            url = f"{_BASE}/{_COUNTRY}/search/{page}"
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        log.warning("adzuna.request_failed", error=str(exc))
        return []

    jobs = data.get("results") or []
    log.info("adzuna.fetched", count=len(jobs), query=query)
    return [_normalise(j) for j in jobs if j.get("redirect_url")]
