"""Resume bullet-point rewriting via AI.

Given a resume text, a job description, and the missing ATS keywords, the AI
identifies 3-6 existing bullets that are strong candidates for enhancement and
rewrites them to naturally incorporate the missing keywords — without
hallucinating experience that isn't implied by the original text.

Provider chain: Gemini -> Ollama -> static keyword-aware templates.
Follows the same pattern as services/ats/ai_feedback.py.
"""
from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import structlog

from app.services.gemini_service import GeminiUnavailable, _ensure_model
from app.services.ollama_service import OllamaUnavailable, chat as ollama_chat

log = structlog.get_logger("ats.resume_tailor")

_JSON_FENCE = (
    "Output JSON ONLY. No markdown fences, no preamble, no explanation. "
    "The very first character of your response must be `[`."
)

_PLACEMENT_RULES = """\
ATS KEYWORD PLACEMENT RULES (non-negotiable):
- Keywords in the first 8 words of a bullet receive the highest positional ATS weight.
- Required keywords outweigh preferred 3:1 — always fill required_missing first.
- Use the EXACT form written in the JD (e.g. "FastAPI" not "Fast API", "CI/CD" not "CICD").
- Each keyword appears at most ONCE per bullet — no stuffing.
- Best insertion patterns: "Built X using [kw]", "[kw]-based X", "leveraging [kw]",
  "with [kw] orchestration", "via [kw] pipelines", "on [kw]"."""

_QUALITY_GATES = """\
QUALITY GATES — a rewrite FAILS if any of these are true:
  [FAIL] Changes the action verb (keep "Built", "Designed", "Led", "Reduced", etc.)
  [FAIL] Alters, removes, or invents any quantitative metric ("40% faster", "3M users")
  [FAIL] Makes the candidate appear more senior or junior than the original implies
  [FAIL] Adds a technology that the original bullet does NOT imply
         Example: original "Analyzed sales data" => do NOT add "Python" or "ML" — hallucination
  [FAIL] Exceeds 30 words (ATS systems truncate long bullets)
  [FAIL] Reads unnaturally or jams keywords side-by-side ("Python FastAPI Docker Kubernetes REST")
  [FAIL] Re-adds a keyword already present in the original bullet
  [FAIL] The "original" field is not verbatim from the resume text"""

_FEW_SHOT = """\
EXAMPLES — study these before generating:

[GOOD] Adding a framework and database:
  original:  "Built REST APIs for the mobile app backend serving 500K daily users"
  missing:   ["FastAPI", "PostgreSQL"]
  rewritten: "Built FastAPI REST APIs for the mobile backend, backed by PostgreSQL, serving 500K daily users"
  added:     ["FastAPI", "PostgreSQL"]
  Why good:  Action verb unchanged, metric unchanged, keywords placed naturally, 19 words.

[GOOD] Adding a methodology:
  original:  "Led a team of 4 engineers to deliver payment integration on time"
  missing:   ["Agile", "Scrum"]
  rewritten: "Led a team of 4 engineers in Agile/Scrum sprints to deliver payment integration on schedule"
  added:     ["Agile", "Scrum"]
  Why good:  Both keywords fit, "on schedule" is an acceptable synonym of "on time".

[GOOD] Adding cloud + container tools:
  original:  "Deployed containerized microservices with automated CI/CD pipelines"
  missing:   ["AWS", "Docker", "Kubernetes"]
  rewritten: "Deployed Docker-containerized microservices to AWS ECS with Kubernetes orchestration and CI/CD automation"
  added:     ["AWS", "Docker", "Kubernetes"]
  Why good:  All 3 keywords inserted naturally, still under 30 words.

[BAD] Hallucination — never do this:
  original:  "Analyzed customer data to identify business trends"
  missing:   ["Python", "Machine Learning", "TensorFlow"]
  bad:       "Analyzed customer data using Python, Machine Learning, and TensorFlow to identify AI-powered trends"
  Why bad:   Original gives zero signal the candidate used these tools. Skip this bullet.

[BAD] Metric tampering — never change numbers:
  original:  "Optimized database queries, reducing load time by 40%"
  missing:   ["Redis", "PostgreSQL"]
  bad:       "Optimized PostgreSQL queries with Redis caching, reducing load time by 65%"
  correct:   "Optimized PostgreSQL queries with Redis caching, reducing load time by 40%"

[BAD] Keyword stuffing — max 2 per bullet:
  original:  "Built authentication service for the platform"
  missing:   ["OAuth2", "JWT", "Python", "FastAPI"]
  bad:       "Built OAuth2 JWT Python FastAPI authentication service for the platform"
  correct:   "Built OAuth2/JWT authentication service in FastAPI for the platform"  (pick 2 max)"""

