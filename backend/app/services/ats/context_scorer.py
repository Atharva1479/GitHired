"""Context-aware keyword scoring — passive mentions score lower than active use."""
from __future__ import annotations
import re

_ACTION_VERBS = {
    "built","developed","designed","engineered","implemented","deployed","created",
    "led","managed","delivered","automated","scaled","migrated","integrated","reduced",
    "improved","increased","optimized","architected","launched","shipped","configured",
    "wrote","maintained","refactored","analyzed","modeled","trained","fine-tuned",
    "used","leveraged","applied","utilized","worked","experienced",
}

_PASSIVE_PATTERNS = re.compile(
    r'\b(?:familiar with|exposure to|learning|learning to|interested in|'
    r'need to learn|want to learn|basic knowledge of|some experience with|'
    r'beginner|novice|knowledge of|understanding of)\b',
    re.IGNORECASE,
)

_SKILLS_SECTION_RE = re.compile(
    r'(?:skills?|technologies|tech stack|competencies|proficiencies)',
    re.IGNORECASE,
)


def _get_window(text: str, kw: str, window: int = 60) -> str:
    idx = text.lower().find(kw.lower())
    if idx == -1:
        return ""
    return text[max(0, idx - window): idx + len(kw) + window].lower()


def _is_active_use(window: str, in_skills_section: bool) -> bool:
    if in_skills_section:
        return True
    if _PASSIVE_PATTERNS.search(window):
        return False
    for w in window.split():
        clean = re.sub(r'[^a-z]', '', w.lower())
        if clean in _ACTION_VERBS or clean.rstrip("s") in _ACTION_VERBS:
            return True
    return False


def score_keyword_context(resume_text: str, matched_keywords: list[str]) -> dict:
    if not matched_keywords:
        return {
            "context_score": 100,
            "passive_keywords": [],
            "active_count": 0,
            "passive_count": 0,
            "suggestions": [],
        }

    skills_section_text = ""
    for line in resume_text.split("\n"):
        if _SKILLS_SECTION_RE.search(line) and len(line.strip()) < 40:
            idx = resume_text.find(line)
            skills_section_text = resume_text[idx:idx+400].lower()
            break

    active, passive = [], []
    for kw in matched_keywords:
        in_skills = kw.lower() in skills_section_text
        window = _get_window(resume_text, kw)
        if _is_active_use(window, in_skills):
            active.append(kw)
        else:
            passive.append(kw)

    total = len(matched_keywords)
    active_ratio = len(active) / total
    context_score = int(30 + active_ratio * 70)

    suggestions: list[str] = []
    if passive:
        names = ", ".join(passive[:4])
        suggestions.append(
            f"Keywords mentioned passively (not in active-use context): {names}. "
            "Move them into an experience bullet or skills section with a proficiency claim."
        )

    return {
        "context_score": context_score,
        "passive_keywords": passive,
        "active_count": len(active),
        "passive_count": len(passive),
        "suggestions": suggestions,
    }
