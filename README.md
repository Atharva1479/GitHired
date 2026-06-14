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
Discover jobs posted in the last 6–24 hours — before the competition piles up. Aggregates listings from **LinkedIn, Indeed, Naukri, and Glassdoor** via JSearch + Adzuna.

- **Freshness scoring** — 🔥 `<6h` · ⚡ `6–24h` · 🟡 `24–72h` · 🔴 `72h+` with estimated applicant counts
- **Velocity tracking** — shows if competition is growing fast since the job was first cached
- **Resume match %** — lazy-loads your ATS score (0–100) against each job's JD directly on the card
- **Keyword gap** — highlights skills in the JD that are missing from your resume
- **One-click Apply & Track** — opens the job in a new tab and auto-creates an application entry; JD text is saved, status set to Applied, duplicate applies blocked (HTTP 409)
- **JD preview panel** — right-side drawer with full job description, ATS scan button, and apply CTA
- **One-click ATS scan** — runs a full resume scan from the preview panel, stores result, navigates to `/ats/results`
- **Similar jobs** — after applying, shows 3 similar fresh roles (PostgreSQL full-text search on job title)
- **Saved searches** — save any query for daily email alerts via Resend
- **Filters** — freshness window, experience level, remote-only toggle, employment type (Full-time / Part-time / Contract / Internship)

### 📋 Application Pipeline
Kanban board with four stages: **Applied → Screening → Interview → Offer / Rejected / Ghosted**. Attach your resume and JD per role, update stages by drag-and-drop, and get time-aware nudges when a role goes quiet for too long.

### 🤝 Referral Tracker
Four-stage referral pipeline: **Request Sent → Accepted → Message Sent → Replied → Referred / Dropped**. Track every warm intro so nothing falls through the cracks. One click drafts a personalized LinkedIn referral ask via Gemini.

### 🤖 AI Voice Agent — Pilot
Talk to Pilot by text or voice. Pilot reads your pipeline, surfaces your 3–5 highest-leverage actions for today, drafts follow-ups and referral messages on demand, and updates your tracker hands-free. Powered by Gemini + ElevenLabs TTS + Groq Whisper STT.

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
| **AI — LLM** | Google Gemini 2.5 Flash · Ollama / llama3 (interview + DSA) |
| **AI — Voice** | ElevenLabs TTS · Groq Whisper STT |
| **AI — ML (ATS)** | scikit-learn · Word2Vec · MiniLM sentence embeddings |
| **Job APIs** | JSearch (RapidAPI) · Adzuna |
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
│   │   ├── migrations/
│   │   ├── repositories/       — interview.py (DB query layer)
│   │   ├── routers/            — auth, applications, jobs, interview, ats, resumes,
│   │   │                         dsa, study, referrals, pilot, gamify, nudges,
│   │   │                         drafts, dashboard, analytics, settings, files
│   │   └── services/           — job_search, interview_ai, skill_gap, pilot,
│   │                             jsearch_client, adzuna_client, email_service,
│   │                             tts, stt, ollama_service, gemini_service, gamify
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
    │   ├── jobs/               — JobCard, JobFilters, JobPreviewPanel, ApplyModal, SavedSearchPanel
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
- API keys (see [Environment Variables](#environment-variables) below)

### 1. Backend

```bash
cd backend
cp .env.example .env     # fill in your API keys

uv sync                  # install Python dependencies
uv run alembic upgrade head  # apply all migrations (0001–0026)

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

Copy `backend/.env.example` to `backend/.env` and fill in the following keys:

### 🗄️ Database
| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string — e.g. `postgresql://postgres:postgres@localhost:5432/githired` |

### 🤖 Gemini (LLM — study plans, AI chat, DSA review)
Get your key from **[Google AI Studio](https://aistudio.google.com/)** → *Get API key*.
| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Your Gemini API key |
| `GEMINI_MODEL` | Default: `gemini-2.5-flash-lite` (free tier, ~1000 req/day) |

### 🦙 Ollama (local LLM — interview questions + DSA evaluation)
[Install Ollama](https://ollama.com/download), then run `ollama pull llama3`. No API key needed.
| Variable | Description |
|---|---|
| `OLLAMA_BASE_URL` | Default: `http://localhost:11434` |
| `OLLAMA_MODEL` | Default: `llama3` |

### 🎙️ Groq (Speech-to-Text for voice agent & mock interviews)
Get your key from **[Groq Console](https://console.groq.com/)** → *API Keys* → *Create API Key*. Free tier is generous.
| Variable | Description |
|---|---|
| `GROQ_API_KEY` | Your Groq API key |

### 🔊 ElevenLabs (Text-to-Speech for voice agent & mock interviews)
Get your key from **[ElevenLabs](https://elevenlabs.io/)** → *Profile* → *API Key*. Free tier: 10k characters/month.
| Variable | Description |
|---|---|
| `ELEVENLABS_API_KEY` | Your ElevenLabs API key |
| `ELEVENLABS_VOICE_ID` | Default: `EXAVITQu4vr4xnSDxMaL` (Bella — free tier voice) |

### 🔍 Job APIs (Fresh Job Finder)
**JSearch** aggregates LinkedIn, Indeed, Naukri, Glassdoor. Free tier: 500 req/month.  
Get your key from **[RapidAPI — JSearch](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch)**.

**Adzuna** is a free job board API. Free tier: 250 req/day.  
Register at **[Adzuna Developer](https://developer.adzuna.com/)**.
| Variable | Description |
|---|---|
| `JSEARCH_API_KEY` | RapidAPI key with JSearch subscription |
| `ADZUNA_APP_ID` | Adzuna application ID |
| `ADZUNA_API_KEY` | Adzuna API key |

### 🔐 Google OAuth (sign-in)
Go to **[Google Cloud Console](https://console.cloud.google.com/)** → *APIs & Services* → *Credentials* → *Create OAuth 2.0 Client ID*. Set authorized redirect URI to `http://localhost:8000/api/auth/google/callback`.
| Variable | Description |
|---|---|
| `GOOGLE_CLIENT_ID` | OAuth 2.0 Client ID |
| `GOOGLE_CLIENT_SECRET` | OAuth 2.0 Client Secret |
| `SESSION_SECRET` | Any long random string (e.g. run `openssl rand -hex 32`) |

### 📧 Resend (email alerts for saved job searches — optional)
Get your key from **[Resend](https://resend.com/)** → *API Keys*. Leave blank to disable email alerts.
| Variable | Description |
|---|---|
| `RESEND_API_KEY` | Your Resend API key |

---

## Contributing

This project is built and maintained by [Atharva Jamdar](https://github.com/Atharva1479). Issues and PRs are welcome — please open an issue first for any significant changes.
