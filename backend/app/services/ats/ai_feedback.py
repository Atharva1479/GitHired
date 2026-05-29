"""ATS resume AI feedback via Ollama (Gemini fallback).

Generates human-readable strengths, suggestions, and weaknesses
based on the structured ATS analysis result.
"""
from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import structlog

from app.services.gemini_service import GeminiUnavailable, _ensure_model
from app.services.ollama_service import OllamaUnavailable, chat as ollama_chat

log = structlog.get_logger("ats_ai_feedback")

_JSON_SYSTEM = (
    "Output JSON ONLY — no markdown fences, no commentary, no explanation. "
    "Never wrap the JSON in ```."
)

_REQUIRED_KEYS = {"strengths", "suggestions", "weaknesses"}


def _build_prompt(data: dict[str, Any]) -> str:
    required_missing = ", ".join(data.get("required_missing", [])) or "None"
    preferred_missing = ", ".join(data.get("preferred_missing", [])) or "None"
    sections_found = ", ".join(data.get("sections_found", [])) or "None"
    sections_missing = ", ".join(data.get("sections_missing", [])) or "None"
    ats_risks = "; ".join(data.get("ats_risks", [])) or "None"
    existing_suggestions = "; ".join(data.get("suggestions", [])) or "None"

    return f"""{_JSON_SYSTEM}

You are an expert resume coach and ATS specialist. Based on the ATS analysis below, give concise, specific, actionable feedback that will help this candidate improve their resume for this specific job.

ATS Analysis:
- Overall Score: {data.get("overall_score", 0)}/100
- Required Keywords Missing: {required_missing}
- Preferred Keywords Missing: {preferred_missing}
- Resume Sections Found: {sections_found}
- Resume Sections Missing: {sections_missing}
- ATS Risks: {ats_risks}
- Existing Improvement Notes: {existing_suggestions}

Respond with this exact JSON:
{{
  "strengths": ["<specific strength based on analysis>", "..."],
  "suggestions": ["<concrete action to improve score>", "..."],
  "weaknesses": ["<critical issue hurting ATS score>", "..."]
}}

Rules:
- strengths: 2-3 items. What this resume does well. Be specific.
- suggestions: 3-4 items. One actionable step per bullet. Max 20 words each. Name the section to edit (e.g. "Add X to your Skills section"). Do NOT list more than 2 keywords per bullet — refer to skill categories instead (e.g. "cloud technologies" not a long list).
- weaknesses: 1-2 items. The single most critical gap. Max 20 words each.
- NEVER write a comma-separated list of more than 3 keywords in any bullet.
- NEVER use phrases like "such as X, Y, Z, A, B, C...".
- Each bullet is one short sentence. No sub-clauses, no parentheses.
- If required_missing is "None" and score >= 80, emphasize the positives.
"""


def _extract_json(text: str) -> dict[str, Any]:
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


async def _gemini_feedback(prompt: str) -> dict[str, Any]:
    import google.generativeai as genai

    model = _ensure_model()
    response = await asyncio.to_thread(
        model.generate_content,
        prompt,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            max_output_tokens=1024,
            temperature=0.3,
        ),
    )
    text = (getattr(response, "text", "") or "").strip()
    if not text:
        raise GeminiUnavailable("empty response")
    result = _extract_json(text)
    _validate(result)
    return result


async def _ollama_feedback(prompt: str) -> dict[str, Any]:
    # Simpler prompt for Ollama — smaller models struggle with long complex prompts
    score = 0
    try:
        import re as _re
        m = _re.search(r'Overall Score: (\d+)', prompt)
        score = int(m.group(1)) if m else 0
        req_m = _re.search(r'Required Keywords Missing: (.+)', prompt)
        req_missing = req_m.group(1).strip() if req_m else "None"
    except Exception:
        req_missing = "None"

    simple_prompt = (
        f"Output JSON only. No markdown. First character must be {{.\n\n"
        f"Resume ATS score: {score}/100. Required keywords missing: {req_missing}.\n\n"
        f'Return exactly: {{"strengths": ["strength 1", "strength 2"], '
        f'"weaknesses": ["weakness 1"], '
        f'"suggestions": ["action 1", "action 2", "action 3"]}}'
    )
    raw = await ollama_chat(
        [{"role": "user", "content": simple_prompt}],
        tools=None,
        temperature=0.2,
    )
    content = raw.get("message", {}).get("content", "")
    if not content:
        raise OllamaUnavailable("empty response")
    result = _extract_json(content)
    _validate(result)
    return result


async def generate_ats_feedback(data: dict[str, Any]) -> dict[str, Any]:
    """Generate AI strengths/suggestions/weaknesses for an ATS result.

    Tries Gemini first, falls back to Ollama, falls back to a static
    summary derived from the analysis data so the UI always gets a response.
    """
    prompt = _build_prompt(data)
    try:
        return await _gemini_feedback(prompt)
    except Exception as e:
        log.warning("ats_feedback.gemini_failed", error=str(e))

    try:
        result = await _ollama_feedback(prompt)
        log.info("ats_feedback.ollama_ok")
        return result
    except Exception as e:
        log.warning("ats_feedback.ollama_failed", error=str(e))

    # Static fallback derived from analysis data
    strengths: list[str] = []
    weaknesses: list[str] = []
    suggestions: list[str] = []

    score = data.get("overall_score", 0)
    if score >= 70:
        strengths.append("Your resume matches many of the key requirements for this role.")
    found = data.get("sections_found", [])
    if found:
        strengths.append(f"Strong resume structure with sections: {', '.join(found[:4])}.")

    req_missing = data.get("required_missing", [])
    pref_missing = data.get("preferred_missing", [])
    if req_missing:
        weaknesses.append(f"Missing required keywords: {', '.join(req_missing[:5])}.")
        suggestions.append(f"Add these required keywords to your resume: {', '.join(req_missing[:5])}.")
    if pref_missing:
        suggestions.append(f"Consider adding preferred skills: {', '.join(pref_missing[:4])}.")
    for risk in data.get("ats_risks", [])[:2]:
        weaknesses.append(risk)
    for s in data.get("suggestions", [])[:3]:
        suggestions.append(s)

    if not strengths:
        strengths = ["Resume text was successfully parsed by ATS."]
    if not suggestions:
        suggestions = ["Review the missing keywords and add them to the relevant sections."]
    if not weaknesses:
        weaknesses = ["No critical ATS issues detected."]

    return {"strengths": strengths, "suggestions": suggestions, "weaknesses": weaknesses}
