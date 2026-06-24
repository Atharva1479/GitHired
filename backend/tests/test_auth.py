"""Tests for the auth router.

Covers the critical paths that previously had zero test coverage:
- OAuth state validation
- /me endpoint
- /logout
- /preferences toggle
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_google_login_redirects_or_not_configured() -> None:
    """Login endpoint either redirects to Google or 500s if OAuth not configured."""
    with TestClient(app, follow_redirects=False) as client:
        r = client.get("/api/auth/google/login")
        assert r.status_code in (302, 500)
        if r.status_code == 302:
            assert "accounts.google.com" in r.headers.get("location", "")


def test_google_callback_invalid_state() -> None:
    """Callback with wrong state cookie value redirects to /login?error=invalid_state."""
    with TestClient(app, follow_redirects=False) as client:
        client.cookies.set("jp_oauth_state", "expected-state")
        r = client.get(
            "/api/auth/google/callback",
            params={"code": "fake-code", "state": "wrong-state"},
        )
        assert r.status_code == 302
        assert "invalid_state" in r.headers.get("location", "")


def test_google_callback_missing_code() -> None:
    """Callback with no code parameter redirects to /login?error=invalid_state."""
    with TestClient(app, follow_redirects=False) as client:
        r = client.get("/api/auth/google/callback")
        assert r.status_code == 302
        assert "invalid_state" in r.headers.get("location", "")


def test_google_callback_oauth_error_forwarded() -> None:
    """Callback with error param from Google redirects to /login with that error."""
    with TestClient(app, follow_redirects=False) as client:
        r = client.get(
            "/api/auth/google/callback",
            params={"error": "access_denied"},
        )
        assert r.status_code == 302
        location = r.headers.get("location", "")
        assert "access_denied" in location or "error" in location


def test_me_returns_test_user() -> None:
    """Authenticated /me returns id and email for the injected test user."""
    with TestClient(app) as client:
        r = client.get("/api/auth/me")
        assert r.status_code == 200
        data = r.json()
        assert "id" in data
        assert "email" in data
        assert isinstance(data["id"], int)


def test_logout_returns_ok() -> None:
    """POST /logout returns 200 with ok: true."""
    with TestClient(app) as client:
        r = client.post("/api/auth/logout")
        assert r.status_code == 200
        assert r.json() == {"ok": True}


def test_preferences_toggle_on_and_off() -> None:
    """PATCH /preferences toggles auto_brief_enabled and persists correctly."""
    with TestClient(app) as client:
        r = client.patch("/api/auth/preferences", json={"auto_brief_enabled": True})
        assert r.status_code == 200
        assert r.json()["auto_brief_enabled"] is True

        r2 = client.patch("/api/auth/preferences", json={"auto_brief_enabled": False})
        assert r2.status_code == 200
        assert r2.json()["auto_brief_enabled"] is False


def test_preferences_invalid_body() -> None:
    """PATCH /preferences with missing field returns 422."""
    with TestClient(app) as client:
        r = client.patch("/api/auth/preferences", json={})
        assert r.status_code == 422
