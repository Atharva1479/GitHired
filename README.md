<div align="center">

# GitHired

**The complete job-search platform for developers.**

Track applications · Discover fresh jobs · Score your resume · Study with AI · Practice DSA · Mock interviews · Stay consistent with XP

[![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql)](https://www.postgresql.org/)

</div>

---

## What is GitHired?

Job hunting is more than sending applications. It's finding postings before 100 people have already applied, following up at the right time, asking for referrals before the window closes, studying consistently, and walking into interviews prepared. GitHired brings every part of that workflow into one place — with AI assistance at every step.

## Features

### ⚡ Fresh Job Finder

Discover jobs posted in the last 6–24 hours — before the competition piles up. Aggregates listings from **8 sources in parallel**: JSearch (LinkedIn/Indeed/Glassdoor), Adzuna, Arbeitnow, Jooble (Naukri/LinkedIn India/Monster India), SerpAPI (Google Jobs), and remote-only boards (Remotive, RemoteOK, Jobicy, WeWorkRemotely).

- **Freshness scoring** — 🔥 `<6h` · ⚡ `6–24h` · 🟡 `24–72h` · 🔴 `72h+` with estimated applicant counts
- **Velocity tracking** — shows if competition is growing fast since the job was first cached
- **One-click Apply & Track** — opens the job in a new tab and auto-creates an application entry; JD saved, status set to Applied, duplicate applies blocked (HTTP 409)
- **JD preview panel** — right-side drawer with full job description, ATS scan button, and apply CTA
- **One-click ATS scan** — runs a full resume scan from the preview panel, stores result, navigates to `/ats/results`
- **Similar jobs** — after applying, shows 3 similar fresh roles (PostgreSQL full-text search on job title)
- **Saved searches + alert badge** — save any query; red badge shows new jobs since last alert
- **Load-more pagination** — shows 24 cards at a time; load next 24 on demand (no re-fetch)
- **Search state persistence** — sessionStorage restores your last search on back navigation
- **Filters** — freshness window, experience level, remote-only toggle, employment type

**Performance:**
- Cache hit (fresh): `<10ms`
- Tier-1 early return (≥10 jobs from JSearch+Adzuna): `~5–6s`
- Full fetch (all 8 sources): `≤12s` guaranteed
- Stale-While-Revalidate: serve from cache instantly, refresh in background after 3h

### 📋 Application Pipeline
Kanban board with four stages: **Applied → Screening → Interview → Offer / Rejected / Ghosted**. Attach your resume and JD per role, update stages by drag-and-drop, and get time-aware nudges when a role goes quiet for too long.

### 🤝 Referral Tracker
Four-stage referral pipeline: **Request Sent → Accepted → Message Sent → Replied → Referred / Dropped**. Track every warm intro so nothing falls through the cracks. One click drafts a personalized LinkedIn referral ask via Gemini.

### 🤖 AI Voice Agent — Pilot
Talk to Pilot by text or voice. Pilot reads your pipeline, surfaces your 3–5 highest-leverage actions for today, drafts follow-ups and referral messages on demand, and updates your tracker hands-free. Powered by Gemini + ElevenLabs TTS + Groq Whisper STT. Wake word: "Hey Jarvis".

### 📄 ATS Resume Scorer (ML-powered)
Upload your resume PDF and paste any job description. GitHired's ML engine scores you across **8 dimensions** in seconds: keyword placement, semantic match (Word2Vec + MiniLM sentence embeddings), ontology coverage, experience fit, education, section completeness, and more. Get a colour-coded keyword gap report with placement suggestions. Also reused inline on job cards and the job preview panel.

### 🎤 AI Mock Interview
Full AI voice interview loop — pick a topic (Technical DSA, HR Behavioral, System Design, or JD-based), set your experience level, and choose a 30 or 60 minute session. The AI generates tailored questions via Ollama, reads them aloud via ElevenLabs TTS, and Groq Whisper transcribes your spoken answers. After the session, a background job evaluates every response and generates a **scored report** with:
- Per-question scores (0–10) with ideal answer examples
- Specific, actionable feedback on your answer
- Skill breakdown: Communication, Technical Depth, Problem Solving, Clarity
- Overall score (0–100) and a written performance summary

Past sessions are saved. Reports are accessible at any time from the Interview History page.

### 📚 AI Study Plan
Tell Pilot your target role and companies. It generates a structured revision tree — sections, subsections, and topics — tailored to that role. Mark each topic as done, in-progress, or mastered. Ask Pilot to fill gaps or explain any concept inline.

### 💻 DSA Practice + AI Code Review
Log every LeetCode / DSA problem you attempt. Paste your solution and get instant AI feedback: time and space complexity, approach critique, an optimized alternative, and a step-by-step dry run. Problems are organized by topic with a daily streak counter.

### 🎮 Gamification
Keep showing up every day with **XP & levels**, **daily quests**, **streak freeze tokens**, and **bronze-to-platinum achievements** (First Apply, Referral Machine, 7-day streak, and more). Every action — application, study session, follow-up, DSA solve, completed interview — earns XP.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.12 · FastAPI · asyncpg · Alembic · APScheduler |
| **Database** | PostgreSQL 16 |
| **AI — LLM** | Google Gemini 2.5 Flash · Ollama / qwen3.5:2b (interview + DSA) |
| **AI — Voice** | ElevenLabs TTS · Groq Whisper STT |
| **AI — ML (ATS)** | scikit-learn · Word2Vec · MiniLM sentence embeddings |
| **Job APIs** | JSearch (RapidAPI) · Adzuna · Arbeitnow · Jooble · SerpAPI Google Jobs · Remotive · RemoteOK · Jobicy · WeWorkRemotely |
| **Frontend** | Next.js 14 App Router · TypeScript · Tailwind CSS · TanStack Query v5 |
| **Auth** | Google OAuth 2.0 (via FastAPI + HTTP-only cookies) |
| **Email** | Resend |

---

## Project Structure

```
GitHired/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── models.py
│   │   ├── migrations/versions/    — 0001–0030 (0030 = job_search_cache)
│   │   ├── repositories/           — interview.py, jobs.py (DB query layer)
│   │   ├── routers/                — auth, applications, jobs, interview, ats,
│   │   │                             resumes, dsa, study, referrals, pilot,
│   │   │                             gamify, nudges, drafts, dashboard,
│   │   │                             analytics, settings, files
│   │   └── services/
│   │       ├── job_search.py       — fan-out orchestrator (tiered, circuit-broken)
│   │       ├── circuit_breaker.py  — per-source circuit breaker (CLOSED/OPEN/HALF_OPEN)
│   │       ├── jsearch_client.py   — JSearch / RapidAPI
│   │       ├── adzuna_client.py    — Adzuna
│   │       ├── arbeitnow_client.py — Arbeitnow (global, keyword-filtered)
│   │       ├── jooble_client.py    — Jooble (Naukri, LinkedIn India, Monster India)
│   │       ├── serpapi_client.py   — SerpAPI Google Jobs
│   │       ├── remotive_client.py  — Remotive (remote only)
│   │       ├── remoteok_client.py  — RemoteOK (remote only)
│   │       ├── jobicy_client.py    — Jobicy (remote only)
│   │       ├── weworkremotely_client.py
│   │       ├── interview_ai.py
│   │       ├── skill_gap.py
│   │       ├── pilot.py
│   │       └── ...
│   ├── pyproject.toml
│   ├── alembic.ini
│   └── .env.example
└── frontend/
    ├── app/
    │   ├── dashboard/
    │   ├── applications/
    │   ├── jobs/               — Fresh job finder
    │   ├── interview/          — Setup, session (full-screen), report/[id], history
    │   ├── ats/                — Scorer + results
    │   ├── resumes/
    │   ├── dsa/
    │   ├── study/
    │   ├── referrals/
    │   ├── analytics/
    │   ├── achievements/
    │   ├── nudges/
    │   └── settings/
    ├── components/
    │   ├── jobs/               — JobCard, JobFilters, JobPreviewPanel,
    │   │                         ApplyModal, SavedSearchPanel
    │   ├── interview/          — SetupForm, SessionView, ReportView, InterviewOrb
    │   ├── ats/                — ScoreGauge, CategoryBreakdown, KeywordAnalysis, TailorPanel
    │   └── ...
    ├── hooks/
    └── lib/
```

---

## Quickstart

### Prerequisites
- Python 3.12+ with [uv](https://docs.astral.sh/uv/)
- Node.js 20+
- PostgreSQL 16 running locally
- Ollama running locally (`ollama pull qwen3.5:2b`)
- API keys (see [Environment Variables](#environment-variables) below)

### 1. Backend

```bash
cd backend
cp .env.example .env     # fill in your API keys

uv sync                       # install Python dependencies
uv run alembic upgrade head   # apply all migrations (0001–0030)

uv run uvicorn app.main:app --reload
# → http://localhost:8000/docs
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

> Set `NEXT_PUBLIC_API_URL=http://localhost:8000/api` in `frontend/.env.local`

### Common backend commands

| Task | Command (run from `backend/`) |
|---|---|
| Install deps | `uv sync` |
| Dev server | `uv run uvicorn app.main:app --reload` |
| Run tests | `uv run pytest` |
| Apply migrations | `uv run alembic upgrade head` |
| New migration | `uv run alembic revision -m "describe change"` |
| Lint | `uv run ruff check .` |

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in the following.

**Required** keys are needed for the app to start. **Optional** keys unlock specific features — the app works without them (those features are silently disabled).

---

### 🗄️ Database (Required)

| Variable | Example | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/githired` | asyncpg-compatible PostgreSQL DSN |

---

### 🔐 Auth (Required)

**Session secret** — generate with `openssl rand -hex 32`:

| Variable | Description |
|---|---|
| `SESSION_SECRET` | Long random string for HTTP-only session cookie signing |

**Google OAuth** — go to [Google Cloud Console](https://console.cloud.google.com/) → *APIs & Services* → *Credentials* → *Create OAuth 2.0 Client ID*. Set authorized redirect URI to `http://localhost:8000/api/auth/google/callback`.

| Variable | Description |
|---|---|
| `GOOGLE_CLIENT_ID` | OAuth 2.0 Client ID |
| `GOOGLE_CLIENT_SECRET` | OAuth 2.0 Client Secret |

---

### 🤖 AI — LLM (Required for AI features)

**Gemini** — get your key from [Google AI Studio](https://aistudio.google.com/) → *Get API key*. Free tier: ~1000 req/day on `gemini-2.5-flash-lite`.

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | — | Your Gemini API key |
| `GEMINI_MODEL` | `gemini-2.5-flash-lite` | Override to `gemini-2.5-flash` for higher quality |

**Ollama** — [install Ollama](https://ollama.com/download) locally, then `ollama pull qwen3.5:2b`. No API key needed.

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `qwen3.5:2b` | Model tag — any Ollama model with tool-calling support |

---

### 🎙️ Voice (Optional — needed for voice agent and mock interviews)

**Groq** (Speech-to-Text) — get your key from [Groq Console](https://console.groq.com/) → *API Keys* → *Create API Key*. Generous free tier.

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | — | Your Groq API key |
| `GROQ_STT_MODEL` | `whisper-large-v3` | Whisper model for transcription |

**ElevenLabs** (Text-to-Speech) — get your key from [ElevenLabs](https://elevenlabs.io/) → *Profile* → *API Key*. Free tier: 10k characters/month.

| Variable | Default | Description |
|---|---|---|
| `ELEVENLABS_API_KEY` | — | Your ElevenLabs API key |
| `ELEVENLABS_VOICE_ID` | `EXAVITQu4vr4xnSDxMaL` | Voice ID — default is "Bella" (free tier) |

---

### 🔍 Job Discovery APIs

All job API keys are **optional**. The app works without them — sources with missing keys are silently skipped. Add whichever you have for more/better results.

#### JSearch — LinkedIn, Indeed, Glassdoor (500 req/month free)
1. Go to [RapidAPI — JSearch](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch)
2. Click **Subscribe to Test** → select the free plan
3. Copy your RapidAPI key from the dashboard

| Variable | Description |
|---|---|
| `JSEARCH_API_KEY` | RapidAPI key with JSearch subscription |

#### Adzuna — Global job board (250 req/day free)
1. Go to [developer.adzuna.com](https://developer.adzuna.com/) → *Register*
2. Create an application — you get an App ID and API key immediately

| Variable | Description |
|---|---|
| `ADZUNA_APP_ID` | Adzuna application ID |
| `ADZUNA_API_KEY` | Adzuna API key |

#### Jooble — Naukri, LinkedIn India, Monster India, TimesJobs, Shine (500 req/day free)

Best free source for **Indian job boards**. Aggregates Naukri, LinkedIn India, Monster India, TimesJobs, Shine, and Foundit.

1. Go to [jooble.org/api/about](https://jooble.org/api/about)
2. Fill the short registration form — API key is emailed immediately
3. No credit card required

| Variable | Description |
|---|---|
| `JOOBLE_API_KEY` | Your Jooble API key |

#### SerpAPI — Google Jobs (100 searches/month free)

Highest quality India results — indexes **Naukri, LinkedIn India, Indeed India, Glassdoor** via Google's real-time crawl. Best freshness of all free options.

1. Go to [serpapi.com](https://serpapi.com/) → *Sign Up*
2. Free plan gives 100 searches/month — no credit card for free tier
3. Copy your API key from the dashboard

| Variable | Description |
|---|---|
| `SERPAPI_API_KEY` | Your SerpAPI key |

> **India job coverage summary:**
> | Source | Covers | Free limit |
> |---|---|---|
> | JSearch | LinkedIn, Indeed, Glassdoor | 500 req/month |
> | Adzuna | Direct employer + Adzuna India | 250 req/day |
> | Jooble | Naukri, LinkedIn IN, Monster IN, TimesJobs, Shine | 500 req/day |
> | SerpAPI | All boards via Google (best freshness) | 100 req/month |
> | Arbeitnow | Global/EU boards (keyword-filtered) | Unlimited |

---

### 📧 Email Alerts (Optional)

**Resend** — used for daily saved-search job alerts. Leave blank to disable.

1. Go to [resend.com](https://resend.com/) → *API Keys* → *Create API Key*
2. Free tier: 3000 emails/month, 100/day

| Variable | Default | Description |
|---|---|---|
| `RESEND_API_KEY` | — | Your Resend API key |
| `DIGEST_ENABLED` | `false` | Set to `true` once key is configured |

---

### 🔬 Observability (Optional)

**LangSmith** — LangChain tracing for the Pilot AI agent.

| Variable | Default | Description |
|---|---|---|
| `LANGSMITH_API_KEY` | — | From [smith.langchain.com](https://smith.langchain.com/) |
| `LANGCHAIN_TRACING_V2` | `false` | Set to `true` to enable tracing |
| `LANGSMITH_PROJECT` | `githired-interview` | Project name in LangSmith |

---

## Job Search Architecture

The job search uses a **tiered fan-out** pattern with circuit breakers and stale-while-revalidate caching:

```
Request hits /api/jobs/search
       │
       ├─ 1. Exact-key cache hit? ──── YES → return in <10ms
       │      (age > 3h?)                    + background refresh if stale
       │
       ├─ 2. FTS warm cache (≥15 rows)? ─ YES → return from job_cache
       │
       └─ 3. Live fan-out (all parallel, circuit-broken, timeouts):
              │
              ├── TIER 1 (timeout 6s) ─── JSearch, Adzuna ×2
              │       ↓ ≥10 jobs within 6s?
              │   YES → return immediately, Tier 2 finishes in background
              │   NO  → wait for Tier 2
              │
              └── TIER 2 (timeout 10s) ── Arbeitnow, ATS boards,
                                          SmartRecruiters, Jooble, SerpAPI
                                          + remote boards (if remote_only=True)

Total guaranteed response time: ≤ 12s
Circuit breaker: 5 failures → OPEN (skip source) → 60s → HALF_OPEN → test
```

---

## Contributing

This project is built and maintained by [Atharva Jamdar](https://github.com/Atharva1479). Issues and PRs are welcome — please open an issue first for any significant changes.
