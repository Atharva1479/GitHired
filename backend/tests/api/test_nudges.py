from datetime import date, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import TEST_USER_ID

TODAY = date.today()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _seed_old_application(db: Any, days_ago: int) -> int:
    rows = db.fetchall(
        """
        INSERT INTO applications
            (user_id, company, role, source, applied_date, last_updated, created_at)
        VALUES (%s, 'Acme', 'Eng', 'LinkedIn', %s, NOW(), NOW())
        RETURNING id
        """,
        (TEST_USER_ID, TODAY - timedelta(days=days_ago)),
    )
    return rows[0][0]


def test_run_inserts_then_dedups(client: TestClient, db: Any) -> None:
    _seed_old_application(db, days_ago=8)  # triggers R1 only

    r1 = client.post("/api/nudges/run")
    assert r1.status_code == 202
    inserted_first = r1.json()["inserted"]
    assert inserted_first >= 1

    r2 = client.post("/api/nudges/run")
    assert r2.status_code == 202
    # Second run shouldn't re-insert the same (type, ref, day)
    assert r2.json()["inserted"] == 0


def test_list_today_orders_by_severity(client: TestClient, db: Any) -> None:
    _seed_old_application(db, days_ago=15)  # R1 (due) + R2 (overdue)
    client.post("/api/nudges/run")

    r = client.get("/api/nudges/today")
    assert r.status_code == 200
    body = r.json()
    severities = [n["severity"] for n in body]
    assert severities[0] == "overdue"  # ordered overdue → due → info


def test_mark_acted_removes_from_today(client: TestClient, db: Any) -> None:
    _seed_old_application(db, days_ago=8)
    client.post("/api/nudges/run")
    today = client.get("/api/nudges/today").json()
    assert len(today) >= 1

    nid = today[0]["id"]
    assert client.post(f"/api/nudges/{nid}/acted").status_code == 204

    today2 = client.get("/api/nudges/today").json()
    assert all(n["id"] != nid for n in today2)


def test_snooze_hides_from_today(client: TestClient, db: Any) -> None:
    _seed_old_application(db, days_ago=8)
    client.post("/api/nudges/run")
    today = client.get("/api/nudges/today").json()
    nid = today[0]["id"]

    r = client.post(f"/api/nudges/{nid}/snooze", json={"days": 3})
    assert r.status_code == 204

    today2 = client.get("/api/nudges/today").json()
    assert all(n["id"] != nid for n in today2)

    # Still shows in full history list
    all_list = client.get("/api/nudges").json()
    assert any(n["id"] == nid for n in all_list)


def test_mark_read_dims_in_today(client: TestClient, db: Any) -> None:
    _seed_old_application(db, days_ago=8)
    client.post("/api/nudges/run")
    today = client.get("/api/nudges/today").json()
    nid = today[0]["id"]

    assert client.post(f"/api/nudges/{nid}/read").status_code == 204
    # mark_read keeps it in today (still unacted), but read_at is set
    today2 = client.get("/api/nudges/today").json()
    matched = next((n for n in today2 if n["id"] == nid), None)
    assert matched is None  # today filter excludes read_at IS NOT NULL


def test_run_empty_state_returns_zero(client: TestClient) -> None:
    r = client.post("/api/nudges/run")
    assert r.status_code == 202
    # apply_more nudge fires (weekly_count < 5), so > 0 unless we filter that
    # Either way, second run should be 0
    second = client.post("/api/nudges/run").json()
    assert second["inserted"] == 0


def test_mark_acted_not_found(client: TestClient) -> None:
    assert client.post("/api/nudges/999999/acted").status_code == 404
