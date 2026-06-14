"""Score resume for quantified achievements and action verb strength."""
from __future__ import annotations
import re

STRONG_VERBS = {
    "architected", "engineered", "designed", "built", "developed", "created",
    "launched", "shipped", "deployed", "implemented", "established", "founded",
    "led", "managed", "directed", "spearheaded", "drove", "championed",
    "reduced", "decreased", "eliminated", "optimised", "optimized", "improved",
    "increased", "generated", "delivered", "achieved", "exceeded", "surpassed",
    "scaled", "automated", "streamlined", "transformed", "modernized",
    "integrated", "migrated", "refactored", "restructured", "revamped",
    "mentored", "trained", "hired", "grew", "expanded", "negotiated",
    "secured", "raised", "saved", "cut", "halved", "doubled", "tripled",
}

WEAK_VERBS = {
    "helped", "assisted", "supported", "worked", "participated", "involved",
    "contributed", "handled", "responsible", "maintained", "utilized", "used",
    "performed", "did", "made", "got", "had", "was", "were", "completed",
    "ensured", "provided", "learned", "gained", "obtained",
}

_QUANT_RE = re.compile(
    r'\b\d+(?:\.\d+)?\s*(?:%|percent|x|×|k|m|billion|million|thousand)\b'
    r'|\$\s*\d+(?:\.\d+)?[kmb]?\b'
    r'|\b\d+(?:\.\d+)?[x×]\b'
    r'|\b\d{4,}\b'
    r'|\b\d{1,3}(?:,\d{3})+\b'     # comma-formatted: 10,000 / 5,000
    r'|\b\d+\+(?!\d)',              # explicit lower-bound counts: 10+, 15+ (no trailing \b — + is non-word)
    re.IGNORECASE,
)

_BULLET_RE = re.compile(r'(?:^|\n)\s*[•\-–—*▸○◦]\s*(.+)', re.MULTILINE)


def score_achievements(resume_text: str) -> dict:
    """Return achievement_score (0-100) + diagnostics."""
    items = _BULLET_RE.findall(resume_text)
    total = max(len(items), 1)

    quant_count = sum(1 for item in items if _QUANT_RE.search(item))
    quant_rate  = quant_count / total
    quant_score = min(100, int(quant_rate * 250))

    first_words = []
    for item in items:
        words = item.strip().split()
        if words:
            w = words[0].lower()
            stems = {w, w.rstrip("ed").rstrip("d")}
            first_words.append(stems)

    strong = sum(1 for stems in first_words if stems & STRONG_VERBS)
    weak   = sum(1 for stems in first_words if stems & WEAK_VERBS)
    verb_score = min(100, int((strong / max(len(first_words), 1)) * 250))

    combined = int(quant_score * 0.6 + verb_score * 0.4)

    suggestions: list[str] = []
    if quant_rate < 0.35:
        suggestions.append(
            f"Only {quant_count}/{total} bullets have numbers — "
            "add %, $, or scale metrics to at least 40% of your experience bullets."
        )
    if first_words and strong / max(len(first_words), 1) < 0.35:
        suggestions.append(
            "Many bullets start with weak verbs (helped, assisted, worked) — "
            "replace with: engineered, reduced, scaled, automated, delivered."
        )

    return {
        "achievement_score": combined,
        "quant_score": quant_score,
        "verb_score": verb_score,
        "quant_count": quant_count,
        "total_bullets": total,
        "strong_verb_count": strong,
        "weak_verb_count": weak,
        "suggestions": suggestions,
    }
