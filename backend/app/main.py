import asyncio
import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from slowapi.errors import RateLimitExceeded

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.config import settings
from app.database import close_db, init_db, pool
from app.services import interview_graph as ig
from app.exceptions import install_exception_handlers
from app.routers import applications as applications_router
from app.routers import auth as auth_router
from app.routers import dashboard as dashboard_router
from app.routers import drafts as drafts_router
from app.routers import files as files_router
from app.routers import gamify as gamify_router
from app.routers import nudges as nudges_router
from app.routers import pilot as pilot_router
from app.routers import referrals as referrals_router
from app.routers import resumes as resumes_router
from app.routers import study as study_router
from app.routers import dsa as dsa_router
from app.routers import analytics as analytics_router
from app.routers import settings as settings_router
from app.routers import ats as ats_router
from app.routers import interview as interview_router
from app.routers import jobs as jobs_router
from app.services import metrics
from app.services.observability import (
    RequestContextMiddleware,
    configure_logging,
    configure_sentry,
)
from app.services.ats.word_semantic import unload as word2vec_unload
from app.services.ollama_service import prewarm as ollama_prewarm, unload as ollama_unload
from app.services.scheduler import start_scheduler, stop_scheduler
from app.services.security import SecurityHeadersMiddleware, limiter

configure_logging()
sentry_enabled = configure_sentry()
log = structlog.get_logger("startup")


@asynccontextmanager
async def lifespan(_: FastAPI):
    log.info(
        "app.starting",
        environment=settings.environment,
        sentry=sentry_enabled,
        log_format=settings.log_format,
    )

    # Wire LangSmith env vars — SDK reads os.environ directly, not Pydantic settings
    if settings.langchain_tracing_v2:
        _ls_key = settings.langsmith_api_key.get_secret_value()
        if _ls_key:
            os.environ["LANGSMITH_API_KEY"] = _ls_key
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
            log.info("langsmith.enabled", project=settings.langsmith_project)

    await init_db()
    start_scheduler()
    # Fire the Ollama prewarm in the background so the first real user
    # turn doesn't pay the 30-90s cold-load cost. The app is fully
    # usable before this completes — Gemini is the primary path, Ollama
    # is just the fallback, and even if the prewarm fails the lazy
    # client call will still try.
    prewarm_task = asyncio.create_task(ollama_prewarm())

    # Download required NLTK corpora for ATS keyword extraction (no-op if already cached)
    import nltk
    for _nltk_pkg in ["punkt", "stopwords", "punkt_tab"]:
        try:
            nltk.download(_nltk_pkg, quiet=True)
        except Exception:
            pass

    # Pre-warm ML models in background (graceful — won't crash if unavailable)
    async def _prewarm_models() -> None:
        # SentenceTransformer for job ranking (all-MiniLM-L6-v2, ~22 MB)
        await asyncio.to_thread(
            lambda: __import__(
                "app.services.job_ranker", fromlist=["_model"]
            )._model()
        )
        # SentenceTransformer for ATS semantic scoring
        await asyncio.to_thread(
            lambda: __import__(
                "app.services.ats.semantic_scorer", fromlist=["get_model"]
            ).get_model()
        )
        # word2vec-google-news-300 for ATS keyword matching (~1.7 GB — slow cold load)
        await asyncio.to_thread(
            lambda: __import__(
                "app.services.ats.word_semantic", fromlist=["get_vectors"]
            ).get_vectors()
        )

    asyncio.create_task(_prewarm_models())

    # Initialize LangGraph interview agent with PostgreSQL checkpointer.
    # AsyncPostgresSaver.from_conn_string is an async context manager that opens
    # a dedicated psycopg connection (separate from the asyncpg pool).
    async with AsyncPostgresSaver.from_conn_string(str(settings.database_url)) as checkpointer:
        try:
            await ig.init_graph(checkpointer)
        except Exception as exc:
            log.warning("interview_graph.init_failed", error=str(exc))
            # Non-fatal — existing scripted interview still works

        log.info("app.ready", nudge_cron_hour=settings.nudge_cron_hour)
        yield

    log.info("app.stopping")
    if not prewarm_task.done():
        prewarm_task.cancel()
    await ollama_unload()
    await asyncio.to_thread(word2vec_unload)
    stop_scheduler()
    await close_db()
    log.info("app.stopped")


app = FastAPI(title="JobPilot API", version="0.1.0", lifespan=lifespan)
app.state.limiter = limiter

# Middleware order matters: outermost runs first on the way in, last on the way out.
# Security → Metrics → RequestContext → CORS → app.
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(metrics.PrometheusMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-Id", "X-Gamify"],
)

install_exception_handlers(app)


@app.exception_handler(RateLimitExceeded)
async def _rate_limit(_: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "type": "rate_limited",
            "title": "Too many requests",
            "detail": str(exc.detail) if hasattr(exc, "detail") else "Try again later.",
            "status": 429,
        },
    )


app.include_router(auth_router.router, prefix="/api/auth", tags=["Auth"])
app.include_router(
    applications_router.router, prefix="/api/applications", tags=["Applications"]
)
app.include_router(
    files_router.router, prefix="/api/applications", tags=["Files"]
)
app.include_router(
    referrals_router.router, prefix="/api/referrals", tags=["Referrals"]
)
app.include_router(
    nudges_router.router, prefix="/api/nudges", tags=["Nudges"]
)
app.include_router(
    drafts_router.router, prefix="/api/drafts", tags=["Drafts"]
)
app.include_router(
    dashboard_router.router, prefix="/api/dashboard", tags=["Dashboard"]
)
app.include_router(
    gamify_router.router, prefix="/api/gamify", tags=["Gamify"]
)
app.include_router(
    pilot_router.router, prefix="/api/pilot", tags=["Pilot"]
)
app.include_router(
    study_router.router, prefix="/api/study", tags=["Study"]
)
app.include_router(
    dsa_router.router, prefix="/api/dsa", tags=["DSA"]
)
app.include_router(
    analytics_router.router, prefix="/api/analytics", tags=["Analytics"]
)
app.include_router(
    settings_router.router, prefix="/api/settings", tags=["Settings"]
)
app.include_router(ats_router.router, prefix="/api/ats", tags=["ATS"])
app.include_router(interview_router.router, prefix="/api/interview", tags=["Interview"])
app.include_router(resumes_router.router, prefix="/api", tags=["Resumes"])
app.include_router(jobs_router.router, prefix="/api/jobs", tags=["jobs"])


@app.get("/healthz", tags=["Health"])
async def healthz() -> dict[str, bool]:
    return {"ok": True}


@app.get("/readyz", tags=["Health"])
async def readyz() -> dict[str, bool]:
    async with pool().acquire() as conn:
        await asyncio.wait_for(conn.fetchval("SELECT 1"), timeout=2.0)
    return {"ok": True}


@app.get("/metrics", include_in_schema=False)
async def prometheus_metrics() -> Response:
    if not settings.metrics_enabled:
        return Response(status_code=404)
    payload, content_type = metrics.render()
    return Response(content=payload, media_type=content_type)
