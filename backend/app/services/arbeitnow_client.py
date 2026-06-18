"""Arbeitnow job board API client (free, no auth).

Aggregates listings sourced from Greenhouse, SmartRecruiters, and Join.com.
Docs: https://www.arbeitnow.com/api/job-board-api
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
import structlog

log = structlog.get_logger("arbeitnow_client")

_BASE = "https://www.arbeitnow.com/api/job-board-api"


def _parse_dt(value: str | int | None) -> datetime | None:
    if not value:
        return None
    if isinstance(value, int):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except Exception:
            return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _normalise(raw: dict[str, Any]) -> dict[str, Any]:
    tags: list[str] = raw.get("tags") or []
    return {
        "source": "arbeitnow",
        "external_id": raw.get("slug", ""),
        "title": raw.get("title", ""),
        "company": raw.get("company_name", ""),
        "location": raw.get("location", ""),
        "description": (raw.get("description") or "")[:2000],
        "apply_url": raw.get("url", ""),
        "posted_at": _parse_dt(raw.get("created_at")),
        "employment_type": (raw.get("job_types") or [""])[0] or None,
        "is_remote": bool(raw.get("remote")),
        "salary_min": None,
        "salary_max": None,
        "salary_currency": None,
        "tags": tags[:20],
        "skills": tags[:20],
        "raw_data": raw,
    }


async def search(query: str) -> list[dict[str, Any]]:
    """Search Arbeitnow and return normalised job dicts."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(_BASE, params={"search": query})
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        log.warning("arbeitnow.request_failed", error=str(exc))
        return []

    jobs = data.get("data") or []
    keywords = {w.lower() for w in query.split() if len(w) > 2}
    log.info("arbeitnow.fetched", count=len(jobs), query=query)
    return [
        _normalise(j) for j in jobs
        if j.get("url") and any(kw in (j.get("title") or "").lower() for kw in keywords)
    ]
