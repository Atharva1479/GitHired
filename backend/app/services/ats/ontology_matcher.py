from .esco_loader import get_synonym_map


def ontology_score(keywords: dict, resume_parsed: dict) -> dict:
    synonym_map = get_synonym_map()
    resume_full = " ".join(str(v) for v in resume_parsed.values()).lower()

    required = keywords["required"]
    matched_via_synonym: list[dict] = []
    literal_count = 0

    for kw in required:
        kw_lower = kw.lower()
        if kw_lower in resume_full:
            literal_count += 1
            continue
        aliases = synonym_map.get(kw_lower, [])
        for alias in aliases:
            if alias.lower() in resume_full:
                matched_via_synonym.append({"keyword": kw, "matched_alias": alias})
                break

    total_matched = literal_count + len(matched_via_synonym)
    score = (
        round(total_matched / len(required) * 100, 1)
        if required
        else 50.0
    )
    return {"score": min(score, 100.0), "synonym_matches": matched_via_synonym}
