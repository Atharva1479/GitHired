from pathlib import Path

from pydantic import PostgresDsn, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="forbid")

    database_url: PostgresDsn
    gemini_api_key: SecretStr
    # NOTE on default model choice (2026-05):
    # - `gemini-2.5-flash` free tier: ~20 RPM, ~200 req/day per project
    # - `gemini-2.5-flash-lite` free tier: ~30 RPM, ~1000 req/day
    # The agent burns 2-4 calls per voice turn (initial → tool → final),
    # so flash daily cap is hit in ~50 turns. Lite gives us 5x headroom
    # with the same tool-calling support and marginally lower latency.
    # Override via GEMINI_MODEL=... in .env if you have a paid project.
    gemini_model: str = "gemini-2.5-flash-lite"
    nudge_cron_hour: int = 9
    drafts_per_user_per_day: int = 50
    cors_origins: list[str] = ["http://localhost:3000"]
    log_level: str = "INFO"
    upload_dir: Path = Path("data/uploads")
    max_upload_bytes: int = 10 * 1024 * 1024  # 10 MB
    google_client_id: str = ""
    google_client_secret: SecretStr = SecretStr("")
    session_secret: SecretStr = SecretStr("dev-only-change-me-please-rotate")  # override in non-dev envs
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    cookie_secure: bool = False
    session_max_age_days: int = 30

    # Observability (M7)
    environment: str = "development"  # development | staging | production
    log_format: str = "console"  # console | json
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.1
    metrics_enabled: bool = True
    auth_rate_limit_per_minute: int = 10
    redis_url: str | None = None  # e.g. "redis://redis:6379/0" — enables distributed rate limiting

    # Pilot — voice AI co-pilot (M8 Phase 3)
    pilot_enabled: bool = True
    pilot_rate_limit_per_minute: int = 20
    groq_api_key: SecretStr = SecretStr("")
    groq_stt_model: str = "whisper-large-v3"
    elevenlabs_api_key: SecretStr = SecretStr("")
    elevenlabs_voice_id: str = "EXAVITQu4vr4xnSDxMaL"  # "Bella" — warm friendly default
    elevenlabs_model: str = "eleven_turbo_v2_5"

    # LLM provider routing (M9 follow-up)
    # `gemini`  — always use Gemini; surface quota errors to the user
    # `ollama`  — always use a local Ollama model
    # `auto`    — try Gemini first; on quota/auth/unavailable errors,
    #             automatically retry the same turn via Ollama so the
    #             agent keeps working when the free-tier cap dies.
    llm_provider: str = "auto"
    ollama_base_url: str = "http://localhost:11434"
    # Default to qwen3.5:2b — 2.7GB, 256K context, native tool calling.
    # Swap to llama3.2:3b, qwen2.5:3b, or any other Ollama tag without
    # touching code; the client posts whatever name is set here.
    ollama_model: str = "qwen3.5:2b"
    # 300s covers a cold model load for heavy Q8 quantizations (2.7GB+
    # models can take 90-180s on CPU-only machines). Once warm, calls
    # return in under a second. We also pre-warm at startup.
    # Override via OLLAMA_TIMEOUT_SECONDS=... in .env if needed.
    ollama_timeout_seconds: float = 300.0
    # Pre-warm the model in the background at backend startup so the
    # first real user request doesn't pay the cold-load cost. Disable
    # with OLLAMA_PREWARM=false if you don't want a load on boot.
    ollama_prewarm: bool = True
    # When true, we pass our tool schemas to Ollama and run the
    # tool-calling agent loop. When false, we skip tools entirely —
    # the model just text-answers from the persona without DB access.
    # Set to false if your Ollama model is small/unreliable at tool
    # calling (e.g., gemma2:2b has no native tool support, qwen3.5:2b
    # can be flaky). The agent loses data-lookup capability but
    # becomes much more reliable for empathy / general advice replies.
    ollama_use_tools: bool = True
    # How long to keep the model in RAM after the last request.
    # Accepts Ollama time strings: "60m", "1h", "30m", "0" (unload immediately).
    # Override via OLLAMA_KEEP_ALIVE=... in .env
    ollama_keep_alive: str = "60m"

    # Weekly email digest (via Resend)
    resend_api_key: SecretStr = SecretStr("")
    resend_from_email: str = "JobPilot <digest@jobpilot.app>"
    digest_enabled: bool = False   # flip to True once RESEND_API_KEY is set

    # ── LangChain / LangSmith observability ──────────────────────────────────
    # Set LANGSMITH_API_KEY + LANGCHAIN_TRACING_V2=true to enable tracing.
    # Free tier covers thousands of traces/month. Leave blank to disable.
    langsmith_api_key: SecretStr = SecretStr("")
    langsmith_project: str = "githired-interview"
    langchain_tracing_v2: bool = False

    # ── Interview AI (LangGraph agent) ────────────────────────────────────────
    interview_llm_provider: str = "gemini"   # gemini | groq | auto
    groq_interview_model: str = "llama-3.3-70b-versatile"

    # ── Job Discovery ─────────────────────────────────────────────────────────
    # JSearch on RapidAPI: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
    jsearch_api_key: SecretStr | None = None

    # Adzuna free job API: https://developer.adzuna.com/
    adzuna_app_id: str | None = None
    adzuna_api_key: SecretStr | None = None

    # Jooble job aggregator: https://jooble.org/api/about
    # Aggregates from Naukri, LinkedIn India, Monster India, TimesJobs, Shine, Foundit.
    # Free tier: 500 requests/day.
    jooble_api_key: SecretStr | None = None

    # SerpAPI Google Jobs: https://serpapi.com/
    # Covers LinkedIn India, Naukri, Indeed India, Glassdoor — near real-time freshness.
    # Free tier: 100 searches/month.
    serpapi_api_key: SecretStr | None = None

    # Cache TTL: how long (hours) to keep job results in the DB before re-fetching
    job_cache_ttl_hours: int = 4

    # UTC hour for the daily job-alert email (default 8 = 8 AM UTC = 1:30 PM IST)
    job_alert_cron_hour: int = 8

    @model_validator(mode="after")
    def _production_secret_guard(self) -> "Settings":
        if (
            self.environment != "development"
            and self.session_secret.get_secret_value() == "dev-only-change-me-please-rotate"
        ):
            raise ValueError(
                "SESSION_SECRET must be changed from the default value in non-development environments. "
                "Set SESSION_SECRET to a long random string in your environment or .env file."
            )
        return self


settings = Settings()
