from rapidfuzz import fuzz
from .esco_loader import get_synonym_map

POSITION_WEIGHTS: dict[str, float] = {
    "skills": 2.5,
    "certifications": 2.0,
    "experience": 1.5,
    "summary": 1.2,
    "projects": 1.0,
    "education": 0.8,
    "other": 0.5,
    "contact": 0.3,
}
KEYWORD_TYPE_WEIGHTS: dict[str, float] = {
    "required": 1.0,
    "preferred": 0.5,
    "context": 0.3,
}
MAX_POSITION_WEIGHT = max(POSITION_WEIGHTS.values())  # 2.5


def _keyword_in_text(kw: str, text: str, alias_map: dict[str, str]) -> bool:
    if not text:
        return False
    kw_lower = kw.lower()
    text_lower = text.lower()
    if kw_lower in text_lower:
        return True
    # Synonym expansion
    for alias, canonical in alias_map.items():
        if canonical.lower() == kw_lower and alias in text_lower:
            return True
    # Fuzzy last resort — only on individual tokens to avoid false positives
    for word in text_lower.split():
        if len(word) > 4 and fuzz.ratio(kw_lower, word) >= 88:
            return True
    return False


def positional_keyword_score(
    keywords: dict, resume_parsed: dict, synonym_map: dict,
    recent_experience_text: str = "",
) -> dict:
    # Build alias → canonical map
    alias_map: dict[str, str] = {}
    for canonical, aliases in synonym_map.items():
        for alias in aliases:
            alias_map[alias.lower()] = canonical

    # Full resume text (lowercased) for density counting
    resume_lower = " ".join(str(v) for v in resume_parsed.values() if v).lower()
    recent_lower = recent_experience_text.lower()

    earned = 0.0
    max_possible = 0.0
    matched_keywords: dict[str, dict] = {}
    missing_keywords: dict[str, dict] = {}

    for kw_type, kw_list in [
        ("required", keywords["required"]),
        ("preferred", keywords["preferred"]),
        ("context", keywords["context"]),
    ]:
        type_weight = KEYWORD_TYPE_WEIGHTS[kw_type]
        for kw in kw_list:
            best_pos = 0.0
            best_section: str | None = None
            for section, text in resume_parsed.items():
                if text and _keyword_in_text(kw, str(text), alias_map):
                    pw = POSITION_WEIGHTS.get(section, 0.5)
                    if pw > best_pos:
                        best_pos = pw
                        best_section = section

            possible = type_weight * MAX_POSITION_WEIGHT
            max_possible += possible

            if best_section:
                # --- Density multiplier ---
                kw_lower = kw.lower()
                freq = resume_lower.count(kw_lower)
                if freq <= 1:
                    density_mult = 1.0
                elif freq == 2:
                    density_mult = 1.2
                else:
                    density_mult = min(1.4, 1.0 + 0.15 * freq)

                # --- Recency multiplier ---
                if best_section == "experience" and recent_lower:
                    recency_mult = 1.25 if kw_lower in recent_lower else 0.80
                else:
                    recency_mult = 1.0

                earned += type_weight * best_pos * density_mult * recency_mult
                matched_keywords[kw] = {"section": best_section, "type": kw_type}
            else:
                missing_keywords[kw] = {"type": kw_type}

    score = round((earned / max_possible) * 100, 1) if max_possible > 0 else 0.0

    return {
        "score": score,
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_keywords,
        "required_matched": [k for k, v in matched_keywords.items() if v["type"] == "required"],
        "required_missing": [k for k, v in missing_keywords.items() if v["type"] == "required"],
        "preferred_matched": [k for k, v in matched_keywords.items() if v["type"] == "preferred"],
        "preferred_missing": [k for k, v in missing_keywords.items() if v["type"] == "preferred"],
    }
