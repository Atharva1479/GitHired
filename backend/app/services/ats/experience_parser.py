import re
from datetime import datetime
from .esco_loader import get_degree_keywords

DEGREE_LEVELS: dict[str, int] = {
    "high school": 0, "secondary": 0, "diploma": 1, "associate": 2,
    "bachelor": 3, "b.s": 3, "b.a": 3, "b.e": 3, "b.tech": 3, "undergraduate": 3,
    "master": 4, "m.s": 4, "m.a": 4, "m.e": 4, "m.tech": 4, "mba": 4, "postgraduate": 4,
    "phd": 5, "ph.d": 5, "doctorate": 5, "doctoral": 5,
}


def _extract_degree_level(text: str) -> int | None:
    lower = text.lower()
    highest: int | None = None
    for keyword, level in DEGREE_LEVELS.items():
        if keyword in lower:
            if highest is None or level > highest:
                highest = level
    return highest


def _extract_required_degree_level(jd_text: str) -> tuple[int | None, bool]:
    lower = jd_text.lower()
    preferred_only = bool(re.search(
        r'(?:preferred|nice.to.have|plus|bonus)\b.{0,40}(?:degree|bachelor|master|phd)',
        lower, re.DOTALL,
    ))
    level = _extract_degree_level(jd_text)
    return level, preferred_only


DATE_PATTERNS = [
    (
        r'(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|'
        r'jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|'
        r'dec(?:ember)?)\s+(\d{4})\s*[-–—to]+\s*'
        r'(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|'
        r'jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|'
        r'dec(?:ember)?)\s+(\d{4}|present|current|now)',
        4,
    ),
    (r'\b(\d{4})\s*[-–—to]+\s*(\d{4}|present|current|now)\b', 2),
]


def _recency_weight(start: int, end: int, now: int) -> float:
    years = end - start
    years_ago = now - end
    if years_ago <= 2:
        return years * 1.5
    elif years_ago <= 5:
        return years * 1.0
    else:
        return years * 0.6


def parse_experience(jd_text: str, resume_text: str) -> dict:
    now = datetime.now().year
    ranges: list[tuple[int, int]] = []

    for pattern, group_count in DATE_PATTERNS:
        for m in re.finditer(pattern, resume_text, re.IGNORECASE):
            try:
                g = m.groups()
                if group_count == 4:
                    s = int(g[1])
                    e = now if g[3].lower() in ("present", "current", "now") else int(g[3])
                else:
                    s = int(g[0])
                    e = now if g[1].lower() in ("present", "current", "now") else int(g[1])
                if 1970 <= s <= now and s <= e:
                    ranges.append((s, e))
            except Exception:
                continue

    ranges.sort()
    merged: list[list[int]] = []
    for s, e in ranges:
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])

    total_years = sum(e - s for s, e in merged)
    weighted_years = sum(_recency_weight(s, e, now) for s, e in merged)

    req_match = re.search(
        r'(\d+)\+?\s*(?:to\s*\d+)?\s*years?\s*(?:of\s+)?(?:experience|exp|work)',
        jd_text,
        re.IGNORECASE,
    )
    required_years: int | None = int(req_match.group(1)) if req_match else None

    if required_years:
        ratio = weighted_years / required_years
        if ratio >= 1.0:
            exp_score = 100
        elif ratio >= 0.85:
            exp_score = 85
        elif ratio >= 0.70:
            exp_score = 70
        elif ratio >= 0.50:
            exp_score = 50
        else:
            exp_score = 30
    else:
        if total_years >= 8:
            exp_score = 100
        elif total_years >= 5:
            exp_score = 90
        elif total_years >= 3:
            exp_score = 80
        elif total_years >= 1:
            exp_score = 70
        else:
            exp_score = 50

    degree_keywords = get_degree_keywords()
    resume_lower = resume_text.lower()
    degree_found = any(d.lower() in resume_lower for d in degree_keywords)

    resume_degree_level = _extract_degree_level(resume_text)
    required_degree_level, preferred_only = _extract_required_degree_level(jd_text)

    if required_degree_level is None:
        education_score = 100
    elif resume_degree_level is None:
        education_score = 30
    elif resume_degree_level >= required_degree_level:
        education_score = 100
    elif resume_degree_level == required_degree_level - 1:
        education_score = 70 if not preferred_only else 85
    else:
        education_score = 45 if preferred_only else 30

    return {
        "experience_score": exp_score,
        "education_score": education_score,
        "total_years": total_years,
        "weighted_years": round(weighted_years, 1),
        "required_years": required_years,
        "degree_found": degree_found,
        "resume_degree_level": resume_degree_level,
        "required_degree_level": required_degree_level,
        "degree_preferred_only": preferred_only,
        "date_ranges": merged,
    }
