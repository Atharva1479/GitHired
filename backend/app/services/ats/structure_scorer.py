"""Score resume structure: length, section ordering, bullet type diversity."""
from __future__ import annotations
import re

EXPECTED_ORDER = ["contact","summary","objective","profile","experience","work","education","skills","certifications","projects"]

_SECTION_HDR_RE = re.compile(r'(?m)^[ \t]*([A-Z][A-Za-z\s]{1,30})[ \t]*$')
_BULLET_TYPE_RE = re.compile(r'(?m)^\s*([•\-–—*▸○◦▪])\s')
_WORD_RE = re.compile(r'\b\w+\b')


def _estimate_pages(text: str) -> float:
    words = len(_WORD_RE.findall(text))
    return words / 350


def _detect_sections(text: str) -> list[str]:
    headers = []
    for m in _SECTION_HDR_RE.finditer(text):
        h = m.group(1).strip().lower()
        if len(h.split()) <= 4 and any(key in h for key in EXPECTED_ORDER):
            for key in EXPECTED_ORDER:
                if key in h:
                    headers.append(key)
                    break
    return list(dict.fromkeys(headers))


def _section_order_score(detected: list[str]) -> tuple[int, list[str]]:
    issues = []
    score = 100
    for i in range(1, len(detected)):
        try:
            prev_idx = EXPECTED_ORDER.index(detected[i-1])
            curr_idx = EXPECTED_ORDER.index(detected[i])
            if curr_idx < prev_idx:
                issues.append(
                    f"'{detected[i].title()}' appears before '{detected[i-1].title()}' — "
                    "expected order is Experience → Education → Skills."
                )
                score -= 15
        except ValueError:
            pass
    return max(0, score), issues


def _bullet_diversity_score(text: str) -> tuple[int, str | None]:
    types = _BULLET_TYPE_RE.findall(text)
    if not types:
        return 100, None
    unique = set(types)
    if len(unique) > 2:
        return 60, f"Mixed bullet types detected ({', '.join(sorted(unique))}) — use a single consistent style."
    return 100, None


def score_structure(resume_text: str, total_years: int | None = None) -> dict:
    pages = _estimate_pages(resume_text)
    detected = _detect_sections(resume_text)

    if total_years is None:
        expected_pages = 1.5
    elif total_years < 5:
        expected_pages = 1.0
    elif total_years < 15:
        expected_pages = 2.0
    else:
        expected_pages = 2.5

    page_diff = abs(pages - expected_pages)
    page_score = max(0, 100 - int(page_diff * 25))
    page_suggestions = []
    if pages < 0.6:
        page_suggestions.append(
            f"Resume appears very short (~{pages:.1f} pages). Add more detail to experience bullets."
        )
    elif pages > expected_pages + 1:
        page_suggestions.append(
            f"Resume is ~{pages:.1f} pages for {total_years or '?'} years of experience. "
            f"Target {expected_pages:.0f}-{expected_pages+0.5:.0f} pages — trim older roles."
        )

    order_score, order_issues = _section_order_score(detected)
    div_score, div_issue = _bullet_diversity_score(resume_text)

    combined = int(page_score * 0.40 + order_score * 0.35 + div_score * 0.25)

    suggestions = page_suggestions + order_issues
    if div_issue:
        suggestions.append(div_issue)

    return {
        "structure_score": combined,
        "estimated_pages": round(pages, 1),
        "expected_pages": expected_pages,
        "detected_section_order": detected,
        "page_score": page_score,
        "order_score": order_score,
        "diversity_score": div_score,
        "suggestions": suggestions,
    }
