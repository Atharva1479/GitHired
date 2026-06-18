"""Unit tests for the job-search filter fixes (June 2026 patch).

Covers all 4 bugs:
  1. Arbeitnow: title-keyword filter — non-Java jobs must be excluded
  2. JSearch:   invalid job_requirements values fixed (ENTRY_LEVEL → under_3_years_experience)
  3. Remote-only post-filter removes non-remote jobs
  4. Location post-filter keeps remote + location-match, drops the rest
  5. Experience post-filter strips senior titles for entry / junior titles for senior

No DB, no network — pure unit tests.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.job_search import _apply_filters
from app.services.jsearch_client import _EXP_MAP


# ── Helpers ────────────────────────────────────────────────────────────────────

def _job(
    title: str = "Software Engineer",
    location: str = "India",
    is_remote: bool = False,
) -> dict:
    return {
        "title": title,
        "location": location,
        "is_remote": is_remote,
        "source": "test",
        "external_id": title.lower().replace(" ", "_"),
        "freshness_score": 55,
    }


# ── Fix 2: JSearch _EXP_MAP must use valid API values ─────────────────────────

class TestJSearchExpMap:
    def test_entry_maps_to_valid_jsearch_value(self):
        assert _EXP_MAP["entry"] == "under_3_years_experience"

    def test_senior_maps_to_valid_jsearch_value(self):
        assert _EXP_MAP["senior"] == "more_than_3_years_experience"

    def test_mid_absent_from_map(self):
        # "mid" has no valid JSearch equivalent — must be absent to avoid 400
        assert "mid" not in _EXP_MAP

    def test_old_invalid_values_removed(self):
        assert "ENTRY_LEVEL"  not in _EXP_MAP.values()
        assert "MID_LEVEL"    not in _EXP_MAP.values()
        assert "SENIOR_LEVEL" not in _EXP_MAP.values()


# ── Fix 3: remote_only post-filter ────────────────────────────────────────────

class TestRemoteOnlyFilter:
    def test_non_remote_job_excluded_when_flag_set(self):
        jobs = [
            _job("Java Dev",      is_remote=True),
            _job("Java Engineer", is_remote=False),
        ]
        result = _apply_filters(jobs, remote_only=True, location=None, experience=None)
        assert len(result) == 1
        assert result[0]["title"] == "Java Dev"

    def test_all_remote_jobs_pass(self):
        jobs = [_job(is_remote=True), _job("Backend Eng", is_remote=True)]
        result = _apply_filters(jobs, remote_only=True, location=None, experience=None)
        assert len(result) == 2

    def test_flag_false_keeps_both(self):
        jobs = [_job(is_remote=True), _job(is_remote=False)]
        result = _apply_filters(jobs, remote_only=False, location=None, experience=None)
        assert len(result) == 2

    def test_empty_input(self):
        result = _apply_filters([], remote_only=True, location=None, experience=None)
        assert result == []

    @pytest.mark.parametrize("count", [1, 5, 20])
    def test_all_filtered_when_none_remote(self, count):
        jobs = [_job(f"Job {i}", is_remote=False) for i in range(count)]
        result = _apply_filters(jobs, remote_only=True, location=None, experience=None)
        assert result == []


# ── Fix 4: location post-filter ───────────────────────────────────────────────

class TestLocationFilter:
    def test_non_remote_non_matching_location_excluded(self):
        jobs = [
            _job("Java Dev", location="Berlin, Germany",    is_remote=False),
            _job("Java Eng", location="Bangalore, India",   is_remote=False),
        ]
        result = _apply_filters(jobs, remote_only=False, location="India", experience=None)
        assert len(result) == 1
        assert result[0]["title"] == "Java Eng"

    def test_remote_job_kept_regardless_of_location(self):
        jobs = [
            _job("Remote Dev",  location="",               is_remote=True),
            _job("Berlin Dev",  location="Berlin, Germany", is_remote=False),
        ]
        result = _apply_filters(jobs, remote_only=False, location="India", experience=None)
        assert len(result) == 1
        assert result[0]["title"] == "Remote Dev"

    def test_location_check_is_case_insensitive(self):
        jobs = [_job("Dev", location="Mumbai, INDIA", is_remote=False)]
        result = _apply_filters(jobs, remote_only=False, location="india", experience=None)
        assert len(result) == 1

    def test_no_location_arg_keeps_all(self):
        jobs = [
            _job(location="Germany", is_remote=False),
            _job(location="India",   is_remote=False),
        ]
        result = _apply_filters(jobs, remote_only=False, location=None, experience=None)
        assert len(result) == 2

    def test_partial_location_match(self):
        # "Hyderabad, Telangana, India" should match "India"
        jobs = [_job("Dev", location="Hyderabad, Telangana, India", is_remote=False)]
        result = _apply_filters(jobs, remote_only=False, location="India", experience=None)
        assert len(result) == 1

    def test_empty_location_field_non_remote_excluded(self):
        jobs = [_job("Dev", location="", is_remote=False)]
        result = _apply_filters(jobs, remote_only=False, location="India", experience=None)
        assert result == []


# ── Fix 5: experience post-filter ─────────────────────────────────────────────

class TestExperienceFilter:
    # ── entry level ──

    def test_entry_excludes_senior_title(self):
        jobs = [
            _job("Senior Java Developer"),
            _job("Java Developer"),
        ]
        result = _apply_filters(jobs, remote_only=False, location=None, experience="entry")
        titles = [r["title"] for r in result]
        assert "Senior Java Developer" not in titles
        assert "Java Developer" in titles

    def test_entry_excludes_lead_title(self):
        jobs = [_job("Java Lead Engineer"), _job("Java Engineer")]
        result = _apply_filters(jobs, remote_only=False, location=None, experience="entry")
        titles = [r["title"] for r in result]
        assert "Java Lead Engineer" not in titles
        assert "Java Engineer" in titles

    def test_entry_excludes_principal_and_staff(self):
        jobs = [
            _job("Principal Engineer"),
            _job("Staff Software Engineer"),
            _job("Junior Software Engineer"),
        ]
        result = _apply_filters(jobs, remote_only=False, location=None, experience="entry")
        titles = [r["title"] for r in result]
        assert "Principal Engineer" not in titles
        assert "Staff Software Engineer" not in titles
        assert "Junior Software Engineer" in titles

    # ── senior level ──

    def test_senior_excludes_junior_title(self):
        jobs = [
            _job("Junior Java Developer"),
            _job("Java Developer"),
            _job("Senior Java Developer"),
        ]
        result = _apply_filters(jobs, remote_only=False, location=None, experience="senior")
        titles = [r["title"] for r in result]
        assert "Junior Java Developer" not in titles
        assert "Java Developer" in titles
        assert "Senior Java Developer" in titles

    def test_senior_excludes_fresher_trainee(self):
        jobs = [_job("Fresher Java Trainee"), _job("Java Developer")]
        result = _apply_filters(jobs, remote_only=False, location=None, experience="senior")
        titles = [r["title"] for r in result]
        assert "Fresher Java Trainee" not in titles
        assert "Java Developer" in titles

    # ── mid level ──

    def test_mid_applies_no_filter(self):
        # "mid" has no filter — all jobs should pass through
        jobs = [
            _job("Senior Java Developer"),
            _job("Junior Java Developer"),
            _job("Java Developer"),
        ]
        result = _apply_filters(jobs, remote_only=False, location=None, experience="mid")
        assert len(result) == 3

    # ── no filter ──

    def test_none_experience_applies_no_filter(self):
        jobs = [_job("Senior Dev"), _job("Junior Dev"), _job("Dev")]
        result = _apply_filters(jobs, remote_only=False, location=None, experience=None)
        assert len(result) == 3


# ── Fix 1: Arbeitnow title keyword filter ─────────────────────────────────────

@pytest.mark.asyncio
async def test_arbeitnow_keeps_only_title_keyword_matches():
    """Only jobs whose title contains a search keyword should be returned."""
    from app.services.arbeitnow_client import search

    api_payload = {
        "data": [
            {"title": "Java Developer",         "url": "https://a.co/1", "slug": "java-dev"},
            {"title": "Senior Java Engineer",   "url": "https://a.co/2", "slug": "java-eng"},
            {"title": "Go to Market Manager",   "url": "https://a.co/3", "slug": "gtm"},
            {"title": "Product Designer",       "url": "https://a.co/4", "slug": "designer"},
            {"title": "Flutter & Node.js Dev",  "url": "https://a.co/5", "slug": "flutter"},
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = lambda: None
    mock_resp.json.return_value = api_payload

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("app.services.arbeitnow_client.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        results = await search("Java Developer")

    titles = {r["title"] for r in results}
    assert "Java Developer"       in titles
    assert "Senior Java Engineer" in titles
    assert "Go to Market Manager" not in titles
    assert "Product Designer"     not in titles
    assert "Flutter & Node.js Dev" not in titles


@pytest.mark.asyncio
async def test_arbeitnow_returns_empty_on_no_title_match():
    from app.services.arbeitnow_client import search
    api_payload = {
        "data": [
            {"title": "Marketing Analyst", "url": "https://a.co/1", "slug": "mkt"},
            {"title": "HR Manager",        "url": "https://a.co/2", "slug": "hr"},
        ]
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = lambda: None
    mock_resp.json.return_value = api_payload

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("app.services.arbeitnow_client.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        results = await search("Java Developer")

    assert results == []


@pytest.mark.asyncio
async def test_arbeitnow_skips_jobs_without_url():
    from app.services.arbeitnow_client import search
    api_payload = {
        "data": [
            {"title": "Java Developer", "url": "",                    "slug": "no-url"},
            {"title": "Java Engineer",  "url": "https://a.co/valid", "slug": "has-url"},
        ]
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = lambda: None
    mock_resp.json.return_value = api_payload

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("app.services.arbeitnow_client.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        results = await search("Java Developer")

    assert len(results) == 1
    assert results[0]["title"] == "Java Engineer"
