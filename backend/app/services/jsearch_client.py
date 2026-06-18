"""JSearch RapidAPI client.

Aggregates LinkedIn / Indeed / Naukri / Glassdoor job listings.
API reference: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch

Each result is normalised to a common dict so job_search.py can merge
results from all sources without caring which API produced them.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx
import structlog

from app.config import settings

log = structlog.get_logger("jsearch_client")

_BASE = "https://jsearch.p.rapidapi.com"
_HEADERS = {
    "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
}

_EXP_MAP = {
    "entry":  "under_3_years_experience",
    "senior": "more_than_3_years_experience",
    # "mid" has no JSearch equivalent — omit to avoid 400
}


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _normalise(raw: dict[str, Any]) -> dict[str, Any]:
    """Convert a JSearch job object to our common schema."""
    skills: list[str] = raw.get("job_required_skills") or []
    if not skills:
        for qual in (raw.get("job_highlights") or {}).get("Qualifications") or []:
            skills.append(qual[:80])
    salary_min = raw.get("job_min_salary") or raw.get("job_salary_standardized_min")
    salary_max = raw.get("job_max_salary") or raw.get("job_salary_standardized_max")
    salary_cur = raw.get("job_salary_currency") or raw.get("job_salary_standardized_currency")
    return {
        "source": "jsearch",
        "external_id": raw.get("job_id", ""),
        "title": raw.get("job_title", ""),
        "company": raw.get("employer_name", ""),
        "location": ", ".join(filter(None, [raw.get("job_city"), raw.get("job_country")])),
        "description": (raw.get("job_description") or "")[:2000],
        "apply_url": raw.get("job_apply_link") or raw.get("job_google_link", ""),
        "posted_at": _parse_dt(raw.get("job_posted_at_datetime_utc")),
        "employment_type": raw.get("job_employment_type"),
        "is_remote": bool(raw.get("job_is_remote")),
        "salary_min": int(salary_min) if salary_min else None,
        "salary_max": int(salary_max) if salary_max else None,
        "salary_currency": salary_cur,
        "tags": [],
        "skills": skills[:20],
        "raw_data": raw,
    }


async def search(
    query: str,
    location: str | None = None,
    remote_only: bool = False,
    experience: str | None = None,
    date_posted: str = "today",
    page: int = 1,
    num_pages: int = 1,
) -> list[dict[str, Any]]:
    """Search JSearch and return a list of normalised job dicts.

    Returns [] if JSEARCH_API_KEY is not configured.
    """
    if not settings.jsearch_api_key:
        log.debug("jsearch.skipped", reason="no api key")
        return []

    params: dict[str, Any] = {
        "query": f"{query} {location or ''}".strip(),
        "page": page,
        "num_pages": num_pages,
        "date_posted": date_posted,
        "remote_jobs_only": "true" if remote_only else "false",
    }
    if experience and experience in _EXP_MAP:
        params["job_requirements"] = _EXP_MAP[experience]

    headers = {**_HEADERS, "X-RapidAPI-Key": settings.jsearch_api_key}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{_BASE}/search", params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        log.warning("jsearch.request_failed", error=str(exc))
        return []

    jobs = data.get("data") or []
    log.info("jsearch.fetched", count=len(jobs), query=query)
    return [_normalise(j) for j in jobs if j.get("job_apply_link") or j.get("job_google_link")]
