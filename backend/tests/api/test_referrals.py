from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import TEST_USER_ID


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _payload(**over: Any) -> dict[str, Any]:
    base = {
        "name": "Rohan Sharma",
        "company": "Stripe",
        "target_role": "Frontend Engineer",
        "connection_sent_date": "2026-05-01",
    }
    return {**base, **over}


def _app_payload(**over: Any) -> dict[str, Any]:
    base = {
        "company": "Stripe",
        "role": "Frontend Engineer",
        "source": "LinkedIn",
        "applied_date": "2026-05-01",
    }
    return {**base, **over}


def test_create_minimal(client: TestClient) -> None:
    r = client.post("/api/referrals", json=_payload())
    assert r.status_code == 201
    out = r.json()
    assert out["name"] == "Rohan Sharma"
    assert out["connection_status"] == "Request Sent"
    assert out["id"] > 0


def test_create_rejects_missing_required(client: TestClient) -> None:
    r = client.post("/api/referrals", json={"name": "A"})
    assert r.status_code == 422


def test_list_returns_created(client: TestClient) -> None:
    for n in ("A", "B", "C"):
        client.post("/api/referrals", json=_payload(name=n))
    r = client.get("/api/referrals")
    assert r.status_code == 200
    assert len(r.json()) == 3


def test_mark_accepted(client: TestClient, db: Any) -> None:
    created = client.post("/api/referrals", json=_payload()).json()
    r = client.post(f"/api/referrals/{created['id']}/mark-accepted")
    assert r.status_code == 200
    assert r.json()["connection_status"] == "Accepted"
    rows = db.fetchall(
        "SELECT 1 FROM events WHERE event_type = %s AND user_id = %s AND deleted_at IS NULL", ("referral.accepted", TEST_USER_ID),
    )
    assert len(rows) == 1


def test_mark_sent_sets_date(client: TestClient) -> None:
    created = client.post("/api/referrals", json=_payload()).json()
    r = client.post(f"/api/referrals/{created['id']}/mark-sent")
    assert r.status_code == 200
    body = r.json()
    assert body["connection_status"] == "Msg Sent"
    assert body["referral_msg_sent_date"] is not None


def test_mark_replied_sets_date(client: TestClient) -> None:
    created = client.post("/api/referrals", json=_payload()).json()
    r = client.post(f"/api/referrals/{created['id']}/mark-replied")
    assert r.status_code == 200
    body = r.json()
    assert body["connection_status"] == "Replied"
    assert body["reply_date"] is not None


def test_patch_status_emits_event(client: TestClient, db: Any) -> None:
    created = client.post("/api/referrals", json=_payload()).json()
    r = client.patch(
        f"/api/referrals/{created['id']}",
        json={"connection_status": "Dropped"},
    )
    assert r.status_code == 200
    rows = db.fetchall(
        "SELECT 1 FROM events "
        "WHERE event_type = %s AND user_id = %s AND deleted_at IS NULL",
        ("referral.status_changed", TEST_USER_ID),
    )
    assert len(rows) == 1


def test_delete_then_get_404(client: TestClient) -> None:
    created = client.post("/api/referrals", json=_payload()).json()
    assert client.delete(f"/api/referrals/{created['id']}").status_code == 204
    assert client.get(f"/api/referrals/{created['id']}").status_code == 404


def test_get_not_found(client: TestClient) -> None:
    assert client.get("/api/referrals/999999").status_code == 404


def test_link_application(client: TestClient) -> None:
    ref = client.post("/api/referrals", json=_payload()).json()
    app = client.post("/api/applications", json=_app_payload()).json()
    r = client.post(
        f"/api/referrals/{ref['id']}/link-application/{app['id']}"
    )
    assert r.status_code == 204
    listed = client.get(f"/api/referrals/{ref['id']}/applications").json()
    assert len(listed) == 1
    assert listed[0]["id"] == app["id"]


def test_unlink_application(client: TestClient) -> None:
    ref = client.post("/api/referrals", json=_payload()).json()
    app = client.post("/api/applications", json=_app_payload()).json()
    client.post(f"/api/referrals/{ref['id']}/link-application/{app['id']}")
    r = client.delete(
        f"/api/referrals/{ref['id']}/link-application/{app['id']}"
    )
    assert r.status_code == 204
    listed = client.get(f"/api/referrals/{ref['id']}/applications").json()
    assert listed == []


def test_link_application_unknown_app_404(client: TestClient) -> None:
    ref = client.post("/api/referrals", json=_payload()).json()
    r = client.post(f"/api/referrals/{ref['id']}/link-application/999999")
    assert r.status_code == 404
