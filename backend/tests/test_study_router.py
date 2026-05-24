"""HTTP-level tests for /api/study/* endpoints.

Uses FastAPI's TestClient against the real app — auth is overridden in
conftest to TEST_USER_ID so every request is "logged in" as the
synthetic test user.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ── plan endpoint ────────────────────────────────────────────────────


def test_get_plan_empty(client: TestClient) -> None:
    r = client.get("/api/study/plan")
    assert r.status_code == 200
    assert r.json() == {"sections": []}


# ── sections CRUD ────────────────────────────────────────────────────


def test_create_section_returns_201(client: TestClient) -> None:
    r = client.post(
        "/api/study/sections",
        json={"name": "Backend", "icon": "server"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Backend"
    assert body["icon"] == "server"
    assert body["position"] == 0


def test_patch_section_renames(client: TestClient) -> None:
    sec = client.post(
        "/api/study/sections", json={"name": "Java"},
    ).json()
    r = client.patch(
        f"/api/study/sections/{sec['id']}", json={"name": "Java SE"},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Java SE"


def test_delete_section_returns_204_and_hides_from_plan(client: TestClient) -> None:
    sec = client.post(
        "/api/study/sections", json={"name": "Goes Away"},
    ).json()
    r = client.delete(f"/api/study/sections/{sec['id']}")
    assert r.status_code == 204

    plan = client.get("/api/study/plan").json()
    assert sec["id"] not in [s["id"] for s in plan["sections"]]


# ── subsections + topics through the API ────────────────────────────


def test_full_create_chain_via_api(client: TestClient) -> None:
    sec = client.post(
        "/api/study/sections", json={"name": "Backend"},
    ).json()
    sub = client.post(
        f"/api/study/sections/{sec['id']}/subsections",
        json={"name": "Spring Boot"},
    ).json()
    assert sub["section_id"] == sec["id"]

    topic = client.post(
        f"/api/study/subsections/{sub['id']}/topics",
        json={
            "title": "Dependency Injection",
            "notes": "scopes",
            "kind": "revise",
            "tags": ["interview", "core"],
        },
    ).json()
    assert topic["kind"] == "revise"
    assert topic["status"] == "todo"
    assert topic["tags"] == ["interview", "core"]


def test_plan_returns_full_nested_tree(client: TestClient) -> None:
    sec = client.post(
        "/api/study/sections", json={"name": "X"},
    ).json()
    sub = client.post(
        f"/api/study/sections/{sec['id']}/subsections", json={"name": "Y"},
    ).json()
    client.post(
        f"/api/study/subsections/{sub['id']}/topics", json={"title": "Z"},
    )
    plan = client.get("/api/study/plan").json()
    target = next(s for s in plan["sections"] if s["id"] == sec["id"])
    assert len(target["subsections"]) == 1
    assert target["subsections"][0]["topics"][0]["title"] == "Z"


# ── revise endpoint ──────────────────────────────────────────────────


def test_revise_topic_returns_envelope_and_flips_status(
    client: TestClient,
) -> None:
    sec = client.post(
        "/api/study/sections", json={"name": "Backend"},
    ).json()
    sub = client.post(
        f"/api/study/sections/{sec['id']}/subsections",
        json={"name": "Spring"},
    ).json()
    topic = client.post(
        f"/api/study/subsections/{sub['id']}/topics",
        json={"title": "DI"},
    ).json()

    r = client.post(f"/api/study/topics/{topic['id']}/revise")
    assert r.status_code == 200
    body = r.json()
    assert body["topic"]["status"] == "done"
    assert body["topic"]["revision_count"] == 1
    assert body["topic"]["last_revised_at"] is not None
    assert body["new_status"] == "done"


def test_unmark_topic_resets_status(client: TestClient) -> None:
    sec = client.post(
        "/api/study/sections", json={"name": "Backend"},
    ).json()
    sub = client.post(
        f"/api/study/sections/{sec['id']}/subsections", json={"name": "S"},
    ).json()
    topic = client.post(
        f"/api/study/subsections/{sub['id']}/topics", json={"title": "T"},
    ).json()
    client.post(f"/api/study/topics/{topic['id']}/revise")
    r = client.post(f"/api/study/topics/{topic['id']}/unmark")
    assert r.status_code == 200
    assert r.json()["status"] == "todo"


# ── progress endpoint ────────────────────────────────────────────────


def test_progress_reflects_status_counts(client: TestClient) -> None:
    sec = client.post(
        "/api/study/sections", json={"name": "X"},
    ).json()
    sub = client.post(
        f"/api/study/sections/{sec['id']}/subsections", json={"name": "Y"},
    ).json()
    a = client.post(
        f"/api/study/subsections/{sub['id']}/topics", json={"title": "A"},
    ).json()
    client.post(
        f"/api/study/subsections/{sub['id']}/topics", json={"title": "B"},
    )
    client.post(f"/api/study/topics/{a['id']}/revise")

    p = client.get("/api/study/progress").json()
    assert p["total_topics"] == 2
    assert p["todo"] == 1
    assert p["done"] == 1
    assert p["revisions_this_week"] == 1


# ── 404 paths ────────────────────────────────────────────────────────


def test_get_missing_section_returns_404_on_patch(client: TestClient) -> None:
    r = client.patch("/api/study/sections/9999999", json={"name": "X"})
    assert r.status_code == 404


def test_revise_missing_topic_returns_404(client: TestClient) -> None:
    r = client.post("/api/study/topics/9999999/revise")
    assert r.status_code == 404
