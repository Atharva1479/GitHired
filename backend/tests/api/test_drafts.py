from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _create_app(client: TestClient) -> int:
    body = {
        "company": "Stripe",
        "role": "Frontend Engineer",
        "source": "LinkedIn",
        "applied_date": "2026-05-01",
    }
    return client.post("/api/applications", json=body).json()["id"]


def _create_ref(client: TestClient) -> int:
    body = {
        "name": "Rohan",
        "company": "Stripe",
        "target_role": "Frontend Engineer",
        "connection_sent_date": "2026-05-01",
    }
    return client.post("/api/referrals", json=body).json()["id"]


def test_application_followup_uses_fallback_without_key(client: TestClient) -> None:
    app_id = _create_app(client)
    r = client.post(f"/api/drafts/application/{app_id}/followup", json={})
    assert r.status_code == 200
    body = r.json()
    assert body["draft_type"] == "followup_email"
    assert body["fallback"] is True
    assert "Stripe" in body["content"]
    assert body["cached"] is False


def test_second_call_returns_cached(client: TestClient) -> None:
    app_id = _create_app(client)
    first = client.post(f"/api/drafts/application/{app_id}/followup", json={}).json()
    second = client.post(f"/api/drafts/application/{app_id}/followup", json={}).json()
    assert second["id"] == first["id"]
    assert second["cached"] is True


def test_regenerate_forces_new_row(client: TestClient) -> None:
    app_id = _create_app(client)
    first = client.post(f"/api/drafts/application/{app_id}/followup", json={}).json()
    second = client.post(
        f"/api/drafts/application/{app_id}/followup",
        json={"regenerate": True},
    ).json()
    assert second["id"] != first["id"]
    assert second["cached"] is False


def test_referral_ask_fallback(client: TestClient) -> None:
    ref_id = _create_ref(client)
    r = client.post(f"/api/drafts/referral/{ref_id}/ask", json={})
    assert r.status_code == 200
    body = r.json()
    assert body["draft_type"] == "referral_ask"
    assert body["fallback"] is True
    assert "Rohan" in body["content"]


def test_referral_followup_fallback(client: TestClient) -> None:
    ref_id = _create_ref(client)
    r = client.post(f"/api/drafts/referral/{ref_id}/followup", json={})
    assert r.status_code == 200
    assert r.json()["draft_type"] == "referral_followup"


def test_history_returns_all(client: TestClient) -> None:
    app_id = _create_app(client)
    client.post(f"/api/drafts/application/{app_id}/followup", json={})
    client.post(
        f"/api/drafts/application/{app_id}/followup",
        json={"regenerate": True},
    )
    r = client.get(f"/api/drafts/application/{app_id}/history")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_quota_returns_429(client: TestClient, db: Any, monkeypatch) -> None:
    from app.config import settings
    monkeypatch.setattr(settings, "drafts_per_user_per_day", 1)
    app_id = _create_app(client)
    # Force two non-cached calls: first creates, second regenerates → should 429
    client.post(f"/api/drafts/application/{app_id}/followup", json={})
    r = client.post(
        f"/api/drafts/application/{app_id}/followup",
        json={"regenerate": True},
    )
    assert r.status_code == 429
