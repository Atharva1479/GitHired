"""Tests for the ATS scorer router.

Covers analyze, ai-feedback, and tailor endpoints which previously had zero
test coverage. ML models may be absent in CI — fallback paths are tested too.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

_RESUME = """
Jane Smith
Backend Engineer — 4 years of experience.

Skills: Python, FastAPI, PostgreSQL, Docker, REST APIs, Git, SQLAlchemy.

Experience:
  Backend Engineer, Acme Inc (2020-2024)
  - Built REST APIs in FastAPI serving 100k req/day.
  - Managed PostgreSQL schemas and wrote Alembic migrations.
  - Containerised services with Docker and docker-compose.

Education: B.Eng Computer Science, 2020.
"""

_JD = """
We are hiring a Backend Software Engineer.
Requirements: Python (3+ years), FastAPI, PostgreSQL, REST API design.
Nice to have: Docker, Redis, Kubernetes, CI/CD.
Responsibilities: design APIs, write tests, deploy microservices.
"""


# ── /api/ats/analyze ──────────────────────────────────────────────────────────

def test_analyze_with_resume_text() -> None:
    """analyze returns overall_score and echoes resume_text back."""
    with TestClient(app) as client:
        r = client.post(
            "/api/ats/analyze",
            data={"job_description": _JD, "resume_text": _RESUME},
        )
        assert r.status_code == 200
        data = r.json()
        assert "overall_score" in data
        assert "resume_text" in data
        assert isinstance(data["overall_score"], (int, float))
        assert 0 <= data["overall_score"] <= 100


def test_analyze_missing_resume_returns_400() -> None:
    """analyze without resume_text or file → 400."""
    with TestClient(app) as client:
        r = client.post("/api/ats/analyze", data={"job_description": _JD})
        assert r.status_code == 400


def test_analyze_empty_jd_returns_400() -> None:
    """analyze with blank job_description → 400."""
    with TestClient(app) as client:
        r = client.post(
            "/api/ats/analyze",
            data={"job_description": "   ", "resume_text": _RESUME},
        )
        assert r.status_code == 400


def test_analyze_too_short_resume_returns_400() -> None:
    """analyze with resume_text shorter than 50 chars → 400."""
    with TestClient(app) as client:
        r = client.post(
            "/api/ats/analyze",
            data={"job_description": _JD, "resume_text": "too short"},
        )
        assert r.status_code == 400


# ── /api/ats/ai-feedback ──────────────────────────────────────────────────────

def test_ai_feedback_returns_200() -> None:
    """ai-feedback endpoint accepts a valid score object and returns 200."""
    with TestClient(app) as client:
        r = client.post(
            "/api/ats/ai-feedback",
            json={
                "overall_score": 68.0,
                "required_missing": ["Redis", "Kubernetes"],
                "preferred_missing": ["Go"],
                "sections_found": ["Experience", "Skills", "Education"],
                "sections_missing": ["Summary"],
                "ats_risks": ["Generic objective statement"],
                "suggestions": ["Add a concise summary section"],
            },
        )
        assert r.status_code == 200


def test_ai_feedback_empty_missing_lists() -> None:
    """ai-feedback with no missing keywords still returns 200."""
    with TestClient(app) as client:
        r = client.post(
            "/api/ats/ai-feedback",
            json={"overall_score": 90.0},
        )
        assert r.status_code == 200


# ── /api/ats/tailor ───────────────────────────────────────────────────────────

def test_tailor_no_missing_returns_empty_suggestions() -> None:
    """tailor with no missing keywords short-circuits and returns empty list."""
    with TestClient(app) as client:
        r = client.post(
            "/api/ats/tailor",
            json={
                "resume_text": _RESUME,
                "jd_text": _JD,
                "required_missing": [],
                "preferred_missing": [],
            },
        )
        assert r.status_code == 200
        assert r.json() == {"suggestions": []}


def test_tailor_short_resume_returns_400() -> None:
    """tailor with resume_text < 50 chars → 400."""
    with TestClient(app) as client:
        r = client.post(
            "/api/ats/tailor",
            json={
                "resume_text": "tiny",
                "jd_text": _JD,
                "required_missing": ["Redis"],
                "preferred_missing": [],
            },
        )
        assert r.status_code == 400


def test_tailor_with_missing_keywords_returns_200() -> None:
    """tailor with keywords returns 200 and a suggestions list."""
    with TestClient(app) as client:
        r = client.post(
            "/api/ats/tailor",
            json={
                "resume_text": _RESUME,
                "jd_text": _JD,
                "required_missing": ["Redis"],
                "preferred_missing": ["Kubernetes"],
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)
