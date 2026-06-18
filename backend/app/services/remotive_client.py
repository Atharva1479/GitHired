"""Remotive remote jobs API client (free, no auth).

Only returns remote tech jobs. Good signal-to-noise for software roles.
Docs: https://remotive.com/api/remote-jobs
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx
import structlog

log = structlog.get_logger("remotive_client")

_BASE = "https://remotive.com/api/remote-jobs"


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _normalise(raw: dict[str, Any]) -> dict[str, Any]:
    tags: list[str] = raw.get("tags") or []
    return {
        "source": "remotive",
        "external_id": str(raw.get("id", "")),
        "title": raw.get("title", ""),
        "company": raw.get("company_name", ""),
        "location": raw.get("candidate_required_location") or "Remote",
        "description": (raw.get("description") or "")[:2000],
        "apply_url": raw.get("url", ""),
        "posted_at": _parse_dt(raw.get("publication_date")),
        "employment_type": raw.get("job_type"),
        "is_remote": True,
        "salary_min": None,
        "salary_max": None,
        "salary_currency": None,
        "tags": tags[:20],
        "skills": tags[:20],
        "raw_data": raw,
    }


async def search(query: str) -> list[dict[str, Any]]:
    """Search Remotive and return normalised job dicts."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(_BASE, params={"search": query, "limit": 50})
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        log.warning("remotive.request_failed", error=str(exc))
        return []

    jobs = data.get("jobs") or []
    log.info("remotive.fetched", count=len(jobs), query=query)
    return [_normalise(j) for j in jobs if j.get("url")]
