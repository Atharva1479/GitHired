"""WeWorkRemotely RSS feed client (free, no auth).

Fetches 3 category feeds (programming, devops, data), caches raw XML for 2h,
then keyword-filters job titles against the search query.
"""
from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx
import structlog

log = structlog.get_logger("weworkremotely_client")

_FEEDS = [
    "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
]

# Simple in-memory cache: {url: (fetched_at_unix, xml_text)}
_cache: dict[str, tuple[float, str]] = {}
_CACHE_TTL = 7200  # 2 hours


def _parse_rss_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _normalise(title_raw: str, link: str, pub_date: str | None) -> dict[str, Any]:
    # WWR title format: "Company Name: Job Title"
    if ": " in title_raw:
        company, _, role = title_raw.partition(": ")
    else:
        company, role = "Unknown", title_raw
    return {
        "source": "weworkremotely",
        "external_id": link,
        "title": role.strip(),
        "company": company.strip(),
        "location": "Remote",
        "description": "",
        "apply_url": link,
        "posted_at": _parse_rss_dt(pub_date),
        "employment_type": "fulltime",
        "is_remote": True,
        "salary_min": None,
        "salary_max": None,
        "salary_currency": None,
        "tags": [],
        "skills": [],
        "raw_data": {"title": title_raw, "link": link},
    }


async def _fetch_feed(url: str) -> str:
    now = time.time()
    cached = _cache.get(url)
    if cached and (now - cached[0]) < _CACHE_TTL:
        return cached[1]
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            text = resp.text
            _cache[url] = (now, text)
            return text
    except Exception as exc:
        log.warning("weworkremotely.feed_failed", url=url, error=str(exc))
        return cached[1] if cached else ""


async def search(query: str) -> list[dict[str, Any]]:
    """Fetch all 3 WWR feeds, filter by query keywords, return normalised dicts."""
    keywords = {w.lower() for w in query.split() if len(w) > 2}
    results: list[dict[str, Any]] = []

    for feed_url in _FEEDS:
        xml_text = await _fetch_feed(feed_url)
        if not xml_text:
            continue
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            log.warning("weworkremotely.parse_failed", url=feed_url, error=str(exc))
            continue

        for item in root.findall(".//item"):
            title_raw = item.findtext("title") or ""
            link = item.findtext("link") or ""
            pub_date = item.findtext("pubDate")

            # Only keep items whose title contains at least one query keyword
            title_lower = title_raw.lower()
            if not any(kw in title_lower for kw in keywords):
                continue

            if link:
                results.append(_normalise(title_raw, link, pub_date))

    log.info("weworkremotely.fetched", count=len(results), query=query)
    return results
