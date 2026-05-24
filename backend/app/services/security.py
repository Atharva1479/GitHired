"""Security middleware + rate limiter."""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings

# --- Rate limiter ---------------------------------------------------------
# Keyed by client IP. For SaaS behind a reverse proxy, ensure the proxy sets
# X-Forwarded-For correctly and `get_remote_address` picks it up.
limiter = Limiter(key_func=get_remote_address, default_limits=[])


# --- Security headers -----------------------------------------------------

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Sensible defaults. HSTS only in production to avoid breaking http://localhost."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        response: Response = await call_next(request)
        h = response.headers
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("X-Frame-Options", "SAMEORIGIN")
        h.setdefault("Referrer-Policy", "no-referrer")
        h.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=()",
        )
        if settings.environment == "production":
            h.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response
