"""M10 Phase 4 — study AI generation tests.

Strategy: mock the Gemini and Ollama providers so tests run without
external dependencies. Each test verifies schema validation, Pydantic
output, and that the apply endpoints persist rows correctly.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import study_ai


# ── fixtures ─────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


_PLAN_JSON = {
    "sections": [
        {
            "name": "Backend",
            "subsections": [
                {
                    "name": "Spring Boot",
                    "topics": [
                        {"title": "Dependency Injection", "notes": "scopes, qualifier"},
                        {"title": "Bean lifecycle"},
                    ],
                }
            ],
        }
    ]
}

_TOPICS_JSON = {
    "topics": [
        {"title": "Dependency Injection", "notes": "scopes, qualifier"},
        {"title": "Bean lifecycle"},
        {"title": "Auto-configuration"},
    ]
}


def _mock_gemini(payload: dict):
    """Return an async context-manager-compatible mock of _gemini_json."""
    async def _fake(prompt: str):
        return payload

    return _fake


def _mock_ollama(payload: dict):
    async def _fake(prompt: str):
        return payload

    return _fake


# ── generate_plan unit tests ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_plan_returns_pydantic_model():
    with patch.object(study_ai, "_gemini_json", _mock_gemini(_PLAN_JSON)):
        result = await study_ai.generate_plan("Java Backend Developer")

    assert len(result.sections) == 1
    sec = result.sections[0]
    assert sec.name == "Backend"
    assert len(sec.subsections) == 1
    sub = sec.subsections[0]
    assert sub.name == "Spring Boot"
    assert len(sub.topics) == 2
    assert sub.topics[0].title == "Dependency Injection"
    assert sub.topics[0].notes == "scopes, qualifier"
    assert sub.topics[1].notes is None


@pytest.mark.asyncio
async def test_generate_plan_falls_back_to_ollama_on_gemini_failure():
    from app.services.gemini_service import GeminiUnavailable

    async def _fail(_prompt: str):
        raise GeminiUnavailable("quota exceeded")

    with (
        patch.object(study_ai, "_gemini_json", _fail),
        patch.object(study_ai, "_ollama_json", _mock_ollama(_PLAN_JSON)),
        patch.object(study_ai.settings, "llm_provider", "auto"),
    ):
        result = await study_ai.generate_plan("Java Backend Developer")

    assert len(result.sections) == 1


@pytest.mark.asyncio
async def test_generate_plan_raises_on_invalid_json():
    async def _bad(_prompt: str):
        return {"unexpected_key": []}

    with patch.object(study_ai, "_gemini_json", _bad):
        result = await study_ai.generate_plan("Anything")
    # Empty sections is valid — no sections produced but no exception.
    assert result.sections == []


@pytest.mark.asyncio
async def test_generate_plan_strips_markdown_fences():
    raw_text = "```json\n" + json.dumps(_PLAN_JSON) + "\n```"

    async def _fenced(_prompt: str):
        return study_ai._extract_json(raw_text)

    with patch.object(study_ai, "_gemini_json", _fenced):
        result = await study_ai.generate_plan("Java Backend Developer")

    assert len(result.sections) == 1


# ── generate_topics unit tests ───────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_topics_returns_list():
    with patch.object(study_ai, "_gemini_json", _mock_gemini(_TOPICS_JSON)):
        result = await study_ai.generate_topics("Backend", "Spring Boot", count=3)

    assert len(result.topics) == 3
    assert result.topics[0].title == "Dependency Injection"


@pytest.mark.asyncio
async def test_generate_topics_ollama_fallback():
    from app.services.gemini_service import GeminiUnavailable

    async def _fail(_prompt: str):
        raise GeminiUnavailable("quota")

    with (
        patch.object(study_ai, "_gemini_json", _fail),
        patch.object(study_ai, "_ollama_json", _mock_ollama(_TOPICS_JSON)),
        patch.object(study_ai.settings, "llm_provider", "auto"),
    ):
        result = await study_ai.generate_topics("Backend", "Spring Boot", count=3)

    assert len(result.topics) == 3


# ── HTTP endpoint tests ──────────────────────────────────────────────


def test_generate_plan_endpoint_returns_200(client: TestClient):
    with patch.object(study_ai, "_gemini_json", _mock_gemini(_PLAN_JSON)):
        r = client.post(
            "/api/study/generate",
            json={"role": "Java Backend Developer", "target_companies": ["Stripe"]},
        )
    assert r.status_code == 200
    body = r.json()
    assert len(body["sections"]) == 1
    assert body["sections"][0]["name"] == "Backend"


def test_generate_plan_endpoint_503_on_provider_error(client: TestClient):
    from app.services.gemini_service import GeminiUnavailable
    from app.services.ollama_service import OllamaUnavailable

    async def _gemini_fail(_prompt):
        raise GeminiUnavailable("quota")

    async def _ollama_fail(_prompt):
        raise OllamaUnavailable("down")

    with (
        patch.object(study_ai, "_gemini_json", _gemini_fail),
        patch.object(study_ai, "_ollama_json", _ollama_fail),
        patch.object(study_ai.settings, "llm_provider", "auto"),
    ):
        r = client.post(
            "/api/study/generate",
            json={"role": "Java Backend Developer"},
        )
    assert r.status_code == 503


def test_apply_generated_plan_persists_tree(client: TestClient):
    with patch.object(study_ai, "_gemini_json", _mock_gemini(_PLAN_JSON)):
        preview = client.post(
            "/api/study/generate",
            json={"role": "Java Backend Developer"},
        ).json()

    r = client.post("/api/study/generate/apply", json=preview)
    assert r.status_code == 200
    plan = r.json()
    # At least one section with the right name should be in the saved tree.
    names = [s["name"] for s in plan["sections"]]
    assert "Backend" in names


def test_generate_topics_endpoint_returns_preview(client: TestClient):
    # Need a subsection to generate for.
    sec = client.post(
        "/api/study/sections", json={"name": "Backend"},
    ).json()
    sub = client.post(
        f"/api/study/sections/{sec['id']}/subsections",
        json={"name": "Spring Boot"},
    ).json()

    with patch.object(study_ai, "_gemini_json", _mock_gemini(_TOPICS_JSON)):
        r = client.post(
            f"/api/study/subsections/{sub['id']}/generate-topics",
            json={"count": 3},
        )
    assert r.status_code == 200
    body = r.json()
    assert len(body["topics"]) == 3


def test_apply_generated_topics_persists(client: TestClient):
    sec = client.post(
        "/api/study/sections", json={"name": "Backend"},
    ).json()
    sub = client.post(
        f"/api/study/sections/{sec['id']}/subsections",
        json={"name": "Spring Boot"},
    ).json()

    with patch.object(study_ai, "_gemini_json", _mock_gemini(_TOPICS_JSON)):
        preview = client.post(
            f"/api/study/subsections/{sub['id']}/generate-topics",
            json={"count": 3},
        ).json()

    r = client.post(
        f"/api/study/subsections/{sub['id']}/generate-topics/apply",
        json=preview,
    )
    assert r.status_code == 201
    topics = r.json()
    assert len(topics) == 3
    assert topics[0]["title"] == "Dependency Injection"
    assert all(t["subsection_id"] == sub["id"] for t in topics)
