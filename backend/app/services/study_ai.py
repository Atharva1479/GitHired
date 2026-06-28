"""M10 Phase 4 — AI study plan and topic generation.

Two public entry points:
  generate_plan(...)   → StudyGenerateResponse
  generate_topics(...) → StudyGenerateTopicsResponse

Both use Gemini with response_mime_type='application/json' for structured
output, then Pydantic-validate the result. On GeminiUnavailable the call
falls back to Ollama (text mode; JSON is extracted from the reply).

The caller (router) is responsible for persisting the preview and for
rate-limiting: plan generation is expensive (4096 output tokens) and is
capped at 1/day/user by the router; topic generation is capped at 30/day.
"""
from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import structlog

try:
    from langsmith import traceable as _traceable
except ImportError:
    def _traceable(**_kw):  # type: ignore[misc]
        def _wrap(fn):
            return fn
        return _wrap

from app.config import settings

_GENERATE_PLAN_V = "v1"
_GENERATE_TOPICS_V = "v1"
from app.models import (
    StudyAISectionPreview,
    StudyAISubsectionPreview,
    StudyAITopicPreview,
    StudyGenerateResponse,
    StudyGenerateTopicsResponse,
)
from app.services.gemini_service import GeminiUnavailable, _ensure_model
from app.services.ollama_service import OllamaUnavailable, chat as ollama_chat

log = structlog.get_logger("study_ai")


# ── Prompt builders ───────────────────────────────────────────────────

_JSON_SYSTEM = (
    "Output JSON ONLY — no markdown fences, no commentary, no explanation. "
    "Never wrap the JSON in ```."
)


def _san(text: str, max_len: int = 200) -> str:
    """Strip newlines and truncate user-controlled strings before prompt injection."""
    return text.replace("\n", " ").replace("\r", " ").strip()[:max_len]


def _plan_prompt(
    role: str,
    target_companies: list[str] | None,
    existing_sections: list[str] | None,
) -> str:
    safe_role = _san(role, 200)
    companies = (
        ", ".join(_san(c, 100) for c in target_companies) if target_companies else "general SWE roles"
    )
    existing = ", ".join(_san(s, 100) for s in existing_sections) if existing_sections else "none"
    return f"""{_JSON_SYSTEM}

You are a curriculum designer building a technical interview revision plan.

Engineer role: {safe_role}
Target companies: {companies}
Existing sections (do NOT duplicate): {existing}

Generate 4-7 sections. Each section has 3-6 subsections. Each subsection \
has 6-12 topics.
Topics must be specific enough to revise in a single 30-minute sitting.
Good: "Actuator endpoints in production" — Bad: "Spring stuff".
Each topic may have an optional "notes" field (3-6 comma-separated keywords).

Output schema (strict JSON):
{{
  "sections": [
    {{
      "name": "Backend",
      "subsections": [
        {{
          "name": "Spring Boot",
          "topics": [
            {{"title": "Dependency Injection", "notes": "scopes, qualifier, profile"}},
            {{"title": "Bean lifecycle"}}
          ]
        }}
      ]
    }}
  ]
}}"""


def _topics_prompt(
    section_name: str,
    subsection_name: str,
    count: int,
    hint: str | None,
) -> str:
    safe_hint = _san(hint, 300) if hint else None
    hint_line = f"\nUser hint: {safe_hint}" if safe_hint else ""
    return f"""{_JSON_SYSTEM}

You are a curriculum designer generating interview revision topics.

Section: {_san(section_name, 200)}
Subsection: {_san(subsection_name, 200)}{hint_line}

Generate exactly {count} specific, interview-relevant topics for this subsection.
Each topic may have an optional "notes" field (3-6 comma-separated keywords).

Output schema (strict JSON):
{{
  "topics": [
    {{"title": "...", "notes": "..."}},
    {{"title": "..."}}
  ]
}}"""


# ── JSON extraction ───────────────────────────────────────────────────


