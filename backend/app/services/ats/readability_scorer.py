"""Reading level, date consistency, GPA detection, repeated phrases."""
from __future__ import annotations
import re
from collections import Counter

_SENTENCE_RE = re.compile(r'[.!?]+')
_SYLLABLE_RE = re.compile(r'[aeiouAEIOU]+')

_DATE_FORMATS = {
    "mon_year": re.compile(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}\b', re.IGNORECASE),
    "num_year":  re.compile(r'\b\d{1,2}/\d{4}\b'),
    "year_only": re.compile(r'(?<!\d)\b(20\d{2}|19\d{2})\b(?!\d)'),
    "full_mon":  re.compile(r'\b(?:January|February|March|April|June|July|August|September|October|November|December)\s+\d{4}\b', re.IGNORECASE),
}

_GPA_RE = re.compile(
    r'\bGPA[\s:]*(\d\.\d{1,2})\b'
    r'|(\d\.\d{1,2})\s*/\s*4\.0'
    r'|\b(cum laude|magna cum laude|summa cum laude)\b',
    re.IGNORECASE,
)

_PHRASE_RE = re.compile(r'\b([a-z]{4,}\s+[a-z]{3,}(?:\s+[a-z]{3,})?)\b')


def _count_syllables(word: str) -> int:
    word = word.lower().strip(".,!?;:")
    count = len(_SYLLABLE_RE.findall(word))
    if word.endswith("e") and count > 1:
        count -= 1
    return max(1, count)


def _flesch_kincaid(text: str) -> float:
    words = text.split()
    if not words:
        return 50.0
    sentences = max(1, len(_SENTENCE_RE.findall(text)))
    syllables = sum(_count_syllables(w) for w in words)
    score = 206.835 - 1.015 * (len(words) / sentences) - 84.6 * (syllables / len(words))
    return round(max(0, min(100, score)), 1)


def _date_format_consistency(text: str) -> tuple[int, str | None]:
    found_formats = {name for name, pat in _DATE_FORMATS.items() if pat.search(text)}
    if len(found_formats) > 1 and "year_only" in found_formats:
        found_formats.discard("year_only")
    if len(found_formats) > 1:
        return 70, (
            f"Mixed date formats detected ({', '.join(sorted(found_formats))}). "
            "Use one consistent format throughout (e.g. always 'Jan 2020')."
        )
    return 100, None


def _detect_gpa(text: str) -> dict:
    m = _GPA_RE.search(text)
    if not m:
        return {"gpa_found": False, "gpa_value": None, "honors": None}
    gpa = m.group(1) or m.group(2)
    honors = m.group(3)
    return {
        "gpa_found": True,
        "gpa_value": float(gpa) if gpa else None,
        "honors": honors,
    }


def _repeated_phrases(text: str, threshold: int = 3) -> list[str]:
    lower = text.lower()
    phrases = _PHRASE_RE.findall(lower)
    counts = Counter(phrases)
    return [p for p, c in counts.items() if c >= threshold and len(p) > 8]


def score_readability(resume_text: str) -> dict:
    fk = _flesch_kincaid(resume_text)
    date_score, date_issue = _date_format_consistency(resume_text)
    gpa_info = _detect_gpa(resume_text)
    repeated = _repeated_phrases(resume_text)

    if 40 <= fk <= 70:
        fk_score = 100
    elif fk > 70:
        fk_score = max(60, 100 - int((fk - 70) * 2))
    else:
        fk_score = max(50, 100 - int((40 - fk) * 2))

    repeated_score = max(0, 100 - len(repeated) * 15)
    combined = int(fk_score * 0.35 + date_score * 0.35 + repeated_score * 0.30)

    suggestions: list[str] = []
    if fk < 30:
        suggestions.append(
            f"Reading level very complex (Flesch score {fk}) — ATS may misparse dense jargon. "
            "Use clear, concise sentences."
        )
    elif fk > 80:
        suggestions.append(
            f"Reading level too simple (Flesch score {fk}) — add more technical specificity."
        )
    if date_issue:
        suggestions.append(date_issue)
    if repeated:
        ex = "', '".join(repeated[:2])
        suggestions.append(
            f"Repeated phrases detected: '{ex}'. "
            "Vary your language to avoid ATS spam filters."
        )

    return {
        "readability_score": combined,
        "flesch_kincaid": fk,
        "fk_score": fk_score,
        "date_format_score": date_score,
        "repeated_phrases": repeated[:5],
        "gpa": gpa_info,
        "suggestions": suggestions,
    }
