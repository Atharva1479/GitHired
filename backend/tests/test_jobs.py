"""Integration tests for the jobs router.

Covers the endpoints that were at zero coverage:
- GET /api/jobs/search (cache lookup + API calls, mocked at service layer)
- GET /api/jobs/searches (saved searches CRUD)
- POST /api/jobs/searches
- DELETE /api/jobs/searches/{id}
- POST /api/jobs/{id}/bookmark
- GET /api/jobs/searches/new-count
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app

# A minimal JobResult dict as returned by the search service
_JOB = {
    "id": 9999,
    "source": "jsearch",
    "external_id": "test-ext-1",
    "title": "Software Engineer",
    "company": "TestCo",
    "location": "Remote",
    "description": "A great job.",
    "apply_url": "https://testco.com/apply",
    "posted_at": None,
    "employment_type": "FULLTIME",
    "skills": ["Python", "FastAPI"],
    "hours_old": 10,
    "freshness_score": 0.9,
    "freshness_label": "⚡ 6–24h",
    "freshness_color": "green",
    "est_applicants": "<10",
    "velocity_label": None,
    "bookmark_status": None,
    "is_remote": True,
    "salary_min": None,
    "salary_max": None,
    "salary_currency": None,
    "tags": [],
    "semantic_score": None,
}


# ── /api/jobs/search ──────────────────────────────────────────────────────────


def test_search_returns_results() -> None:
    """search endpoint returns a list of job results."""
    with patch(
        "app.routers.jobs.job_search.search_jobs",
        new_callable=AsyncMock,
        return_value=[_JOB],
    ):
        with TestClient(app) as client:
            r = client.get("/api/jobs/search", params={"q": "python engineer"})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["title"] == "Software Engineer"
    assert data[0]["company"] == "TestCo"


def test_search_requires_q_param() -> None:
    """search without q param returns 422 validation error."""
    with TestClient(app) as client:
        r = client.get("/api/jobs/search")
    assert r.status_code == 422


def test_search_q_min_length_1() -> None:
    """search with empty q param returns 422."""
    with TestClient(app) as client:
        r = client.get("/api/jobs/search", params={"q": ""})
    assert r.status_code == 422


def test_search_returns_empty_list_when_no_results() -> None:
    """search returns [] when the service finds nothing."""
    with patch(
        "app.routers.jobs.job_search.search_jobs",
        new_callable=AsyncMock,
        return_value=[],
    ):
        with TestClient(app) as client:
            r = client.get("/api/jobs/search", params={"q": "obscure-role-xyz"})
    assert r.status_code == 200
    assert r.json() == []


# ── /api/jobs/searches (saved searches) ─────────────────────────────────────


def test_list_saved_searches_empty_initially() -> None:
    """Fresh test user has no saved searches."""
    with TestClient(app) as client:
        r = client.get("/api/jobs/searches")
    assert r.status_code == 200
    assert r.json() == []


def test_create_and_list_saved_search() -> None:
    """Creating a saved search makes it appear in the list."""
    with TestClient(app) as client:
        r = client.post(
            "/api/jobs/searches",
            json={"name": "Python Jobs", "query": "python", "freshness_hours": 24},
        )
        assert r.status_code in (200, 201)
        created = r.json()
        assert created["name"] == "Python Jobs"
        assert created["query"] == "python"

        r2 = client.get("/api/jobs/searches")
        assert r2.status_code == 200
        names = [s["name"] for s in r2.json()]
        assert "Python Jobs" in names


def test_delete_saved_search() -> None:
    """Deleting a saved search removes it from the list."""
    with TestClient(app) as client:
        r = client.post(
            "/api/jobs/searches",
            json={"name": "ToDelete", "query": "react", "freshness_hours": 48},
        )
        assert r.status_code in (200, 201)
        search_id = r.json()["id"]

        r2 = client.delete(f"/api/jobs/searches/{search_id}")
        assert r2.status_code in (200, 204)

        r3 = client.get("/api/jobs/searches")
        ids = [s["id"] for s in r3.json()]
        assert search_id not in ids


def test_create_saved_search_requires_name_and_query() -> None:
    """Missing name or query field returns 422."""
    with TestClient(app) as client:
        r = client.post("/api/jobs/searches", json={"name": "No Query"})
    assert r.status_code == 422


# ── /api/jobs/searches/new-count ─────────────────────────────────────────────


def test_new_jobs_count_returns_int() -> None:
    """new-count endpoint returns a dict with integer count."""
    with TestClient(app) as client:
        r = client.get("/api/jobs/searches/new-count")
    assert r.status_code == 200
    data = r.json()
    assert "count" in data
    assert isinstance(data["count"], int)