def _extract_json(text: str) -> Any:
    """Strip markdown fences and parse the first JSON object found."""
    text = re.sub(r"```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        raise


# ── Provider calls ────────────────────────────────────────────────────


async def _gemini_json(prompt: str) -> Any:
    import google.generativeai as genai

    model = _ensure_model()
    resp = await asyncio.to_thread(
        model.generate_content,
        prompt,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.7,
            max_output_tokens=4096,
        ),
    )
    text = (getattr(resp, "text", "") or "").strip()
    if not text:
        raise GeminiUnavailable("empty JSON response")
    return _extract_json(text)


async def _ollama_json(prompt: str) -> Any:
    result = await ollama_chat(
        [{"role": "user", "content": prompt}],
        tools=None,
        temperature=0.7,
    )
    text = result.get("message", {}).get("content", "")
    return _extract_json(text)


async def _call_with_fallback(prompt: str) -> Any:
    """Try Gemini, fall back to Ollama on failure."""
    if settings.llm_provider in ("gemini", "auto"):
        try:
            return await _gemini_json(prompt)
        except Exception as e:  # noqa: BLE001
            log.warning("study_ai.gemini_failed", error=str(e))
            if settings.llm_provider == "gemini":
                raise GeminiUnavailable(str(e)) from e

    try:
        return await _ollama_json(prompt)
    except OllamaUnavailable as e:
        raise ValueError("AI generation unavailable — try again later.") from e
    except Exception as e:  # noqa: BLE001
        log.warning("study_ai.ollama_failed", error=str(e))
        raise ValueError("AI returned an unexpected response — try again.") from e


# ── Public API ────────────────────────────────────────────────────────


@_traceable(name="study.generate_plan", run_type="llm", tags=[f"prompt_v:{_GENERATE_PLAN_V}"])
async def generate_plan(
    role: str,
    target_companies: list[str] | None = None,
    existing_sections: list[str] | None = None,
) -> StudyGenerateResponse:
    """Generate a full study plan preview. Pydantic-validated before returning."""
    prompt = _plan_prompt(role, target_companies, existing_sections)
    raw = await _call_with_fallback(prompt)

    try:
        sections_raw = raw.get("sections", []) if isinstance(raw, dict) else []
        sections = [
            StudyAISectionPreview(
                name=s["name"],
                subsections=[
                    StudyAISubsectionPreview(
                        name=sub["name"],
                        topics=[
                            StudyAITopicPreview(
                                title=t["title"],
                                notes=t.get("notes"),
                            )
                            for t in sub.get("topics", [])
                        ],
                    )
                    for sub in s.get("subsections", [])
                ],
            )
            for s in sections_raw
        ]
        return StudyGenerateResponse(sections=sections)
    except (KeyError, TypeError, ValueError) as e:
        log.warning("study_ai.plan_parse_error", error=str(e), raw=raw)
        raise ValueError("AI returned an unexpected format. Try again.") from e


@_traceable(name="study.generate_topics", run_type="llm", tags=[f"prompt_v:{_GENERATE_TOPICS_V}"])
async def generate_topics(
    section_name: str,
    subsection_name: str,
    count: int = 10,
    hint: str | None = None,
) -> StudyGenerateTopicsResponse:
    """Generate a topic list preview for one subsection."""
    prompt = _topics_prompt(section_name, subsection_name, count, hint)
    raw = await _call_with_fallback(prompt)

    try:
        topics_raw = (
            raw.get("topics", raw) if isinstance(raw, dict) else raw
        )
        topics = [
            StudyAITopicPreview(title=t["title"], notes=t.get("notes"))
            for t in topics_raw
            if isinstance(t, dict) and t.get("title")
        ]
        return StudyGenerateTopicsResponse(topics=topics)
    except (KeyError, TypeError, ValueError) as e:
        log.warning("study_ai.topics_parse_error", error=str(e), raw=raw)
        raise ValueError("AI returned an unexpected format. Try again.") from e
