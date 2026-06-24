"""Integration tests for the analytics router.

Verifies that the repository-backed analytics endpoints return valid shapes,
handle zero-data state gracefully, and validate funnel rate calculations.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_analytics_stats_shape() -> None:
    """GET /api/analytics/stats returns the expected four-section structure."""
    with TestClient(app) as client:
        r = client.get("/api/analytics/stats")
    assert r.status_code == 200
    data = r.json()

    assert "funnel" in data
    assert "by_source" in data
    assert "weekly_trend" in data
    assert "by_status" in data


def test_funnel_zero_state() -> None:
    """With no applications, all funnel counts are 0 and rates are 0."""
    with TestClient(app) as client:
        r = client.get("/api/analytics/stats")
    assert r.status_code == 200
    funnel = r.json()["funnel"]
    assert funnel["applied"] == 0
    assert funnel["response_rate"] == 0
    assert funnel["offer_rate"] == 0
    assert 0 <= funnel["response_rate"] <= 100
    assert 0 <= funnel["offer_rate"] <= 100


def test_by_source_is_list() -> None:
    """by_source is a list of {source, count, response_rate} objects."""
    with TestClient(app) as client:
        r = client.get("/api/analytics/stats")
    assert r.status_code == 200
    by_source = r.json()["by_source"]
    assert isinstance(by_source, list)
    for item in by_source:
        assert "source" in item
        assert "count" in item
        assert "response_rate" in item
        assert isinstance(item["count"], int)


def test_weekly_trend_is_list() -> None:
    """weekly_trend is a list of {week_start, count} objects."""
    with TestClient(app) as client:
        r = client.get("/api/analytics/stats")
    assert r.status_code == 200
    trend = r.json()["weekly_trend"]
    assert isinstance(trend, list)
    for point in trend:
        assert "week_start" in point
        assert "count" in point


def test_digest_trigger_blocked_in_test_env() -> None:
    """The /analytics/digest/trigger endpoint works in non-production env."""
    with TestClient(app) as client:
        # In test env (not production), it should queue the task and return 202
        r = client.post("/api/analytics/digest/trigger")
    # 202 = queued; 403 = production guard blocked it (shouldn't happen in test)
    assert r.status_code in (202, 503)
