"""AI service for interview question generation, turn evaluation, and report generation.

Tries Gemini first (fast, cloud), falls back to Ollama (local).
Three public entry points:
  generate_questions(...)  → list[str]
  evaluate_turn(...)       → dict with ideal_answer, score, feedback
  generate_report(...)     → dict with overall_score, skill_breakdown, summary
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

log = structlog.get_logger("interview_ai")

# Named interview style categories — everything else is treated as a tech/custom topic.
_STYLE_CATEGORIES = {"HR Behavioral", "System Design", "JD Based", "Technical Interview"}

# Skill axes for named styles. Tech/custom topics get dynamic axes inferred from questions.
_SKILL_AXES: dict[str, list[str]] = {
    "HR Behavioral": [
        "Communication",
        "STAR Structure",
        "Self-Awareness",
        "Emotional Intelligence",
    ],
    "Technical Interview": [
        "Technical Knowledge",
        "Problem Solving",
        "Communication",
        "Clarity",
    ],
    "System Design": [
        "Scalability Thinking",
        "Trade-off Analysis",
        "Architecture Knowledge",
        "Communication",
    ],
}


def _extract_json(text: str) -> Any:
    text = re.sub(r"```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        arr_start = text.find("[")
        obj_start = text.find("{")
        if arr_start != -1 and (obj_start == -1 or arr_start < obj_start):
            end = text.rfind("]") + 1
            return json.loads(text[arr_start:end])
        elif obj_start != -1:
            end = text.rfind("}") + 1
            return json.loads(text[obj_start:end])
        raise ValueError("No JSON found in response")


async def _gemini(prompt: str, max_tokens: int = 1024) -> Any:
    import google.generativeai as genai

    model = _ensure_model()
    response = await asyncio.to_thread(
        model.generate_content,
        prompt,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            max_output_tokens=max_tokens,
            temperature=0.3,
        ),
    )
    text = (getattr(response, "text", "") or "").strip()
    if not text:
        raise GeminiUnavailable("empty response")
    return _extract_json(text)


async def _ollama(prompt: str, temperature: float = 0.3) -> Any:
    raw = await ollama_chat(
        [{"role": "user", "content": prompt}],
        tools=None,
        temperature=temperature,
    )
    content = raw.get("message", {}).get("content", "")
    if not content:
        raise OllamaUnavailable("empty response")
    return _extract_json(content)


async def _call(prompt: str, max_tokens: int = 1024, temperature: float = 0.3) -> Any:
    """Try Gemini first, fall back to Ollama based on LLM_PROVIDER setting."""
    if settings.llm_provider in ("gemini", "auto"):
        try:
            return await _gemini(prompt, max_tokens)
        except Exception as exc:
            log.warning("interview_ai.gemini_failed", error=str(exc))
            if settings.llm_provider == "gemini":
                raise

    return await _ollama(prompt, temperature)


# ─── Public functions ──────────────────────────────────────────────────────────

_DIFFICULTY_CONTEXT = {
    "easy": (
        "Focus on foundational concepts, standard definitions, and common everyday use cases. "
        "Suitable for candidates with limited hands-on experience. Avoid edge cases or advanced internals."
    ),
    "medium": (
        "Cover real-world applied knowledge — practical scenarios, design decisions, debugging situations, "
        "and trade-off reasoning. Expect candidates to demonstrate solid hands-on experience."
    ),
    "hard": (
        "Probe deep expertise — internal implementation details, performance bottlenecks, subtle edge cases, "
        "large-scale architecture decisions, and production-level reasoning. "
        "Questions should challenge even senior engineers."
    ),
}


async def generate_questions(
    topic: str,
    role: str,
    years_exp: str,
    num_questions: int = 7,
    difficulty: str = "medium",
    jd_text: str | None = None,
) -> list[str]:
    count = max(1, min(20, num_questions))
    difficulty_guidance = _DIFFICULTY_CONTEXT.get(difficulty, _DIFFICULTY_CONTEXT["medium"])

    is_style = topic in _STYLE_CATEGORIES

    if is_style:
        style_instructions: dict[str, str] = {
            "HR Behavioral": """\
