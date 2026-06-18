"""RemoteOK API client (free, no auth).

Returns salary data when available. First array element is metadata — skip it.
Docs: https://remoteok.com/api
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
import structlog

log = structlog.get_logger("remoteok_client")

_BASE = "https://remoteok.com/api"


def _parse_ts(value: int | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromtimestamp(value, tz=timezone.utc)
    except Exception:
        return None


def _normalise(raw: dict[str, Any]) -> dict[str, Any]:
    tags: list[str] = raw.get("tags") or []
    return {
        "source": "remoteok",
        "external_id": str(raw.get("id", raw.get("slug", ""))),
        "title": raw.get("position", ""),
        "company": raw.get("company", ""),
        "location": "Remote",
        "description": (raw.get("description") or "")[:2000],
        "apply_url": raw.get("url") or raw.get("apply_url", ""),
        "posted_at": _parse_ts(raw.get("date")),
        "employment_type": "fulltime",
        "is_remote": True,
        "salary_min": raw.get("salary_min"),
        "salary_max": raw.get("salary_max"),
        "salary_currency": "USD" if (raw.get("salary_min") or raw.get("salary_max")) else None,
        "tags": tags[:20],
        "skills": tags[:20],
        "raw_data": raw,
    }


async def search(query: str) -> list[dict[str, Any]]:
    """Search RemoteOK by tag and return normalised job dicts."""
    tag = query.split()[0].lower() if query.strip() else query
    try:
        async with httpx.AsyncClient(timeout=15, headers={"User-Agent": "JobTracker/1.0"}) as client:
            resp = await client.get(_BASE, params={"tag": tag})
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        log.warning("remoteok.request_failed", error=str(exc))
        return []

    # First element is metadata dict with "legal" key — skip non-job entries
    jobs = [j for j in data if isinstance(j, dict) and j.get("id") and j.get("position")]
    log.info("remoteok.fetched", count=len(jobs), query=query)
    return [_normalise(j) for j in jobs if j.get("url") or j.get("apply_url")]
