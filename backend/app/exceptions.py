from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse
import structlog

from app.config import settings

log = structlog.get_logger("exceptions")


class DomainError(Exception):
    status_code: int = 500
    type_: str = "internal_error"
    title: str = "Internal error"

    def __init__(self, detail: str = "") -> None:
        super().__init__(detail)
        self.detail = detail


class NotFound(DomainError):
    status_code = 404
    type_ = "not_found"
    title = "Resource not found"


class Conflict(DomainError):
    status_code = 409
    type_ = "conflict"
    title = "Conflict"


class RateLimited(DomainError):
    status_code = 429
    type_ = "rate_limited"
    title = "Too many requests"


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "type": exc.type_,
                "title": exc.title,
                "detail": exc.detail,
                "status": exc.status_code,
            },
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        """Last-resort: log with traceback, sanitize response in prod."""
        log.exception(
            "unhandled.exception",
            path=request.url.path,
            method=request.method,
            error_type=type(exc).__name__,
        )
        detail = (
            "An unexpected error occurred."
            if settings.environment == "production"
            else str(exc)
        )
        return JSONResponse(
            status_code=500,
            content={
                "type": "internal_error",
                "title": "Internal error",
                "detail": detail,
                "status": 500,
            },
        )