_SELECTION_STRATEGY = """\
SELECTION STRATEGY:
1. Scan ALL sections of the resume for improvable content:
   - Experience: action bullets with strong verbs — best candidates
   - Projects: technical project descriptions — excellent for adding stack keywords
   - Summary/Profile: 2-3 line intro — good for adding role-level or methodology keywords
   - Skills: if listed as prose (not a comma list), rewrite to include missing skills naturally
   - Certifications/Education: only if the missing keyword is a certification or degree type
2. For each required missing keyword, find the ONE line/bullet across ANY section that most
   plausibly relates to it. Match by domain:
   "deployed services" -> Docker/Kubernetes/AWS in Experience or Projects;
   "analytical skills" -> Summary; unlisted framework -> Skills section.
3. Prefer technically-rich bullets in Experience/Projects — they have the most room.
   Fall back to Summary or Skills only when Experience/Projects have no plausible match.
4. If a line cannot accept a keyword without hallucination, skip it entirely.
5. Never include the same original line twice.
6. Target 3-6 rewrites across all sections. Fewer high-quality rewrites beat many weak ones."""


def _build_prompt(
    resume_text: str,
    jd_text: str,
    required_missing: list[str],
    preferred_missing: list[str],
) -> str:
    tier1 = required_missing[:12]
    tier2 = preferred_missing[:8]

    tier1_str = ", ".join(f'"{k}"' for k in tier1) if tier1 else "None"
    tier2_str = ", ".join(f'"{k}"' for k in tier2) if tier2 else "None"

    resume_block = resume_text[:4000].strip()
    jd_block = jd_text[:1500].strip()

    return f"""{_JSON_FENCE}

You are a senior technical recruiter and Certified Professional Resume Writer (CPRW) \
with 15 years of FAANG hiring experience. You have reviewed 50,000+ resumes and know \
exactly which bullet-point rewrites pass ATS screening AND impress human reviewers.

Your task: rewrite specific resume bullets to incorporate missing ATS keywords. \
Never hallucinate — only add keywords that the original bullet plausibly implies.

RESUME TEXT:
{resume_block}

JOB DESCRIPTION (for context):
{jd_block}

MISSING REQUIRED KEYWORDS (highest priority — fill these first):
{tier1_str}

MISSING PREFERRED KEYWORDS (add only when a bullet has natural room):
{tier2_str}

{_PLACEMENT_RULES}

{_QUALITY_GATES}

{_FEW_SHOT}

{_SELECTION_STRATEGY}

OUTPUT — a JSON array, first character must be `[`:
[
  {{
    "section": "<actual section name: Experience | Projects | Summary | Skills | Certifications | Education>",
    "original": "<verbatim line copied from the resume above — must be an exact substring>",
    "rewritten": "<improved line with keywords woven in naturally>",
    "keywords_added": ["keyword1"],
    "rationale": "<one sentence: why this line across any section and how the keyword fits naturally>"
  }}
]

If no line across any section can be honestly improved, return: []
"""


def _extract_json(text: str) -> list[dict[str, Any]]:
    text = re.sub(r"```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```", "", text).strip()
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("[")
        end = text.rfind("]") + 1
        if start == -1 or end == 0:
            return []
        try:
            result = json.loads(text[start:end])
        except json.JSONDecodeError:
            return []
    return result if isinstance(result, list) else []


def _validate(item: Any) -> bool:
    if not isinstance(item, dict):
        return False
    if not {"section", "original", "rewritten", "keywords_added"}.issubset(item.keys()):
        return False
    if not isinstance(item["keywords_added"], list):
        return False
    if item["original"].strip() == item["rewritten"].strip():
        return False
    return True


