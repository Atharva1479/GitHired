"""SerpAPI Google Jobs client.

Searches Google Jobs via SerpAPI — covers LinkedIn India, Naukri, Indeed India,
Glassdoor, and every board Google indexes, with near-real-time freshness.

Free tier: 100 searches/month. Register at https://serpapi.com/
Set env var SERPAPI_API_KEY before use. Returns [] silently if key is missing.

API reference: https://serpapi.com/google-jobs-api
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import structlog

from app.config import settings

log = structlog.get_logger("serpapi_client")

_BASE = "https://serpapi.com/search"

# chips value for last-3-days filter (Google Jobs internal filter string)
_CHIPS_3DAYS = "date_posted:3days"


def _parse_relative_age(text: str | None) -> datetime | None:
    """Convert SerpAPI relative strings like '3 days ago' to a UTC datetime."""
    if not text:
        return None
    text = text.lower().strip()
    now = datetime.now(tz=timezone.utc)
    patterns = [
        (r"(\d+)\s+hour", timedelta(hours=1)),
        (r"(\d+)\s+day", timedelta(days=1)),
        (r"(\d+)\s+week", timedelta(weeks=1)),
        (r"(\d+)\s+month", timedelta(days=30)),
    ]
    for pattern, unit in patterns:
        m = re.search(pattern, text)
        if m:
            return now - unit * int(m.group(1))
    if "just posted" in text or "today" in text:
        return now
    return None


def _extract_skills(job: dict[str, Any]) -> list[str]:
    """Pull short skill tags from Qualifications / Requirements highlights."""
    skills: list[str] = []
    for section in job.get("job_highlights", []):
        if section.get("title", "").lower() in ("qualifications", "requirements"):
            for item in section.get("items", [])[:6]:
                if len(item) < 40:
                    skills.append(item.strip())
    return skills[:8]


def _normalise(raw: dict[str, Any]) -> dict[str, Any]:
    ext = raw.get("detected_extensions", {})
    posted_at = _parse_relative_age(ext.get("posted_at"))
    salary_raw = ext.get("salary", "")

    # Prefer the first direct apply link; fall back to via-board link
    apply_links = raw.get("apply_options", [])
    apply_url = apply_links[0].get("link", "") if apply_links else ""

    # `via` = "via LinkedIn", "via Naukri.com" — strip the "via " prefix
    via = raw.get("via", "")
    source_board = re.sub(r"^via\s+", "", via).lower().replace(" ", "_") if via else "google_jobs"

    return {
        "source": f"serpapi:{source_board}",
        "external_id": raw.get("job_id", ""),          # SerpAPI provides a stable job_id
        "title": raw.get("title", ""),
        "company": raw.get("company_name", ""),
        "location": raw.get("location", ""),
        "description": raw.get("description", ""),
        "apply_url": apply_url,
        "posted_at": posted_at,
        "employment_type": ext.get("schedule_type", ""),
        "skills": _extract_skills(raw),
        "is_remote": (
            "remote" in raw.get("title", "").lower()
            or "remote" in raw.get("location", "").lower()
            or ext.get("work_from_home", False)
        ),
        "salary_min": None,
        "salary_max": None,
        "salary_currency": None,
        "tags": [salary_raw] if salary_raw else [],
        "raw_data": raw,
    }


async def search(
    query: str,
    location: str | None = None,
    fetch_pages: int = 2,
) -> list[dict[str, Any]]:
    """Search Google Jobs via SerpAPI, fetching up to fetch_pages × 10 results.

    Returns [] if SERPAPI_API_KEY is not set or on any API error.
    Uses next_page_token for pagination (SerpAPI Google Jobs returns max 10 per page).
    Passes gl=in + hl=en when location contains India to improve relevance.
    """
    if not settings.serpapi_api_key:
        return []

    api_key = settings.serpapi_api_key.get_secret_value()
    location_lower = (location or "").lower()
    is_india = any(w in location_lower for w in ("india", "bangalore", "mumbai", "delhi",
                                                   "hyderabad", "pune", "chennai", "kolkata",
                                                   "bengaluru", "noida", "gurgaon", "gurugram"))

    params: dict[str, Any] = {
        "engine": "google_jobs",
        "q": f"{query} {location}".strip() if location else query,
        "api_key": api_key,
        "chips": _CHIPS_3DAYS,
        "hl": "en",
    }
    if location:
        params["location"] = location
    if is_india:
        params["gl"] = "in"

    all_results: list[dict[str, Any]] = []
    next_page_token: str | None = None

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            for page in range(fetch_pages):
                if page > 0:
                    if not next_page_token:
                        break
                    params["next_page_token"] = next_page_token
                    params.pop("chips", None)   # chips only valid on first page

                resp = await client.get(_BASE, params=params)
                resp.raise_for_status()
                data = resp.json()

                jobs = data.get("jobs_results") or []
                all_results.extend(_normalise(j) for j in jobs)

                # SerpAPI pagination token for the next page
                next_page_token = (
                    data.get("serpapi_pagination", {}).get("next_page_token")
                )

                if not jobs:
                    break

        log.info("serpapi.fetched", query=query, location=location, count=len(all_results))
        return all_results

    except Exception as exc:
        log.warning("serpapi.request_failed", error=str(exc))
        return all_results  # return whatever we got before the error
