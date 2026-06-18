"""Semantic job ranking + resume auto-detection.

Uses sentence-transformers (all-MiniLM-L6-v2, 22MB, CPU-fast) to compute
cosine similarity between the user's resume and each job description.

Resume selection:
  - Option B (explicit): caller passes resume_id → that resume is used.
  - Option A (auto): query keywords are matched against role_tag on the
    resumes table (populated when user uploads a resume). Falls back to
    the most recently uploaded resume when no tag matches.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

import asyncpg
import numpy as np
import structlog

log = structlog.get_logger("job_ranker")

# ── Resume type → keyword buckets ─────────────────────────────────────────────
RESUME_BUCKETS: dict[str, set[str]] = {
    "java":   {
        "java", "spring", "spring boot", "kafka", "maven", "gradle",
        "hibernate", "jvm", "j2ee", "microservices", "junit", "jpa",
    },
    "python": {
        "python", "fastapi", "django", "flask", "asyncio", "pydantic",
        "celery", "sqlalchemy", "pytest", "uvicorn", "starlette", "pandas",
    },
    "ai": {
        "llm", "langchain", "langgraph", "agent", "ml", "machine learning",
        "pytorch", "tensorflow", "rag", "embedding", "openai", "huggingface",
        "fine-tuning", "diffusion", "ai", "nlp", "vector", "transformers",
        "generative", "llama", "mistral", "gemini",
    },
}


def detect_resume_type(query: str) -> str | None:
    """Return 'java' | 'python' | 'ai' | None based on query keywords."""
    q = query.lower()
    scores = {
        bucket: sum(1 for kw in keywords if kw in q)
        for bucket, keywords in RESUME_BUCKETS.items()
    }
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else None


async def pick_resume(
    conn: asyncpg.Connection,
    user_id: int,
    query: str,
    resume_id: int | None = None,
) -> tuple[str | None, str | None]:
    """Return (parsed_text, resume_name) for the best matching resume.

    Uses role_tag column on the resumes table to match auto-detected type.
    Falls back to the most recent resume when no tag matches.
    """
    rows = await conn.fetch(
        """
        SELECT id, name, role_tag, parsed_text
        FROM resumes
        WHERE user_id = $1 AND deleted_at IS NULL
        ORDER BY created_at DESC
        """,
        user_id,
    )
    if not rows:
        return None, None

    # Option B: explicit resume choice
    if resume_id is not None:
        for r in rows:
            if r["id"] == resume_id:
                return r["parsed_text"], r["name"]

    # Option A: auto-detect from query
    detected = detect_resume_type(query)
    if detected and len(rows) > 1:
        for r in rows:
            if (r["role_tag"] or "").lower() == detected:
                log.info("job_ranker.resume_auto_detected", detected=detected, resume=r["name"])
                return r["parsed_text"], r["name"]

    # Fallback: latest resume
    return rows[0]["parsed_text"], rows[0]["name"]


@lru_cache(maxsize=1)
def _model() -> Any:
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("all-MiniLM-L6-v2")


def rank_jobs_by_resume(
    jobs: list[dict[str, Any]],
    resume_text: str,
) -> list[dict[str, Any]]:
    """Compute semantic similarity and re-rank jobs by blended score.

    blended_score = 0.55 * freshness_score + 0.45 * semantic_score
    """
    if not resume_text or not jobs:
        return jobs

    try:
        model = _model()
        resume_emb = model.encode(resume_text[:2000], normalize_embeddings=True)
        job_texts = [
            f"{j.get('title', '')} {(j.get('description') or '')}"[:1000]
            for j in jobs
        ]
        job_embs = model.encode(job_texts, normalize_embeddings=True, batch_size=32)
        sims = (np.array(job_embs) @ np.array(resume_emb)).tolist()

        for job, sim in zip(jobs, sims):
            job["semantic_score"] = round(float(sim) * 100, 1)
            job["blended_score"] = (
                0.55 * job.get("freshness_score", 40)
                + 0.45 * (float(sim) * 100)
            )

        return sorted(jobs, key=lambda x: x.get("blended_score", 0), reverse=True)

    except Exception as exc:
        log.warning("job_ranker.rank_failed", error=str(exc))
        return jobs
