import logging
from .esco_loader import get_all_skills, get_synonym_map

log = logging.getLogger("ats.keyword_extractor")


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
    context_kws = find_skills(jd_parsed["context_text"])

    # Extract repeated bigrams/trigrams from required section as extra keywords
    extra_required: list[str] = []
    try:
        from nltk import bigrams, trigrams, word_tokenize
        from nltk.corpus import stopwords

        stop = set(stopwords.words("english"))
        tokens = [
            t.lower()
            for t in word_tokenize(jd_parsed["required_text"])
            if t.isalpha() and t.lower() not in stop and len(t) > 2
        ]
        full_lower = jd_parsed["full_text"].lower()
        for ng in list(bigrams(tokens)) + list(trigrams(tokens)):
            phrase = " ".join(ng)
            if full_lower.count(phrase) >= 2 and phrase not in required_kws:
                extra_required.append(phrase)
    except Exception as exc:
        log.debug("keyword_extractor: nltk n-gram pass skipped", error=str(exc))

    all_kws = list(set(required_kws + preferred_kws + context_kws + extra_required))
    return {
        "required": list(set(required_kws + extra_required)),
        "preferred": list(set(preferred_kws)),
        "context": list(set(context_kws)),
        "all_unique": list(set(all_kws)),
    }
