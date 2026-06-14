"""Detect years-per-skill claims and match against JD experience requirements."""
from __future__ import annotations
import re as _re

_SKILL_YRS_RE = _re.compile(
    r'(\d+)\+?\s*(?:to\s*\d+\+?)?\s*years?\s*(?:of\s*)?(?:experience\s*(?:with|in|using)?\s*)?([A-Za-z][A-Za-z+#.\s]{1,25})',
    _re.IGNORECASE,
)
_ALT_RE = _re.compile(
    r'([A-Za-z][A-Za-z+#.\s]{1,25})\s*(?:for|over|across)\s*(\d+)\+?\s*years?',
    _re.IGNORECASE,
)
_JD_REQ_RE = _re.compile(
    r'(\d+)\+?\s*years?\s*(?:of\s*)?(?:experience\s*(?:with|in|using)?\s*)?([A-Za-z][A-Za-z+#.\s]{1,25})',
    _re.IGNORECASE,
)

_STOP = {"experience","work","development","engineering","software","technology","industry","field"}


def _clean(skill: str) -> str:
    return skill.strip().lower().rstrip("s, ")


def _skills_match(a: str, b: str) -> bool:
    """Word-boundary safe match — prevents 'java' matching inside 'javascript'."""
    return bool(
        _re.search(r'\b' + _re.escape(a) + r'\b', b) or
        _re.search(r'\b' + _re.escape(b) + r'\b', a)
    )


def _extract_skill_years(text: str, pattern: _re.Pattern) -> dict[str, int]:
    result: dict[str, int] = {}
    for m in pattern.finditer(text):
        yrs_str, skill_str = m.group(1), m.group(2)
        skill = _clean(skill_str)
        if skill and skill not in _STOP and len(skill) > 1:
            try:
                yrs = int(yrs_str)
                if 0 < yrs <= 30:
                    result[skill] = max(result.get(skill, 0), yrs)
            except ValueError:
                pass
    return result


def score_skill_experience(resume_text: str, jd_text: str) -> dict:
    resume_skill_yrs = _extract_skill_years(resume_text, _SKILL_YRS_RE)
    for m in _ALT_RE.finditer(resume_text):
        skill, yrs_str = _clean(m.group(1)), m.group(2)
        if skill and skill not in _STOP:
            try:
                resume_skill_yrs[skill] = max(resume_skill_yrs.get(skill, 0), int(yrs_str))
            except ValueError:
                pass

    jd_requirements = _extract_skill_years(jd_text, _JD_REQ_RE)

    if not jd_requirements:
        return {
            "skill_exp_score": 80,
            "resume_skill_years": resume_skill_yrs,
            "jd_requirements": {},
            "met": [],
            "unmet": [],
            "suggestions": [],
        }

    met, unmet = [], []
    for skill, required_yrs in jd_requirements.items():
        resume_yrs = 0
        for r_skill, r_yrs in resume_skill_yrs.items():
            if _skills_match(skill, r_skill):
                resume_yrs = max(resume_yrs, r_yrs)
        if resume_yrs >= required_yrs:
            met.append({"skill": skill, "required": required_yrs, "found": resume_yrs})
        else:
            unmet.append({"skill": skill, "required": required_yrs, "found": resume_yrs})

    total = len(jd_requirements)
    score = int(len(met) / total * 100) if total else 80

    suggestions: list[str] = []
    if unmet:
        examples = [f"{u['skill']} ({u['required']}+ yrs required, {u['found']} found)" for u in unmet[:3]]
        suggestions.append(
            f"Experience duration mismatch: {'; '.join(examples)}. "
            "Add explicit 'X years of [skill]' claims to your summary or experience bullets."
        )

    return {
        "skill_exp_score": score,
        "resume_skill_years": resume_skill_yrs,
        "jd_requirements": jd_requirements,
        "met": met,
        "unmet": unmet,
        "suggestions": suggestions,
    }
