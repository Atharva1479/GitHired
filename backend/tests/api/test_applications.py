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
        "company": "Stripe",
        "role": "Frontend Engineer",
        "source": "LinkedIn",
        "applied_date": "2026-05-01",
    }
    return {**base, **over}


def test_create_minimal(client: TestClient) -> None:
    r = client.post("/api/applications", json=_payload())
    assert r.status_code == 201
    out = r.json()
    assert out["company"] == "Stripe"
    assert out["status"] == "Applied"
    assert out["follow_up_count"] == 0
    assert out["id"] > 0


def test_create_rejects_invalid_source(client: TestClient) -> None:
    r = client.post("/api/applications", json=_payload(source="Twitter"))
    assert r.status_code == 422


def test_list_returns_created(client: TestClient) -> None:
    for c in ("A", "B", "C"):
        client.post("/api/applications", json=_payload(company=c))
    r = client.get("/api/applications")
    assert r.status_code == 200
    assert len(r.json()) == 3


def test_list_filters_by_status(client: TestClient) -> None:
    for c in ("A", "B"):
        client.post("/api/applications", json=_payload(company=c))
    target = client.post("/api/applications", json=_payload(company="X")).json()
    client.patch(f"/api/applications/{target['id']}", json={"status": "Interview"})

    r = client.get("/api/applications", params={"status": "Interview"})
    assert r.status_code == 200
    assert {row["company"] for row in r.json()} == {"X"}


def test_get_not_found(client: TestClient) -> None:
    r = client.get("/api/applications/999999")
    assert r.status_code == 404
    assert r.json()["type"] == "not_found"


def test_create_emits_event(client: TestClient, db: Any) -> None:
    client.post("/api/applications", json=_payload())
    rows = db.fetchall(
        "SELECT event_type FROM events "
        "WHERE event_type = %s AND user_id = %s AND deleted_at IS NULL",
        ("application.created", TEST_USER_ID),
    )
    assert len(rows) == 1


def test_update_status_emits_event(client: TestClient, db: Any) -> None:
    created = client.post("/api/applications", json=_payload()).json()
    r = client.patch(
        f"/api/applications/{created['id']}", json={"status": "Screening"}
    )
    assert r.status_code == 200
    assert r.json()["status"] == "Screening"

    rows = db.fetchall(
        "SELECT payload FROM events "
        "WHERE event_type = %s AND user_id = %s AND deleted_at IS NULL",
        ("application.status_changed", TEST_USER_ID),
    )
    assert len(rows) == 1


def test_update_no_status_change_emits_no_event(client: TestClient, db: Any) -> None:
    created = client.post("/api/applications", json=_payload()).json()
    client.patch(f"/api/applications/{created['id']}", json={"notes": "follow up next week"})

    rows = db.fetchall(
        "SELECT 1 FROM events "
        "WHERE event_type = %s AND user_id = %s AND deleted_at IS NULL",
        ("application.status_changed", TEST_USER_ID),
    )
    assert rows == []


def test_delete_then_get_returns_404(client: TestClient) -> None:
    created = client.post("/api/applications", json=_payload()).json()
    r = client.delete(f"/api/applications/{created['id']}")
    assert r.status_code == 204

    r = client.get(f"/api/applications/{created['id']}")
    assert r.status_code == 404


def test_delete_excludes_from_list(client: TestClient) -> None:
    created = client.post("/api/applications", json=_payload()).json()
    client.delete(f"/api/applications/{created['id']}")
    r = client.get("/api/applications")
    assert all(row["id"] != created["id"] for row in r.json())


def test_followup_increments(client: TestClient) -> None:
    created = client.post("/api/applications", json=_payload()).json()
    r = client.post(f"/api/applications/{created['id']}/followup")
    assert r.status_code == 200
    body = r.json()
    assert body["follow_up_count"] == 1
    assert body["last_followed_up_at"] is not None


def test_followup_not_found(client: TestClient) -> None:
    r = client.post("/api/applications/999999/followup")
    assert r.status_code == 404
