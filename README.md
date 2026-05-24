<div align="center">

# GitHired

**The complete job-search platform for developers.**

Track applications · Score your resume · Study with AI · Practice DSA · Mock interviews · Stay consistent with XP

[![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql)](https://www.postgresql.org/)

</div>

---

## What is GitHired?

Job hunting is more than sending applications. It's following up at the right time, asking for referrals before the window closes, studying consistently, and walking into interviews prepared. GitHired brings every part of that workflow into one place — with AI assistance at every step.

## Features

### 📋 Application Pipeline
Kanban board with four stages: **Applied → Screening → Interview → Offer / Rejected / Ghosted**. Attach your resume and JD per role, update stages by drag-and-drop, and get time-aware nudges when a role goes quiet for too long.

### 🤝 Referral Tracker
Four-stage referral pipeline: **Request Sent → Accepted → Message Sent → Replied → Referred / Dropped**. Track every warm intro so nothing falls through the cracks. One click drafts a personalized LinkedIn referral ask via Gemini.

### 🤖 AI Voice Agent — Pilot
Talk to Pilot by text or voice. Pilot reads your pipeline, surfaces your 3–5 highest-leverage actions for today, drafts follow-ups and referral messages on demand, and updates your tracker hands-free. Powered by Gemini + ElevenLabs TTS + Groq Whisper STT.

### 📚 AI Study Plan
Tell Pilot your target role and companies. It generates a structured revision tree — sections, subsections, and topics — tailored to that role. Mark each topic as done, in-progress, or mastered. Ask Pilot to fill gaps or explain any concept inline.

### 💻 DSA Practice + AI Code Review
Log every LeetCode / DSA problem you attempt. Paste your solution and get instant AI feedback: time and space complexity, approach critique, an optimized alternative, and a step-by-step dry run. Problems are organized by topic with a daily streak counter.

### 🎮 Gamification
Keep showing up every day with **XP & levels**, **daily quests**, **streak freeze tokens**, and **bronze-to-platinum achievements** (First Apply, Referral Machine, 7-day streak, and more). Every action — application, study session, follow-up, DSA solve — earns XP.

### 📄 ATS Resume Scorer (ML-powered)
Upload your resume PDF and paste any job description. GitHired's ML engine scores you across **8 dimensions** in seconds: keyword placement, semantic match (Word2Vec + MiniLM sentence embeddings), ontology coverage, experience fit, education, section completeness, and more. Get a colour-coded keyword gap report with placement suggestions.

### 🎤 AI Mock Interview
Full AI voice interview loop — pick a topic (HR Behavioral, System Design, JD-based, or any technology), choose difficulty (Easy / Medium / Hard), and set how many questions (3–15). The AI asks questions via TTS; you answer by voice; Groq Whisper transcribes your answer. After the session a background job evaluates every response and generates a **scored report** with:
- Per-question scores (0–10) with ideal answer examples
- Specific, actionable feedback on your answer
- Skill breakdown: Communication, Technical Depth, Problem Solving, Clarity
- Overall score (0–100) and a written summary

Past sessions are saved with soft-delete. You can review any report at any time.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.12 · FastAPI · asyncpg · Alembic · APScheduler |
| **Database** | PostgreSQL 16 |
| **AI — LLM** | Google Gemini 2.5 Flash (primary) · Ollama / llama3 (fallback) |
| **AI — Voice** | ElevenLabs TTS · Groq Whisper STT |
| **AI — ML (ATS)** | scikit-learn · Word2Vec · MiniLM sentence embeddings |
| **Frontend** | Next.js 14 App Router · TypeScript · Tailwind CSS · TanStack Query |
| **Auth** | Google OAuth 2.0 (via FastAPI + HTTP-only cookies) |

---

## Project Structure

```
GitHired/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── migrations/
│   │   ├── repositories/
│   │   ├── routers/
│   │   └── services/
│   ├── pyproject.toml
│   ├── alembic.ini
│   └── .env.example
└── frontend/
    ├── app/
    │   ├── page.tsx
    │   ├── dashboard/
    │   ├── applications/
    │   ├── referrals/
    │   ├── study/
    │   ├── dsa/
    │   ├── interview/
    │   ├── ats/
    │   └── settings/
    ├── components/
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
uv run alembic upgrade head  # apply all migrations

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

### 🤖 Gemini (LLM — study plans, AI chat, DSA review, interview evaluation)
Get your key from **[Google AI Studio](https://aistudio.google.com/)** → *Get API key*.
| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Your Gemini API key |
| `GEMINI_MODEL` | Default: `gemini-2.5-flash-lite` (free tier, ~1000 req/day) |

### 🦙 Ollama (local LLM fallback — optional)
[Install Ollama](https://ollama.com/download), then run `ollama pull qwen3.5:2b`. No API key needed.
| Variable | Description |
|---|---|
| `OLLAMA_BASE_URL` | Default: `http://localhost:11434` |
| `OLLAMA_MODEL` | Default: `qwen3.5:2b` |

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

### 🔐 Google OAuth (sign-in)
Go to **[Google Cloud Console](https://console.cloud.google.com/)** → *APIs & Services* → *Credentials* → *Create OAuth 2.0 Client ID*. Set authorized redirect URI to `http://localhost:8000/api/auth/google/callback`.
| Variable | Description |
|---|---|
| `GOOGLE_CLIENT_ID` | OAuth 2.0 Client ID |
| `GOOGLE_CLIENT_SECRET` | OAuth 2.0 Client Secret |
| `SESSION_SECRET` | Any long random string (e.g. run `openssl rand -hex 32`) |

### 📧 Resend (email digest — optional)
Get your key from **[Resend](https://resend.com/)** → *API Keys*. Leave blank to disable the digest feature.
| Variable | Description |
|---|---|
| `RESEND_API_KEY` | Your Resend API key |

---

## Contributing

This project is built and maintained by [Atharva Jamdar](https://github.com/Atharva1479). Issues and PRs are welcome — please open an issue first for any significant changes.
