"""Analyze bullet quality: length, tense, duplicates, STAR method, soft skills."""
from __future__ import annotations
import re
from difflib import SequenceMatcher

_BULLET_RE = re.compile(r'(?:^|\n)\s*[•\-–—*▸○◦▪]\s*(.{10,})', re.MULTILINE)

_PAST_TENSE_VERBS = {
    "built","developed","designed","engineered","implemented","deployed","created",
    "led","managed","delivered","automated","scaled","migrated","integrated","reduced",
    "improved","increased","optimized","launched","shipped","configured","wrote",
    "maintained","refactored","analyzed","modeled","trained","collaborated","worked",
    "supported","helped","assisted","coordinated","established","achieved","drove",
}
_PRESENT_TENSE_VERBS = {
    "build","develop","design","engineer","implement","deploy","create","lead","manage",
    "deliver","automate","scale","migrate","integrate","reduce","improve","increase",
    "optimize","launch","ship","configure","write","maintain","refactor","analyze",
    "model","train","collaborate","work","support","help","assist","coordinate",
    "establish","achieve","drive",
}

_METRIC_RE = re.compile(
    r'\b\d+(?:\.\d+)?\s*(?:%|x|×|k|m|billion|million|thousand)\b'
    r'|\$\s*\d+|\b\d{4,}\b',
    re.IGNORECASE,
)

SOFT_SKILLS = {
    "leadership","communication","collaboration","teamwork","cross-functional",
    "stakeholder","analytical","problem-solving","adaptable","initiative",
    "interpersonal","presentation","mentoring","coaching","negotiation",
    "time management","detail-oriented","self-motivated","proactive",
}


def _word_count(text: str) -> int:
    return len(text.split())


def _first_verb(text: str) -> str:
    words = text.strip().split()
    return words[0].lower().rstrip("s") if words else ""


def analyze_bullets(resume_text: str, current_role_text: str = "") -> dict:
    bullets = _BULLET_RE.findall(resume_text)
    if not bullets:
        return {
            "bullet_quality_score": 70,
            "total_bullets": 0,
            "short_bullets": 0,
            "long_bullets": 0,
            "star_bullets": 0,
            "star_score": 70,
            "duplicate_pairs": 0,
            "tense_issues": 0,
            "soft_skill_count": 0,
            "soft_skills_found": [],
            "suggestions": [],
        }

    total = len(bullets)
    suggestions: list[str] = []

    # Bullet length
    short = sum(1 for b in bullets if _word_count(b) < 8)
    long  = sum(1 for b in bullets if _word_count(b) > 30)
    length_score = max(0, 100 - (short * 8) - (long * 5))
    if short > 2:
        suggestions.append(
            f"{short} bullets are under 8 words — too sparse for ATS context extraction. "
            "Expand with technology, scope, or outcome details."
        )
    if long > 2:
        suggestions.append(
            f"{long} bullets exceed 30 words — ATS systems truncate these. "
            "Break long bullets into two shorter ones."
        )

    # STAR method
    star = sum(
        1 for b in bullets
        if (_first_verb(b) in _PAST_TENSE_VERBS or _first_verb(b) in _PRESENT_TENSE_VERBS)
        and _METRIC_RE.search(b)
        and _word_count(b) >= 10
    )
    star_score = min(100, int(star / max(total, 1) * 200))
    if star / max(total, 1) < 0.4:
        suggestions.append(
            f"Only {star}/{total} bullets follow the STAR format (action + context + metric). "
            "Add measurable outcomes to more bullets."
        )

    # Tense consistency
    tense_issues = 0
    if current_role_text:
        current_bullets = _BULLET_RE.findall(current_role_text)
        for b in current_bullets:
            v = _first_verb(b)
            if v in _PAST_TENSE_VERBS:
                tense_issues += 1
    tense_score = max(0, 100 - tense_issues * 15)
    if tense_issues > 1:
        suggestions.append(
            f"{tense_issues} bullets in your current role use past tense. "
            "Current role bullets should use present tense (Build, Lead, Design)."
        )

    # Duplicate detection
    dup_pairs = 0
    for i in range(len(bullets)):
        for j in range(i + 1, len(bullets)):
            sim = SequenceMatcher(None, bullets[i].lower(), bullets[j].lower()).ratio()
            if sim > 0.80:
                dup_pairs += 1
    dup_score = max(0, 100 - dup_pairs * 20)
    if dup_pairs:
        suggestions.append(
            f"{dup_pairs} near-duplicate bullet{'s' if dup_pairs > 1 else ''} detected. "
            "Each bullet should describe a distinct achievement."
        )

    # Soft skills
    lower = resume_text.lower()
    soft_found = [s for s in SOFT_SKILLS if s in lower]
    soft_score = min(100, len(soft_found) * 20)

    combined = int(
        length_score * 0.25 +
        star_score   * 0.30 +
        tense_score  * 0.20 +
        dup_score    * 0.15 +
        soft_score   * 0.10
    )

    return {
        "bullet_quality_score": combined,
        "total_bullets": total,
        "short_bullets": short,
        "long_bullets": long,
        "star_bullets": star,
        "star_score": star_score,
        "duplicate_pairs": dup_pairs,
        "tense_issues": tense_issues,
        "soft_skill_count": len(soft_found),
        "soft_skills_found": soft_found,
        "suggestions": suggestions,
    }
