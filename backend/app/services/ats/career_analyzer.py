"""Detect employment gaps and analyze job tenure patterns."""
from __future__ import annotations
import re
from datetime import date

MONTHS = {
    "jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,
    "jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12,
    "january":1,"february":2,"march":3,"april":4,"june":6,"july":7,
    "august":8,"september":9,"october":10,"november":11,"december":12,
}

_DATE_RE = re.compile(
    r'\b(?:(?P<mon>[A-Za-z]{3,9})[\s\.\-]*)?(?P<year>20\d{2}|19\d{2})\b',
    re.IGNORECASE,
)
_PRESENT_RE = re.compile(r'\b(?:present|current|now|today)\b', re.IGNORECASE)
_DATE_RANGE_RE = re.compile(
    r'(?P<start>(?:[A-Za-z]{3,9}[\s\.\-]*)?\d{4})'
    r'\s*[-–—to]+\s*'
    r'(?P<end>(?:[A-Za-z]{3,9}[\s\.\-]*)?\d{4}|present|current|now)',
    re.IGNORECASE,
)


def _parse_ym(text: str, is_end: bool = False) -> tuple[int, int] | None:
    m = _DATE_RE.search(text)
    if not m:
        return None
    year = int(m.group("year"))
    mon_str = (m.group("mon") or "").lower()[:3]
    mon = MONTHS.get(mon_str, 12 if is_end else 1)
    return year, mon


def _ym_to_months(ym: tuple[int, int]) -> int:
    return ym[0] * 12 + ym[1]


def analyze_career(resume_text: str) -> dict:
    today = date.today()
    current_ym = (today.year, today.month)

    ranges: list[tuple[tuple[int,int], tuple[int,int]]] = []
    for m in _DATE_RANGE_RE.finditer(resume_text):
        start = _parse_ym(m.group("start"), is_end=False)
        end_raw = m.group("end")
        if _PRESENT_RE.search(end_raw):
            end = current_ym
        else:
            end = _parse_ym(end_raw, is_end=True)
        if start and end and _ym_to_months(start) <= _ym_to_months(end):
            ranges.append((start, end))

    if not ranges:
        return {
            "career_score": 80,
            "gaps": [],
            "max_gap_months": 0,
            "avg_tenure_months": None,
            "short_tenure_roles": 0,
            "suggestions": [],
        }

    ranges.sort(key=lambda r: _ym_to_months(r[0]))

    gaps: list[dict] = []
    for i in range(1, len(ranges)):
        prev_end   = _ym_to_months(ranges[i-1][1])
        curr_start = _ym_to_months(ranges[i][0])
        gap = curr_start - prev_end
        if gap > 6:
            gaps.append({
                "gap_months": gap,
                "after": f"{ranges[i-1][1][0]}/{ranges[i-1][1][1]:02d}",
                "before": f"{ranges[i][0][0]}/{ranges[i][0][1]:02d}",
            })

    max_gap = max((g["gap_months"] for g in gaps), default=0)
    tenures = [_ym_to_months(e) - _ym_to_months(s) for s, e in ranges]
    avg_tenure = int(sum(tenures) / len(tenures)) if tenures else None
    short = sum(1 for t in tenures if t < 12)

    score = 100
    if max_gap > 12:  score -= 25
    elif max_gap > 6: score -= 12
    if avg_tenure and avg_tenure < 12:   score -= 20
    elif avg_tenure and avg_tenure < 18: score -= 10
    if short >= 3:    score -= 15
    elif short >= 2:  score -= 8
    score = max(0, score)

    suggestions: list[str] = []
    if gaps:
        suggestions.append(
            f"Employment gap{'s' if len(gaps) > 1 else ''} detected ({max_gap} months max). "
            "Add a brief explanation in your summary or cover letter."
        )
    if avg_tenure and avg_tenure < 18:
        suggestions.append(
            f"Average job tenure is {avg_tenure} months — ATS flag candidates with "
            "frequent short stints. Consider grouping contract/freelance work."
        )

    return {
        "career_score": score,
        "gaps": gaps,
        "max_gap_months": max_gap,
        "avg_tenure_months": avg_tenure,
        "short_tenure_roles": short,
        "suggestions": suggestions,
    }
