"""Score the quality of the resume summary/objective section."""
from __future__ import annotations
import re

_SUMMARY_RE = re.compile(
    r'(?:summary|objective|profile|about me|professional summary|career objective|overview)'
    r'\s*\n([\s\S]{30,600}?)(?=\n[A-Z][A-Za-z\s]{1,30}\n|\Z)',
    re.IGNORECASE,
)
_YEAR_RE   = re.compile(r'\b(\d{1,2})\+?\s*years?\b', re.IGNORECASE)
_METRIC_RE = re.compile(r'\b\d+(?:\.\d+)?\s*(?:%|x|×|k|m|million|billion)\b|\$\s*\d+', re.IGNORECASE)


def _extract_summary(resume_text: str) -> str:
    m = _SUMMARY_RE.search(resume_text)
    if m:
        return m.group(1).strip()
    paras = [p.strip() for p in resume_text[:800].split('\n\n') if len(p.strip()) > 60]
    return paras[0] if paras else ""


def score_summary(resume_text: str, jd_text: str, required_keywords: list[str]) -> dict:
    summary = _extract_summary(resume_text)
    if not summary:
        return {
            "summary_score": 40,
            "summary_found": False,
            "keywords_in_summary": [],
            "has_years_claim": False,
            "has_metric": False,
            "summary_word_count": 0,
            "suggestions": [
                "No summary/objective section detected. Add a 2-3 sentence summary that "
                "mirrors the target role title and top 3-4 required keywords."
            ],
        }

    summary_lower = summary.lower()
    kw_in_summary = [k for k in required_keywords if k.lower() in summary_lower]
    kw_ratio = len(kw_in_summary) / max(len(required_keywords), 1)
    kw_score = min(100, int(kw_ratio * 150))

    has_years = bool(_YEAR_RE.search(summary))
    has_metric = bool(_METRIC_RE.search(summary))
    words = len(summary.split())
    length_score = 100 if 40 <= words <= 120 else max(0, 100 - abs(words - 80) * 2)

    combined = int(kw_score * 0.50 + length_score * 0.25 + (25 if has_years else 0) * 0.15 + (25 if has_metric else 0) * 0.10)

    suggestions: list[str] = []
    missing_in_summary = [k for k in required_keywords[:6] if k.lower() not in summary_lower]
    if missing_in_summary:
        suggestions.append(
            f"Summary doesn't mention key JD requirements: {', '.join(missing_in_summary[:3])}. "
            "Weave 2-3 top required keywords into your summary — ATS score it heavily."
        )
    if not has_years:
        suggestions.append("Add your years of experience to the summary (e.g. '5+ years of...').")
    if words < 30:
        suggestions.append("Summary is too short — aim for 50-100 words covering role, skills, and one achievement.")
    elif words > 150:
        suggestions.append("Summary exceeds 150 words — trim to 50-100 words for ATS and recruiter readability.")

    return {
        "summary_score": min(100, combined),
        "summary_found": True,
        "keywords_in_summary": kw_in_summary,
        "has_years_claim": has_years,
        "has_metric": has_metric,
        "summary_word_count": words,
        "suggestions": suggestions,
    }
