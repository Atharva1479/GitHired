"""Integration tests for the dashboard router.

These tests verify that the repository-backed dashboard endpoints return
correct shapes and handle empty state gracefully.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_stats_returns_expected_shape() -> None:
    """GET /api/dashboard/stats returns the expected nested structure."""
    with TestClient(app) as client:
        r = client.get("/api/dashboard/stats")
    assert r.status_code == 200
    data = r.json()
    assert "applications" in data
    assert "referrals" in data
    assert "nudges" in data

    apps = data["applications"]
    assert all(k in apps for k in ("total", "applied", "in_progress", "offers", "response_rate"))
    assert all(isinstance(apps[k], int) for k in ("total", "applied", "in_progress", "offers"))
    assert 0 <= apps["response_rate"] <= 100

    refs = data["referrals"]
    assert all(k in refs for k in ("total", "in_progress", "referred", "conversion_rate"))

    nudges = data["nudges"]
    assert all(k in nudges for k in ("today", "overdue"))


def test_stats_fresh_user_zeros() -> None:
    """A user with no applications has zero totals (not errors)."""
    with TestClient(app) as client:
        r = client.get("/api/dashboard/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["applications"]["total"] == 0
    assert data["applications"]["response_rate"] == 0


def test_activity_returns_list() -> None:
    """GET /api/dashboard/activity returns a list (possibly empty)."""
    with TestClient(app) as client:
        r = client.get("/api/dashboard/activity")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_activity_limit_capped() -> None:
    """Requesting limit > 50 returns 422."""
    with TestClient(app) as client:
        r = client.get("/api/dashboard/activity", params={"limit": 51})
    assert r.status_code == 422


def test_activity_limit_minimum() -> None:
    """Requesting limit=0 returns 422."""
    with TestClient(app) as client:
        r = client.get("/api/dashboard/activity", params={"limit": 0})
    assert r.status_code == 422
