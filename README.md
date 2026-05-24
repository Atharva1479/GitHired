<div align="center">

# GitHired

**The complete job-search platform for developers.**

Track applications · Score your resume · Study with AI · Practice DSA · Mock interviews · Stay consistent with XP

[![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

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
job-tracker/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── models.py
│   │   ├── migrations/
│   │   ├── repositories/
│   │   │   ├── applications.py
│   │   │   ├── referrals.py
│   │   │   ├── study.py
│   │   │   ├── dsa.py
│   │   │   ├── interview.py
│   │   │   └── ...
│   │   ├── routers/
│   │   │   ├── applications.py
│   │   │   ├── referrals.py
│   │   │   ├── study.py
│   │   │   ├── dsa.py
│   │   │   ├── interview.py
│   │   │   ├── pilot.py
│   │   │   ├── ats.py
│   │   │   └── ...
│   │   └── services/
│   │       ├── gemini_service.py
│   │       ├── ollama_service.py
│   │       ├── interview_ai.py
│   │       ├── dsa_ai.py
│   │       ├── nudge_engine.py
│   │       └── ...
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── alembic.ini
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── .env.example
└── frontend/
    ├── app/
    │   ├── page.tsx            (landing page)
    │   ├── dashboard/
    │   ├── applications/
    │   ├── referrals/
    │   ├── study/
    │   ├── dsa/
    │   ├── interview/
    │   │   ├── page.tsx        (setup)
    │   │   ├── session/page.tsx
    │   │   ├── report/[id]/
    │   │   └── history/page.tsx
    │   ├── ats/
    │   └── settings/
    ├── components/
    │   ├── layout/
    │   ├── interview/
    │   └── ...
    ├── hooks/
    └── lib/
```

---

## Quickstart

### Prerequisites
- Python 3.12+ with [uv](https://docs.astral.sh/uv/)
- Node.js 20+
- PostgreSQL 16
- API keys: `GEMINI_API_KEY`, `ELEVENLABS_API_KEY`, `GROQ_API_KEY`

### 1. Backend

```bash
cd backend
cp .env.example .env        # fill in your API keys and DATABASE_URL

docker compose up -d db     # start Postgres
uv run alembic upgrade head  # apply all migrations

uv run uvicorn app.main:app --reload
# → http://localhost:8000/docs
```

### 2. Frontend

```bash
cd frontend
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL=http://localhost:8000/api

npm install
npm run dev
# → http://localhost:3000
```

### Common backend commands

| Task | Command (run from `backend/`) |
|---|---|
| Install deps | `uv sync` |
| Dev server | `uv run uvicorn app.main:app --reload` |
| Run tests | `uv run pytest` |
| Apply migrations | `uv run alembic upgrade head` |
| New migration | `uv run alembic revision -m "describe change"` |
| Lint | `uv run ruff check .` |
| Type-check | `uv run mypy` |

---

## API Overview

| Prefix | Description |
|---|---|
| `POST /api/auth/google` | Google OAuth sign-in |
| `GET/POST /api/applications` | Application pipeline CRUD |
| `GET/POST /api/referrals` | Referral pipeline CRUD |
| `GET/POST /api/study` | Study plan generation and progress |
| `GET/POST /api/dsa` | DSA problem log + AI review |
| `POST /api/interview/sessions` | Start AI mock interview session |
| `POST /api/interview/sessions/{id}/turns` | Submit one Q&A turn |
| `POST /api/interview/sessions/{id}/end` | End session + trigger report |
| `GET /api/interview/sessions/{id}/report` | Poll report (202 pending → 200 ready) |
| `GET /api/interview/history` | List past sessions |
| `POST /api/pilot/chat` | Pilot AI chat (text) |
| `POST /api/pilot/tts` | Text-to-speech (ElevenLabs) |
| `POST /api/pilot/stt` | Speech-to-text (Groq Whisper) |
| `POST /api/ats/score` | ATS resume scoring (ML) |
| `GET /api/gamification/profile` | XP, level, achievements |

---

## Contributing

This project is built and maintained by [Atharva Jamdar](https://github.com/AtharvaJamdar). Issues and PRs are welcome — please open an issue first for any significant changes.

## License

MIT — see [LICENSE](LICENSE).
