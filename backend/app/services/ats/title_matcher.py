"""Normalise and compare resume job titles against the JD target role."""
from __future__ import annotations
import re
from difflib import SequenceMatcher

_ABBR: list[tuple[str, str]] = [
    (r'\bsr\.?\b', 'senior'), (r'\bjr\.?\b', 'junior'),
    (r'\bmgr\.?\b', 'manager'), (r'\bswe\b', 'software engineer'),
    (r'\bsde\b', 'software development engineer'),
    (r'\bdev\b', 'developer'), (r'\barch\b', 'architect'),
]

_ROLE_SUFFIX = (
    r'(?:engineer|developer|architect|manager|lead|analyst|designer|'
    r'scientist|consultant|director|officer|specialist|administrator)'
)
_RESUME_TITLE_RE = re.compile(
    r'(?m)^[ \t]*([A-Z][A-Za-z /,\-]+' + _ROLE_SUFFIX + r')\s*(?:\||at|@|,|$)',
    re.IGNORECASE,
)
_JD_TITLE_RE = re.compile(
    r'^([A-Z][^\n]{3,70}' + _ROLE_SUFFIX + r')',
    re.MULTILINE | re.IGNORECASE,
)


def _normalise(title: str) -> str:
    t = title.lower().strip()
    for pat, rep in _ABBR:
        t = re.sub(pat, rep, t, flags=re.IGNORECASE)
    return t


def _sim(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalise(a), _normalise(b)).ratio()


def score_title_match(resume_text: str, jd_text: str) -> dict:
    """Score how well the candidate's most recent title matches the JD role."""
    jd_match = _JD_TITLE_RE.search(jd_text[:600])
    jd_title = jd_match.group(1).strip() if jd_match else None

    if not jd_title:
        return {
            "title_score": 80,
            "jd_title": None,
            "best_match": None,
            "match_ratio": None,
            "suggestions": [],
        }

    resume_titles = [m.group(1).strip() for m in _RESUME_TITLE_RE.finditer(resume_text)]

    if not resume_titles:
        return {
            "title_score": 40,
            "jd_title": jd_title,
            "best_match": None,
            "match_ratio": 0.0,
            "suggestions": [
                f"No clear job titles detected in your resume. "
                f"Make sure each role starts with your title on its own line."
            ],
        }

    best       = max(resume_titles, key=lambda t: _sim(t, jd_title))
    ratio      = _sim(best, jd_title)
    title_score = min(100, int(ratio * 110))

    suggestions: list[str] = []
    if ratio < 0.55:
        suggestions.append(
            f"Your title '{best}' differs from the target '{jd_title}'. "
            "Add a summary line that mirrors the JD title to improve ATS title matching."
        )

    return {
        "title_score": title_score,
        "jd_title": jd_title,
        "best_match": best,
        "match_ratio": round(ratio, 2),
        "suggestions": suggestions,
    }
