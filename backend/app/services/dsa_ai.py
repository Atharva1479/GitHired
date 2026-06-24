"""DSA solution analysis via Gemini (Ollama fallback).

Single public entry point:
  analyze_solution(...) → dict with time_complexity, space_complexity,
                          approach_summary, feedback, optimized_solution, model

Uses response_mime_type='application/json' on Gemini for structured output.
Falls back to Ollama text mode with JSON extraction.
"""
from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import structlog

from app.config import settings
from app.services.gemini_service import GeminiUnavailable, _ensure_model
from app.services.ollama_service import OllamaUnavailable, chat as ollama_chat

log = structlog.get_logger("dsa_ai")

_JSON_SYSTEM = (
    "Output JSON ONLY — no markdown fences, no commentary, no explanation. "
    "Never wrap the JSON in ```."
)

_REQUIRED_KEYS = {
    "time_complexity",
    "space_complexity",
    "approach_summary",
    "feedback",
    "optimized_solution",
    "optimized_explanation",
    "dry_run_explanation",
}

_ANALYSIS_SCHEMA = {
    "time_complexity": "Big-O notation string, e.g. O(n log n)",
    "space_complexity": "Big-O notation string, e.g. O(n)",
    "approach_summary": "2-4 sentence description of what the user's algorithm does",
    "feedback": "Specific, constructive feedback on the user's solution — what's good, what could improve, edge cases missed",
    "optimized_solution": "A complete, clean, optimized solution in the same language as the user's solution (or Python if unclear)",
    "optimized_explanation": "Plain-English explanation of the optimized solution: the core technique/pattern used (e.g. two pointers, sliding window, monotonic stack), why it achieves better complexity, and the key insight that makes it work — 3 to 5 sentences",
    "dry_run_explanation": "Step-by-step trace of the optimized solution on a small concrete example input. Show variable names and their values at each iteration/recursive call so a beginner can follow exactly how the algorithm reaches the output.",
}


def _analysis_prompt(
    title: str,
    topic: str,
    description: str | None,
    user_solution: str,
) -> str:
    desc_block = f"\n\nProblem Description:\n{description}" if description else ""
    safe_solution = user_solution.replace("```", "'''")
    return f"""{_JSON_SYSTEM}

You are a senior software engineer and DSA expert reviewing a candidate's solution.

Problem: {title}
Topic / Category: {topic}{desc_block}

User's Solution:
```
{safe_solution}
```

Analyze the solution and respond with this exact JSON structure:
{json.dumps(_ANALYSIS_SCHEMA, indent=2)}

Rules:
- time_complexity and space_complexity must be Big-O strings
- approach_summary should describe the algorithm, not restate the code
- feedback must be specific and actionable, not generic
- optimized_solution must be a COMPLETE working solution, not pseudocode
- If the user's solution is already optimal, say so in feedback and provide a clean version
- dry_run_explanation: pick a small but non-trivial example (e.g. 4-6 elements), trace through the optimized solution step by step, label each step with the line/logic being executed and show variable states
"""


def _extract_json(text: str) -> dict[str, Any]:
    """Strip markdown fences and parse JSON from Ollama plain-text responses."""
    text = re.sub(r"```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON object found in response")
        return json.loads(text[start:end])


def _validate(result: dict[str, Any]) -> None:
    missing = _REQUIRED_KEYS - result.keys()
    if missing:
        raise ValueError(f"AI response missing required fields: {missing}")


async def _gemini_analyze(prompt: str) -> dict[str, Any]:
    import google.generativeai as genai

    model = _ensure_model()
    response = await asyncio.to_thread(
        model.generate_content,
        prompt,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            max_output_tokens=4096,
            temperature=0.2,
        ),
    )
    text = (getattr(response, "text", "") or "").strip()
    if not text:
        raise GeminiUnavailable("empty JSON response")
    result = _extract_json(text)
    _validate(result)
    result["model"] = "gemini"
    return result


async def _ollama_analyze(prompt: str) -> dict[str, Any]:
    raw = await ollama_chat(
        [{"role": "user", "content": prompt}],
        tools=None,
        temperature=0.2,
    )
    text = raw.get("message", {}).get("content", "")
    result = _extract_json(text)
    _validate(result)
    result["model"] = "ollama"
    return result


async def analyze_solution(
    title: str,
    topic: str,
    description: str | None,
    user_solution: str,
) -> dict[str, str]:
    """Analyze a user's DSA solution. Returns the five analysis fields plus 'model'."""
    prompt = _analysis_prompt(title, topic, description, user_solution)

    if settings.llm_provider in ("gemini", "auto"):
        try:
            result = await _gemini_analyze(prompt)
            log.info("dsa_ai.gemini_ok", title=title)
            return result
        except Exception as exc:  # noqa: BLE001
            log.warning("dsa_ai.gemini_failed", error=str(exc), fallback="ollama")
            if settings.llm_provider == "gemini":
                raise GeminiUnavailable(str(exc)) from exc

    try:
        result = await _ollama_analyze(prompt)
        log.info("dsa_ai.ollama_ok", title=title)
        return result
    except OllamaUnavailable as exc:
        log.error("dsa_ai.all_failed", error=str(exc))
        raise RuntimeError("AI analysis unavailable — both Gemini and Ollama failed") from exc
    except Exception as exc:  # noqa: BLE001
        log.error("dsa_ai.all_failed", error=str(exc))
        raise RuntimeError("AI analysis unavailable — both Gemini and Ollama failed") from exc
