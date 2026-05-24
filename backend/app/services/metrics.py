"""Prometheus metrics: counters + a request-timing middleware."""
from __future__ import annotations

import time

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Match

from app.config import settings

# --- Metric definitions ---------------------------------------------------

REQUESTS_TOTAL = Counter(
    "jobpilot_requests_total",
    "Total HTTP requests handled.",
    ["method", "path", "status"],
)

REQUEST_DURATION = Histogram(
    "jobpilot_request_duration_seconds",
    "HTTP request duration in seconds.",
    ["method", "path"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

GEMINI_CALLS_TOTAL = Counter(
    "jobpilot_gemini_calls_total",
    "Total Gemini API calls.",
    ["model", "outcome"],  # outcome: ok | fallback | rate_limited | error
)

GEMINI_COST_USD_TOTAL = Counter(
    "jobpilot_gemini_cost_usd_total",
    "Approximate cumulative Gemini cost in USD.",
    ["model"],
)

NUDGES_FIRED_TOTAL = Counter(
    "jobpilot_nudges_fired_total",
    "Nudges inserted by the engine.",
    ["type", "severity"],
)

LOGIN_TOTAL = Counter(
    "jobpilot_login_total",
    "Auth login attempts.",
    ["outcome"],  # success | failed | invalid_state
)

GAMIFY_XP_AWARDED = Counter(
    "jobpilot_gamify_xp_awarded_total",
    "Total XP awarded.",
    ["event_key"],
)

GAMIFY_LEVEL_UPS = Counter(
    "jobpilot_gamify_level_ups_total",
    "Level-up transitions by destination level.",
    ["new_level"],
)

GAMIFY_ACHIEVEMENTS = Counter(
    "jobpilot_gamify_achievements_total",
    "Achievements unlocked.",
    ["code"],
)

PILOT_TURNS = Counter(
    "jobpilot_pilot_turns_total",
    "Pilot conversation turns.",
    ["outcome", "kind"],  # outcome: ok|error  kind: greeting|chat
)

PILOT_AGENT_TURNS = Counter(
    "jobpilot_pilot_agent_turns_total",
    "Pilot agent loop completions, by outcome.",
    ["outcome"],  # ok | ok_suspect | timeout | max_steps | error | refusal | gemini_unavailable
)

PILOT_AGENT_TOOL_CALLS = Counter(
    "jobpilot_pilot_agent_tool_calls_total",
    "Pilot agent tool calls.",
    ["tool", "outcome"],  # outcome: ok | error
)


# --- Helpers --------------------------------------------------------------

def render() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST


def record_gemini(model: str, outcome: str, cost_usd: float = 0.0) -> None:
    GEMINI_CALLS_TOTAL.labels(model=model, outcome=outcome).inc()
    if cost_usd > 0:
        GEMINI_COST_USD_TOTAL.labels(model=model).inc(cost_usd)


def record_nudge(nudge_type: str, severity: str) -> None:
    NUDGES_FIRED_TOTAL.labels(type=nudge_type, severity=severity).inc()


def record_login(outcome: str) -> None:
    LOGIN_TOTAL.labels(outcome=outcome).inc()


# --- Middleware -----------------------------------------------------------

class PrometheusMiddleware(BaseHTTPMiddleware):
    """Record requests_total + request_duration_seconds.

    Path label uses the route template (e.g. '/api/applications/{id}') to keep
    cardinality bounded — never the raw URL.
    """

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        if not settings.metrics_enabled:
            return await call_next(request)

        if request.url.path == "/metrics":
            return await call_next(request)

        start = time.perf_counter()
        status_code = 500
        try:
            response: Response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            elapsed = time.perf_counter() - start
            label_path = _route_template(request) or request.url.path
            REQUESTS_TOTAL.labels(
                method=request.method,
                path=label_path,
                status=str(status_code),
            ).inc()
            REQUEST_DURATION.labels(
                method=request.method, path=label_path
            ).observe(elapsed)


def _route_template(request: Request) -> str | None:
    """Resolve the matched route template; falls back to None on miss."""
    routes = request.scope.get("app").routes if request.scope.get("app") else []
    for route in routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            return getattr(route, "path", None)
    return None
