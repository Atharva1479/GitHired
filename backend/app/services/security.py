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
# Keyed by client IP. For SaaS behind a reverse proxy, ensure the proxy sets
# X-Forwarded-For correctly and `get_remote_address` picks it up.
#
# When REDIS_URL is set, counters are stored in Redis so all replicas share
# the same rate-limit state. Without it, each process tracks independently —
# effective limit becomes N × configured limit behind a load balancer.
if settings.redis_url:
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[],
        storage_uri=settings.redis_url,
    )
else:
    if settings.environment == "production":
        _logging.getLogger("security").warning(
            "REDIS_URL is not set — rate limits are per-process only and will be "
            "ineffective behind multiple replicas. Set REDIS_URL to enable distributed limiting."
        )
    limiter = Limiter(key_func=get_remote_address, default_limits=[])


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
        if settings.environment == "production":
            h.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response
