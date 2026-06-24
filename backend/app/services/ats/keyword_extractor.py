import structlog
from .esco_loader import get_all_skills, get_synonym_map

log = structlog.get_logger("ats.keyword_extractor")


def extract_keywords(jd_parsed: dict) -> dict:
    master_skills = get_all_skills()
    synonym_map = get_synonym_map()

    # Build alias → canonical reverse map
    alias_to_canonical: dict[str, str] = {}
    for canonical, aliases in synonym_map.items():
        for alias in aliases:
            alias_to_canonical[alias.lower()] = canonical

    def find_skills(text: str) -> list[str]:
        if not text:
            return []
        text_lower = text.lower()
        found: set[str] = set()
        for skill in master_skills:
            if skill.lower() in text_lower:
                found.add(skill)
        for alias, canonical in alias_to_canonical.items():
            if alias in text_lower:
                found.add(canonical)
        return list(found)

    required_kws = find_skills(jd_parsed["required_text"])
    preferred_kws = find_skills(jd_parsed["preferred_text"])

    # Remove from preferred any keyword already in required. Without this, the
    # positional_scorer's preferred pass overwrites those keywords' matched_keywords
    # entry from type="required" to type="preferred", deflating found_required and
    # therefore kw_score even when all required keywords are present in the resume.
    required_set = set(required_kws)
    preferred_kws = [k for k in preferred_kws if k not in required_set]

    # Exclude from context any skill already classified as required or preferred.
    classified = required_set | set(preferred_kws)
    context_kws = [k for k in find_skills(jd_parsed["context_text"]) if k not in classified]

    all_kws = list(set(required_kws + preferred_kws + context_kws))
    return {
        "required": list(set(required_kws)),
        "preferred": list(set(preferred_kws)),
        "context": list(set(context_kws)),
        "all_unique": list(set(all_kws)),
    }
