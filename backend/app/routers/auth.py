import secrets
from typing import Annotated

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

from app.config import settings
from app.deps import get_db, get_user_id
from app.repositories import users as users_repo
from app.services import google_oauth, metrics, session
from app.services.security import limiter

router = APIRouter()
OAUTH_STATE_COOKIE = "jp_oauth_state"


@router.get("/google/login")
@limiter.limit(f"{settings.auth_rate_limit_per_minute}/minute")
async def google_login(request: Request) -> RedirectResponse:
    if not settings.google_client_id:
        raise HTTPException(500, "Google OAuth not configured")
    state = secrets.token_urlsafe(24)
    url = google_oauth.build_authorize_url(state)
    resp = RedirectResponse(url, status_code=302)
    resp.set_cookie(
        OAUTH_STATE_COOKIE,
        state,
        max_age=600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return resp


@router.get("/google/callback")
async def google_callback(
    request: Request,
    db: Annotated[asyncpg.Connection, Depends(get_db)],
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    if error:
        metrics.record_login("failed")
        return RedirectResponse(
            f"{settings.frontend_url}/login?error={error}", status_code=302
        )
    expected = request.cookies.get(OAUTH_STATE_COOKIE)
    if not code or not state or not expected or state != expected:
        metrics.record_login("invalid_state")
        return RedirectResponse(
            f"{settings.frontend_url}/login?error=invalid_state", status_code=302
        )

    try:
        tokens = await google_oauth.exchange_code(code)
        info = await google_oauth.fetch_userinfo(tokens["access_token"])
    except Exception:
        metrics.record_login("failed")
        return RedirectResponse(
            f"{settings.frontend_url}/login?error=oauth_failed", status_code=302
        )

    sub = info.get("sub")
    email = info.get("email")
    name = info.get("name") or (email.split("@")[0] if email else "User")
    if not sub or not email:
        metrics.record_login("failed")
        return RedirectResponse(
            f"{settings.frontend_url}/login?error=missing_profile", status_code=302
        )

    user = await users_repo.upsert_google_user(
        db,
        google_sub=sub,
        email=email,
        name=name,
        picture_url=info.get("picture"),
    )

    metrics.record_login("success")
    resp = RedirectResponse(f"{settings.frontend_url}/dashboard", status_code=302)
    session.issue(resp, user_id=user["id"])
    resp.delete_cookie(OAUTH_STATE_COOKIE, path="/")
    return resp


@router.post("/logout")
async def logout() -> Response:
    resp = JSONResponse({"ok": True})
    session.clear(resp)
    return resp


@router.get("/me")
async def me(
    request: Request,
    db: Annotated[asyncpg.Connection, Depends(get_db)],
    user_id: Annotated[int, Depends(get_user_id)],
) -> dict[str, object]:
    user = await users_repo.get_by_id(db, user_id)
    if not user:
        raise HTTPException(401, "Not authenticated")
    return {
        "id": user["id"],
        "email": user["email"],
        "display_name": user["display_name"],
        "picture_url": user.get("picture_url"),
        "auto_brief_enabled": bool(user.get("auto_brief_enabled", False)),
        # Per-login id baked into the signed session cookie. Stays the
        # same across page refreshes, changes on logout/login. The
        # frontend uses this to greet only once per actual login.
        "session_id": session.read_session_id(request),
    }


class _PreferencesPatch(BaseModel):
    auto_brief_enabled: bool


@router.patch("/preferences")
async def update_preferences(
    body: _PreferencesPatch,
    db: Annotated[asyncpg.Connection, Depends(get_db)],
    user_id: Annotated[int, Depends(get_user_id)],
) -> dict[str, bool]:
    """Toggle user preferences. Currently scoped to the voice auto-brief."""
    value = await users_repo.set_auto_brief(db, user_id, body.auto_brief_enabled)
    return {"auto_brief_enabled": value}
