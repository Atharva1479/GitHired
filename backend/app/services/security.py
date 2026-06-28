"""Security middleware + rate limiter."""
from __future__ import annotations

import logging as _logging

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings


# --- Rate limiter ---------------------------------------------------------
# Key: authenticated user_id (prevents IP rotation bypass) → falls back to
# IP for unauthenticated requests (login, health, etc.).
# The import is deferred inside the function to avoid a circular import at
# module load time (session → config, security → config are both fine, but
# security → session during Settings construction can't resolve).

def _get_user_or_ip(request: Request) -> str:
    try:
        from app.services.session import read as _read_session  # deferred — avoids circular
        uid = _read_session(request)
        if uid is not None:
            return f"user:{uid}"
    except Exception:  # noqa: BLE001
        pass
    return get_remote_address(request)


# When REDIS_URL is set, counters are stored in Redis so all replicas share
# the same rate-limit state. Without it, each process tracks independently —
# effective limit becomes N × configured limit behind a load balancer.
if settings.redis_url:
    limiter = Limiter(
        key_func=_get_user_or_ip,
        default_limits=[],
        storage_uri=settings.redis_url,
    )
else:
    if settings.environment == "production":
        _logging.getLogger("security").warning(
            "REDIS_URL is not set — rate limits are per-process only and will be "
            "ineffective behind multiple replicas. Set REDIS_URL to enable distributed limiting."
        )
    limiter = Limiter(key_func=_get_user_or_ip, default_limits=[])


# --- Security headers -----------------------------------------------------

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Sensible defaults. HSTS only in production to avoid breaking http://localhost."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        response: Response = await call_next(request)
        h = response.headers
        h.setdefault("X-Content-Type-Options", "nosniff")
        # Skip X-Frame-Options for file-serving endpoints so the PDF viewer
        # iframe can load across origins in development (frontend :3000 → api :8000).
        path = request.url.path
        if not (path.endswith("/file") or "/files/" in path):
            h.setdefault("X-Frame-Options", "SAMEORIGIN")
        h.setdefault("Referrer-Policy", "no-referrer")
        h.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=()",
        )
        # CSP: this is a JSON API — no HTML surfaces are served, so a tight
        # policy is safe. default-src 'none' blocks any accidental HTML page
        # from loading scripts, images, or frames.
        h.setdefault(
            "Content-Security-Policy",
            "default-src 'none'; frame-ancestors 'none'",
        )
        if settings.environment == "production":
            h.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response