- Ask behavioral questions using STAR-eliciting phrasing ("Tell me about a time when...", "Describe a situation where...").
- Cover: teamwork, conflict resolution, leadership, failure & learning, time management under pressure, giving/receiving feedback.
- NEVER ask technical or coding questions.""",

            "Technical Interview": """\
- Ask verbal technical questions only — CS fundamentals, language concepts, debugging approaches, tooling trade-offs.
- Cover: OOP/design principles, memory & concurrency concepts, REST/API design, code quality, testing philosophy.
- NEVER ask the candidate to write, trace, or produce code. All questions must be answerable by speaking.""",

            "System Design": """\
- Ask open-ended architecture questions that require reasoning through real-world design decisions.
- Cover: load balancing, database selection, caching strategies, API contracts, fault tolerance, consistency vs availability.
- Progress from a single service to full distributed system scope.""",

            "JD Based": f"""\
- Derive every question directly from the skills, tools, and responsibilities in the job description below.
- Prioritize the most prominent requirements. Mix technical competency checks with situational/behavioral questions.
- Do not ask questions that could apply to any generic job.

<job_description>
{(jd_text or "")[:2000]}
</job_description>""",
        }
        instructions = style_instructions.get(topic, "- Ask relevant, progressively challenging questions.")
        interview_context = f"{topic} interview for a {role} with {years_exp} years of experience"
    else:
        # Custom or tech-specific topic (e.g. Java, Spring Boot, FastAPI, Gen AI)
        instructions = f"""\
- This is a technical interview focused specifically on: {topic}
- Generate questions actually asked in real {topic} interviews at companies like Google, Amazon, Microsoft, Flipkart, etc.
- Cover a mix of: core concepts, common real-world pitfalls, best practices, architectural decisions, and debugging scenarios.
- Questions should reveal depth of hands-on experience — not just "what is X" but "how/why/when would you use X?"
- NEVER ask the candidate to write code. All questions must be answerable verbally.
- Examples of good question styles:
    "How does X work internally and what are its performance implications?"
    "When would you choose X over Y, and what trade-offs does that involve?"
    "Walk me through how you would debug [common problem in this technology]."
    "What are the most common mistakes developers make with X?"
"""
        interview_context = f"{topic} technical interview for a {role} with {years_exp} years of experience"

    prompt = f"""Output JSON ONLY — a single JSON array of strings. No markdown, no commentary.

You are a senior technical interviewer preparing a {interview_context}.

<difficulty>
Level: {difficulty.upper()}
{difficulty_guidance}
</difficulty>

<task>
Generate exactly {count} interview questions calibrated to the {difficulty} difficulty level above.
</task>

<guidelines>
{instructions}
- Questions must progress in complexity, all staying within the {difficulty} difficulty band.
- Each question must be one complete, clear sentence.
- All questions must be distinct — no repetition of concepts or phrasing.
</guidelines>

Return format (JSON array only): ["question 1", "question 2", ..., "question {count}"]"""

    result = await _call(prompt, max_tokens=1000, temperature=0.6)
    if not isinstance(result, list):
        raise ValueError(f"Expected list, got {type(result)}")
    return [str(q) for q in result[:count]]


async def evaluate_turn(
    topic: str,
    role: str,
    question: str,
    user_answer: str,
) -> dict[str, Any]:
    prompt = f"""Output JSON ONLY. No markdown, no commentary.

You are an expert interviewer evaluating a candidate response in a {topic} interview for a {role} role.

<question>
{question}
</question>

<candidate_answer>
{user_answer if user_answer.strip() else "[No answer provided]"}
</candidate_answer>

