# backend/app/services/jooble_client.py
"""Jooble job aggregator API client.

Aggregates from Naukri, LinkedIn India, Monster India, TimesJobs, Shine, Foundit.
Free tier: 500 requests/day. Register at https://jooble.org/api/about

Set env var JOOBLE_API_KEY before use. If the key is missing, search() returns [].
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import httpx
import structlog

from app.config import settings

log = structlog.get_logger("jooble_client")

_BASE = "https://jooble.org/api"


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        # Jooble returns "2026-06-19T00:00:00.0000000"
        return datetime.fromisoformat(value[:19]).replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _extract_external_id(link: str) -> str:
    """Extract numeric job ID from Jooble redirect URL like https://jooble.org/desc/-123456."""
    match = re.search(r"/desc/(-?\d+)", link)
    return match.group(1).lstrip("-") if match else link[-20:]


def _normalise(raw: dict[str, Any]) -> dict[str, Any]:
    title = raw.get("title", "")
    link = raw.get("link", "")
    # Jooble sometimes includes HTML in snippet — strip tags
    snippet = re.sub(r"<[^>]+>", " ", raw.get("snippet", "")).strip()
    return {
        "source": f"jooble:{raw.get('source', 'unknown')}",
        "external_id": _extract_external_id(link),
        "title": title,
        "company": raw.get("company", ""),
        "location": raw.get("location", ""),
        "description": snippet,
        "apply_url": link,
        "posted_at": _parse_dt(raw.get("updated")),
        "employment_type": raw.get("type", ""),
        "skills": [],
        "is_remote": "remote" in title.lower() or "remote" in (raw.get("location") or "").lower(),
        "salary_min": None,
        "salary_max": None,
        "salary_currency": None,
        "tags": [],
        "raw_data": raw,
    }


async def search(
    query: str,
    location: str | None = None,
    page: int = 1,
    results_per_page: int = 20,
) -> list[dict[str, Any]]:
    """Search Jooble for jobs matching query + location.

    Returns [] if JOOBLE_API_KEY is not set or on any API error.
    """
    if not settings.jooble_api_key:
        return []
    api_key = settings.jooble_api_key.get_secret_value()
    payload = {
        "keywords": query,
        "location": location or "",
        "page": page,
        "resultsOnPage": results_per_page,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{_BASE}/{api_key}", json=payload)
            resp.raise_for_status()
            data = resp.json()
        jobs = data.get("jobs") or []
        results = [_normalise(j) for j in jobs]
        log.info("jooble.fetched", query=query, location=location, count=len(results))
        return results
    except Exception as exc:
        log.warning("jooble.request_failed", error=str(exc))
        return []
