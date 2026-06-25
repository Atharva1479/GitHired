import uuid
from typing import Any

from fastapi import Request, Response
from itsdangerous import BadSignature, URLSafeTimedSerializer

from app.config import settings

COOKIE_NAME = "jp_session"
_serializer = URLSafeTimedSerializer(
    settings.session_secret.get_secret_value(), salt="jp.session.v1"
)


def issue(response: Response, *, user_id: int) -> None:
    # `sid` is a per-login random identifier baked into the signed
    # cookie. A fresh login → fresh sid; a page refresh re-uses the
    # same cookie → same sid. The frontend uses this to decide
    # "this is a new login, greet" vs "this is a refresh, stay quiet".
    sid = uuid.uuid4().hex
    token = _serializer.dumps({"uid": user_id, "sid": sid})
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=settings.session_max_age_days * 24 * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
    )


def clear(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


def _decode(token: str) -> dict[str, Any] | None:
    """Return the decoded payload, or None on bad signature / corruption."""
    try:
        data: dict[str, Any] = _serializer.loads(
            token, max_age=settings.session_max_age_days * 24 * 3600
        )
    except BadSignature:
        return None
    return data if isinstance(data, dict) else None


def read(request: Request) -> int | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    data = _decode(token)
    if data is None:
        return None
    uid = data.get("uid")
    return int(uid) if isinstance(uid, int) else None


def read_session_id(request: Request) -> str | None:
    """Return the per-login session id baked into the cookie, or None.

    Older cookies issued before this feature was added will return None
    — those clients greet exactly once after the upgrade, then stay
    quiet until their next login (when a sid lands). Acceptable.
    """
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    data = _decode(token)
    if data is None:
        return None
    sid = data.get("sid")
    return sid if isinstance(sid, str) and sid else None
