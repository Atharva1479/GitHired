"""Skill gap analyzer — compares resume against matched JDs using existing ATS infrastructure."""
from __future__ import annotations

import re

from app.services.ats.esco_loader import get_all_skills
from app.services.ats.jd_parser import parse_jd
from app.services.ats.keyword_extractor import extract_keywords


_STOP_ROLE_WORDS = {
    "developer", "engineer", "dev", "senior", "junior", "lead", "staff",
    "principal", "full", "stack", "backend", "frontend", "software",
    "and", "or", "the", "a", "an", "with",
}


def extract_role_keywords(role_tag: str) -> list[str]:
    """Extract significant keywords from a role tag for DB matching.

    'Java Developer' -> ['java']
    'Python FastAPI Developer' -> ['python', 'fastapi']
    'Agentic AI Developer' -> ['agentic', 'ai']
    """
    words = re.split(r"[\s/,|]+", role_tag.lower())
    return [w for w in words if w and w not in _STOP_ROLE_WORDS and len(w) > 1]


def analyze_gap(resume_text: str, jd_texts: list[str]) -> list[dict]:
    """Return ranked skill gaps: skills appearing in JDs but absent from resume.

    Each item: {"skill": str, "frequency": int, "total_jobs": int}
    Sorted by frequency descending.
    """
    if not jd_texts:
        return []

    get_all_skills()  # warm up ESCO loader cache
    resume_lower = resume_text.lower()

    skill_freq: dict[str, int] = {}
    for jd_text in jd_texts:
        parsed = parse_jd(jd_text)
        extracted = extract_keywords(parsed)
        seen_in_this_jd: set[str] = set()
        for skill in extracted["all_unique"]:
            seen_in_this_jd.add(skill.lower())
        for skill in seen_in_this_jd:
            skill_freq[skill] = skill_freq.get(skill, 0) + 1

    total = len(jd_texts)
    gaps = []
    for skill, freq in skill_freq.items():
        if skill.lower() not in resume_lower:
            gaps.append({"skill": skill, "frequency": freq, "total_jobs": total})

    gaps.sort(key=lambda x: x["frequency"], reverse=True)
    return gaps
