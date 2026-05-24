import asyncio
import logging
from . import (
    esco_loader,
    experience_parser,
    jd_parser,
    keyword_extractor,
    ontology_matcher,
    parsability_checker,
    positional_scorer,
    resume_parser,
    semantic_scorer,
    word_semantic,
)

log = logging.getLogger("ats.scorer")

WEIGHTS: dict[str, float] = {
    "positional_keyword": 0.25,
    "required_coverage": 0.15,
    "semantic_sentence": 0.20,
    "word_semantic": 0.15,
    "ontology_match": 0.10,
    "experience": 0.08,
    "education": 0.05,
    "parsability": 0.02,
}

GRADE_MAP: list[tuple[int, str]] = [
    (90, "A+"), (85, "A"), (80, "A-"), (75, "B+"), (70, "B"),
    (65, "B-"), (60, "C+"), (55, "C"), (50, "C-"), (40, "D"), (0, "F"),
]


async def analyze_resume(resume_text: str, jd_text: str) -> dict:
    synonym_map = esco_loader.get_synonym_map()

    resume_parsed = resume_parser.parse_resume(resume_text)
    jd_parsed = jd_parser.parse_jd(jd_text)
    keywords = keyword_extractor.extract_keywords(jd_parsed)

    # ESCO occupation-aware implicit skills boost
    jd_title = jd_parsed.get("jd_title", "")
    occupation_skills = esco_loader.get_occupation_skills(jd_title)
    implicit_added: list[str] = []
    if occupation_skills:
        existing = set(keywords["preferred"] + keywords["required"])
        implicit_added = [s for s in occupation_skills if s not in existing][:8]
        keywords["preferred"] = keywords["preferred"] + implicit_added
        keywords["all_unique"] = list(set(keywords["all_unique"] + implicit_added))

    pos_r, ont_r, exp_r, par_r, sem_r, word_r = await asyncio.gather(
        asyncio.to_thread(
            positional_scorer.positional_keyword_score, keywords, resume_parsed, synonym_map
        ),
        asyncio.to_thread(ontology_matcher.ontology_score, keywords, resume_parsed),
        asyncio.to_thread(experience_parser.parse_experience, jd_text, resume_text),
        asyncio.to_thread(
            parsability_checker.check_parsability, resume_text, resume_parsed
        ),
        asyncio.to_thread(semantic_scorer.semantic_sentence_score, jd_parsed, resume_parsed),
        asyncio.to_thread(
            word_semantic.word_similarity_score, keywords["required"], resume_parsed
        ),
    )

    total_required = len(keywords["required"])
    missing_required = len(pos_r["required_missing"])
    required_coverage = (
        (total_required - missing_required) / total_required * 100
        if total_required
        else 75.0
    )

    overall = round(
        pos_r["score"] * WEIGHTS["positional_keyword"]
        + required_coverage * WEIGHTS["required_coverage"]
        + sem_r["score"] * WEIGHTS["semantic_sentence"]
        + word_r["score"] * WEIGHTS["word_semantic"]
        + ont_r["score"] * WEIGHTS["ontology_match"]
        + exp_r["experience_score"] * WEIGHTS["experience"]
        + exp_r["education_score"] * WEIGHTS["education"]
        + par_r["score"] * WEIGHTS["parsability"],
        1,
    )

    grade = next(g for t, g in GRADE_MAP if overall >= t)

    # Build actionable suggestions
    suggestions: list[str] = []
    if pos_r["required_missing"]:
        suggestions.append(
            f"Critical: Add these required keywords to your Skills section: "
            f"{', '.join(pos_r['required_missing'][:5])}"
        )
    if pos_r["preferred_missing"]:
        suggestions.append(
            f"Add preferred skills to improve score: "
            f"{', '.join(pos_r['preferred_missing'][:3])}"
        )
    if "skills" in par_r["sections_missing"]:
        suggestions.append(
            "Add a dedicated 'Technical Skills' section — ATS gives it a 2.5× position weight"
        )
    if not resume_parsed.get("summary", "").strip():
        suggestions.append(
            "Add a professional summary with the target job title and 2-3 key skills from the JD"
        )
    if exp_r["experience_score"] < 70 and exp_r["required_years"]:
        suggestions.append(
            f"JD requires {exp_r['required_years']}+ years — "
            f"make date ranges clearly readable (e.g. 'Jan 2021 – Present')"
        )
    if word_r.get("semantic_matches"):
        examples = [
            f'"{m["resume_term"]}" ≈ "{m["jd_term"]}"'
            for m in word_r["semantic_matches"][:2]
        ]
        suggestions.append(
            f"Word2Vec found semantic matches: {', '.join(examples)} — "
            f"consider using the JD's exact wording for higher keyword score"
        )
    for risk in par_r["ats_risks"]:
        suggestions.append(f"ATS Risk: {risk}")
    missing_in_skills = [
        k
        for k in pos_r["required_matched"]
        if pos_r["matched_keywords"].get(k, {}).get("section") != "skills"
    ]
    if missing_in_skills:
        suggestions.append(
            f"Move these into your Skills section for 2.5× ATS weight: "
            f"{', '.join(missing_in_skills[:4])}"
        )

    return {
        "overall_score": overall,
        "grade": grade,
        "categories": {
            "keyword_match": {
                "label": "Keyword Match (Positional)",
                "score": pos_r["score"],
                "weight": 25,
                "description": (
                    "Skills(2.5×) > Certs(2×) > Experience(1.5×) — Taleo Req Rank model"
                ),
            },
            "required_coverage": {
                "label": "Required Keywords Coverage",
                "score": required_coverage,
                "weight": 15,
                "description": (
                    f"{total_required - missing_required} of {total_required} "
                    f"required keywords found"
                ),
            },
            "semantic_sentence": {
                "label": "Semantic Phrase Match",
                "score": sem_r["score"],
                "weight": 20,
                "description": "MiniLM — 'Led team of 8' matches 'leadership'",
                "fallback": sem_r.get("fallback", False),
            },
            "word_semantic": {
                "label": "Word Semantic Similarity",
                "score": word_r["score"],
                "weight": 15,
                "description": (
                    "Word2Vec — 'engineer' ≈ 'developer', 'built' ≈ 'developed'"
                ),
                "fallback": word_r.get("fallback", False),
            },
            "ontology_match": {
                "label": "ESCO Ontology Match",
                "score": ont_r["score"],
                "weight": 10,
                "description": (
                    "'K8s' matches 'Kubernetes', 'Postgres' matches 'PostgreSQL'"
                ),
            },
            "experience": {
                "label": "Experience (Recency-Weighted)",
                "score": exp_r["experience_score"],
                "weight": 8,
                "description": (
                    f"{exp_r['total_years']} yrs raw, "
                    f"{exp_r.get('weighted_years', exp_r['total_years'])} yrs recency-weighted"
                    + (
                        f" vs {exp_r['required_years']} required"
                        if exp_r["required_years"]
                        else ""
                    )
                ),
            },
            "education": {
                "label": "Education Match",
                "score": exp_r["education_score"],
                "weight": 5,
                "description": "Degree and certification requirements",
            },
            "parsability": {
                "label": "ATS Parsability",
                "score": par_r["score"],
                "weight": 2,
                "description": "Resume structure, sections, ATS-readable formatting",
            },
        },
        "matched_keywords": list(pos_r["matched_keywords"].keys()),
        "missing_keywords": pos_r["required_missing"] + pos_r["preferred_missing"],
        "required_missing": pos_r["required_missing"],
        "preferred_missing": pos_r["preferred_missing"],
        "keyword_placement": pos_r["matched_keywords"],
        "synonym_matches": ont_r["synonym_matches"],
        "semantic_matches": sem_r.get("top_matches", []),
        "word_semantic_matches": word_r.get("semantic_matches", []),
        "suggestions": suggestions[:8],
        "sections": {
            "found": par_r["sections_found"],
            "missing": par_r["sections_missing"],
            "ats_risks": par_r["ats_risks"],
        },
        "experience_data": {
            "total_years": exp_r["total_years"],
            "weighted_years": exp_r.get("weighted_years"),
            "required_years": exp_r["required_years"],
            "degree_found": exp_r["degree_found"],
        },
        "occupation_context": {
            "detected_title": jd_title,
            "implicit_skills_added": implicit_added,
        },
        "jd_structure": {
            "required_count": len(keywords["required"]),
            "preferred_count": len(keywords["preferred"]),
            "context_count": len(keywords["context"]),
        },
        "keyword_stats": {
            "total_jd_keywords": len(keywords["all_unique"]),
            "matched_count": len(pos_r["matched_keywords"]),
            "missing_count": len(pos_r["missing_keywords"]),
            "required_missing_count": len(pos_r["required_missing"]),
            "match_percentage": (
                round(
                    len(pos_r["matched_keywords"]) / len(keywords["all_unique"]) * 100
                )
                if keywords["all_unique"]
                else 0
            ),
        },
        "ml_status": {
            "semantic_sentence_active": not sem_r.get("fallback", False),
            "word_semantic_active": not word_r.get("fallback", False),
        },
    }
