"""Jobicy remote jobs API client (free, no auth).

Returns salary data (annualSalaryMin/Max) when available.
Docs: https://jobicy.com/api/v2/remote-jobs
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx
import structlog

log = structlog.get_logger("jobicy_client")

_BASE = "https://jobicy.com/api/v2/remote-jobs"


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _normalise(raw: dict[str, Any]) -> dict[str, Any]:
    slug = raw.get("jobSlug", "")
    apply_url = f"https://jobicy.com/jobs/{slug}" if slug else ""
    return {
        "source": "jobicy",
        "external_id": str(raw.get("id", slug)),
        "title": raw.get("jobTitle", ""),
        "company": raw.get("companyName", ""),
        "location": raw.get("jobGeo") or "Remote",
        "description": (raw.get("jobExcerpt") or "")[:2000],
        "apply_url": apply_url,
        "posted_at": _parse_dt(raw.get("pubDate")),
        "employment_type": None,
        "is_remote": True,
        "salary_min": raw.get("annualSalaryMin"),
        "salary_max": raw.get("annualSalaryMax"),
        "salary_currency": raw.get("salaryCurrency"),
        "tags": [],
        "skills": [],
        "raw_data": raw,
    }


async def search(query: str) -> list[dict[str, Any]]:
    """Search Jobicy by tag (first word of query) and return normalised job dicts."""
    tag = query.split()[0].lower() if query.strip() else query
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(_BASE, params={"count": 50, "tag": tag})
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        log.warning("jobicy.request_failed", error=str(exc))
        return []

    jobs = data.get("jobs") or []
    log.info("jobicy.fetched", count=len(jobs), query=query)
    return [_normalise(j) for j in jobs if j.get("jobSlug")]
