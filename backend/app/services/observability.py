"""Logging, request-id propagation, and Sentry init."""
from __future__ import annotations

import logging
import time
import uuid
from contextvars import ContextVar

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings

_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
_user_id_ctx: ContextVar[int | None] = ContextVar("user_id", default=None)


def configure_logging() -> None:
    """Configure stdlib + structlog. JSON in prod, pretty console in dev."""
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        timestamper,
        _add_request_context,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.log_format == "json":
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level.upper())
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Quiet noisy libraries
    logging.basicConfig(level=settings.log_level.upper(), format="%(message)s")
    for noisy in ("uvicorn.access", "httpx", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def _add_request_context(
    _: structlog.types.WrappedLogger,
    __: str,
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    rid = _request_id_ctx.get()
    uid = _user_id_ctx.get()
    if rid:
        event_dict.setdefault("request_id", rid)
    if uid:
        event_dict.setdefault("user_id", uid)
    return event_dict


def configure_sentry() -> bool:
    """Initialize Sentry SDK if a DSN is configured. Returns whether enabled."""
    if not settings.sentry_dsn:
        return False
    import sentry_sdk
    from sentry_sdk.integrations.asyncio import AsyncioIntegration
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        send_default_pii=False,
        integrations=[
            StarletteIntegration(),
            FastApiIntegration(),
            AsyncioIntegration(),
        ],
    )
    return True


def set_user_context(user_id: int | None) -> None:
    _user_id_ctx.set(user_id)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assign a request_id, log request/response, expose X-Request-Id."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        token = _request_id_ctx.set(rid)
        logger = structlog.get_logger("http")
        start = time.perf_counter()

        # Avoid logging health probes — keep the signal clean.
        skip = request.url.path in ("/healthz", "/readyz", "/metrics")
        if not skip:
            logger.info(
                "request.start", method=request.method, path=request.url.path
            )

        try:
            response: Response = await call_next(request)
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            logger.exception(
                "request.unhandled",
                method=request.method,
                path=request.url.path,
                elapsed_ms=round(elapsed, 2),
                error=str(exc),
            )
            _request_id_ctx.reset(token)
            raise

        elapsed = (time.perf_counter() - start) * 1000
        response.headers["X-Request-Id"] = rid
        if not skip:
            logger.info(
                "request.end",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                elapsed_ms=round(elapsed, 2),
            )
        _request_id_ctx.reset(token)
        return response