def _static_fallback(
    required_missing: list[str],
    preferred_missing: list[str],
) -> list[dict[str, Any]]:
    """Keyword-aware template suggestions when both AI providers are offline."""
    _cloud = {"AWS", "GCP", "Azure", "EC2", "S3", "Lambda", "GKE", "ECS"}
    _container = {"Docker", "Kubernetes", "K8s", "Helm", "Podman"}
    _db = {"PostgreSQL", "MySQL", "MongoDB", "Redis", "DynamoDB", "Cassandra", "SQL"}
    _lang = {"Python", "Go", "Rust", "TypeScript", "JavaScript", "Java", "Kotlin", "Scala"}
    _framework = {"FastAPI", "Django", "Flask", "React", "Next.js", "Node.js", "Spring"}
    _method = {"Agile", "Scrum", "Kanban", "TDD", "CI/CD", "DevOps", "MLOps"}

    def _bucket(kw: str) -> tuple[str, str]:
        if kw in _cloud:       return "cloud platform",    "Experience or Projects"
        if kw in _container:   return "container tech",    "Experience or Projects"
        if kw in _db:          return "database",          "Experience or Skills"
        if kw in _lang:        return "language",          "Skills or Experience"
        if kw in _framework:   return "framework",         "Experience or Skills"
        if kw in _method:      return "methodology",       "Summary or Experience"
        return                        "technology",         "Experience or Skills"

    all_missing = (
        [(k, "required") for k in required_missing[:4]] +
        [(k, "preferred") for k in preferred_missing[:2]]
    )
    suggestions = []
    for kw, tier in all_missing:
        bucket, section_hint = _bucket(kw)
        suggestions.append({
            "section": section_hint.split(" or ")[0],
            "original": f"[Find your most relevant {section_hint} line related to {bucket}]",
            "rewritten": (
                f"[Add '{kw}' to that line naturally — e.g. 'built X using {kw}', "
                f"'deployed X on {kw}', or 'with {kw} integration']"
            ),
            "keywords_added": [kw],
            "rationale": (
                f"'{kw}' is a {'required' if tier == 'required' else 'preferred'} "
                f"keyword missing from your resume. Adding it to a {bucket} line in "
                f"{section_hint} will improve your ATS keyword match score."
            ),
        })
    return suggestions


async def _gemini_tailor(prompt: str) -> list[dict[str, Any]]:
    import google.generativeai as genai
    model = _ensure_model()
    response = await asyncio.to_thread(
        model.generate_content,
        prompt,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            max_output_tokens=2048,
            temperature=0.35,
            top_p=0.85,
        ),
    )
    text = (getattr(response, "text", "") or "").strip()
    if not text:
        raise GeminiUnavailable("empty response")
    items = _extract_json(text)
    return [i for i in items if _validate(i)]


async def _ollama_tailor(prompt: str) -> list[dict[str, Any]]:
    raw = await ollama_chat(
        [{"role": "user", "content": prompt}],
        tools=None,
        temperature=0.35,
    )
    content = raw.get("message", {}).get("content", "")
    if not content:
        raise OllamaUnavailable("empty response")
    items = _extract_json(content)
    return [i for i in items if _validate(i)]


async def generate_tailor_suggestions(
    resume_text: str,
    jd_text: str,
    required_missing: list[str],
    preferred_missing: list[str],
) -> list[dict[str, Any]]:
    """Rewrite resume bullets to incorporate missing ATS keywords.

    Returns validated {section, original, rewritten, keywords_added, rationale} dicts.
    Provider chain: Gemini -> Ollama -> keyword-aware static templates.
    """
    prompt = _build_prompt(resume_text, jd_text, required_missing, preferred_missing)

    try:
        result = await _gemini_tailor(prompt)
        if result:
            log.info("ats.tailor.gemini_ok", count=len(result))
            return result
    except Exception as e:
        log.warning("ats.tailor.gemini_failed", error=str(e)[:200])

    try:
        result = await _ollama_tailor(prompt)
        if result:
            log.info("ats.tailor.ollama_ok", count=len(result))
            return result
    except Exception as e:
        log.warning("ats.tailor.ollama_failed", error=str(e)[:200])

    log.warning("ats.tailor.using_static_fallback")
    return _static_fallback(required_missing, preferred_missing)