<task>
Evaluate the response and return this exact JSON structure:
{{
  "ideal_answer": "<3-5 sentences written in first person as if a strong candidate is speaking. Be concrete and specific — name real approaches, tools, or examples. Never describe what a good answer should contain; write the actual answer itself.>",
  "score": <integer 0-10>,
  "feedback": "<2-3 sentences of specific, actionable feedback referencing what the candidate actually said. Be constructive and direct.>"
}}
</task>

<scoring_rubric>
0-2: No answer, completely off-topic, or factually wrong
3-4: Shows awareness but lacks structure, specifics, or key points
5-6: Adequate — covers the basics but lacks depth or precision
7-8: Good answer with only minor gaps or imprecision
9-10: Excellent — complete, well-structured, insightful
</scoring_rubric>"""

    try:
        result = await _call(prompt, max_tokens=600, temperature=0.3)
        return {
            "ideal_answer": str(result.get("ideal_answer", "")),
            "score": max(0, min(10, int(result.get("score", 5)))),
            "feedback": str(result.get("feedback", "")),
        }
    except Exception as exc:
        log.error("interview_ai.evaluate_turn_failed", error=str(exc))
        return {"ideal_answer": "", "score": 0, "feedback": "AI evaluation failed."}


async def generate_report(
    topic: str,
    role: str,
    question_evals: list[dict[str, Any]],
) -> dict[str, Any]:
    if not question_evals:
        return {
            "overall_score": 0,
            "skill_breakdown": {},
            "summary": "No answers were recorded for this session.",
        }

    avg_score = sum(e["score"] for e in question_evals) / len(question_evals)
    overall_score = max(0, min(100, round(avg_score * 10)))

    evals_text = "\n".join(
        f"Q{i + 1}: {e['question']}\nScore: {e['score']}/10\nFeedback: {e['feedback']}"
        for i, e in enumerate(question_evals)
    )

    fixed_axes = _SKILL_AXES.get(topic)

    if fixed_axes:
        axes_schema = ", ".join(f'"{k}": <integer 0-100>' for k in fixed_axes)
        axes_instruction = f"""\
Rate each of these skill dimensions based on the candidate's overall performance.
Use exactly these keys in "skill_breakdown": {{{axes_schema}}}"""
    else:
        # Tech/custom topic or JD Based — infer relevant axes from what the questions actually tested
        axes_instruction = f"""\
The interview was on the topic: "{topic}". Based on the specific questions asked and the candidate's answers,
identify exactly 4 skill dimensions that were meaningfully tested (e.g. specific sub-areas of {topic}, or competencies like debugging, architecture, best practices).
Name each dimension concisely (2-4 words). Rate each 0-100 based on the candidate's actual performance.
Use this schema for "skill_breakdown": {{"<skill 1>": <0-100>, "<skill 2>": <0-100>, "<skill 3>": <0-100>, "<skill 4>": <0-100>}}"""

    prompt = f"""Output JSON ONLY. No markdown, no commentary.

You are generating a performance report for a {topic} mock interview for a {role} candidate.

<interview_results>
Overall Score: {overall_score}/100

{evals_text}
</interview_results>

<task>
{axes_instruction}

Also write a "summary" of 3-5 sentences covering: overall performance level, the candidate's strongest area, and the most important area to improve.

Return this exact JSON:
{{
  "skill_breakdown": {{...}},
  "summary": "<3-5 sentences>"
}}
</task>"""

    try:
        result = await _call(prompt, max_tokens=600, temperature=0.3)
        return {
            "overall_score": overall_score,
            "skill_breakdown": result.get("skill_breakdown", {}),
            "summary": str(result.get("summary", "")),
        }
    except Exception as exc:
        log.error("interview_ai.generate_report_failed", error=str(exc))
        return {
            "overall_score": overall_score,
            "skill_breakdown": {},
            "summary": "AI report generation failed. Score is calculated from individual answers.",
        }
