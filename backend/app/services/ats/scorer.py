import asyncio
import datetime
import logging
import re

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
from .achievement_scorer import score_achievements
from .certification_matcher import score_certifications
from .title_matcher import score_title_match
from app.services.ats.context_scorer import score_keyword_context
from app.services.ats.contact_scorer import score_contact
from app.services.ats.career_analyzer import analyze_career
from app.services.ats.bullet_analyzer import analyze_bullets
from app.services.ats.structure_scorer import score_structure
from app.services.ats.summary_scorer import score_summary
from app.services.ats.skill_experience_scorer import score_skill_experience
from app.services.ats.readability_scorer import score_readability
from app.services.ats.page_density_scorer import score_page_density

log = logging.getLogger("ats.scorer")

# 5-category model: mirrors what real ATS filters (Workday/Taleo/Greenhouse) actually check.
# Human-recruiter signals (bullets, readability, career gaps) are computed for feedback
# but do not contribute to the headline score.
CATEGORY_WEIGHTS: dict[str, float] = {
    "keyword_match":    40.0,  # required (70%) + preferred (30%) coverage
    "experience":       20.0,  # years parsed vs years required
    "education":        15.0,  # degree level vs JD requirement
    "sections_present": 15.0,  # key sections parseable + no hard ATS format failures
    "resume_quality":   10.0,  # achievement density + bullet strength + summary (human signal)
}
assert abs(sum(CATEGORY_WEIGHTS.values()) - 100.0) < 0.1

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

    # Extract recent experience lines (last 3 years) for positional scorer
    current_year = datetime.date.today().year
    recent_cutoff = current_year - 3
    exp_text = resume_parsed.get("experience", "")
    recent_lines = [
        line for line in exp_text.split("\n")
        if re.findall(r'\b(20\d{2})\b', line) and
           max((int(y) for y in re.findall(r'\b(20\d{2})\b', line)), default=0) >= recent_cutoff
    ]
    recent_experience_text = "\n".join(recent_lines)

    pos_r, ont_r, exp_r, par_r, sem_r, word_r = await asyncio.gather(
        asyncio.to_thread(
            positional_scorer.positional_keyword_score,
            keywords, resume_parsed, synonym_map,
            recent_experience_text=recent_experience_text,
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

    # Synchronous fast scorers — run after gather
    achievement_data = score_achievements(resume_text)
    cert_data        = score_certifications(resume_text, jd_text)
    title_data       = score_title_match(resume_text, jd_text)

    # Get matched keywords list for context scoring
    matched_kw_list = list(pos_r.get("matched_keywords", {}).keys()) if isinstance(pos_r.get("matched_keywords"), dict) else []
    is_tech = any(w in jd_text.lower() for w in ["engineer","developer","software","python","java","cloud","data"])

    context_data = score_keyword_context(resume_text, matched_kw_list)
    contact_data = score_contact(resume_text, is_tech_role=is_tech)
    career_data  = analyze_career(resume_text)
    bullet_data  = analyze_bullets(resume_text)
    struct_data  = score_structure(resume_text, total_years=exp_r.get("total_years"))

    # Get required_missing list for summary and page density scorers
    req_missing_list = pos_r["required_missing"] if isinstance(pos_r.get("required_missing"), list) else []

    # When all required keywords are present (req_missing_list empty), check the full
    # required list so a well-written summary still gets credit for keyword coverage.
    summary_kw_list = req_missing_list if req_missing_list else list(keywords["required"])
    summary_data     = score_summary(resume_text, jd_text, summary_kw_list)
    skill_exp_data   = score_skill_experience(resume_text, jd_text)
    readability_data = score_readability(resume_text)
    page_data        = score_page_density(resume_text, req_missing_list)

    total_required = len(keywords["required"])
    total_preferred = len(keywords["preferred"])
    found_required = len(pos_r["required_matched"])
    found_preferred = len(pos_r["preferred_matched"])

    # --- 5-category ATS score ---
    # 1. Keyword Match (40%): required (70%) + preferred (30%) coverage
    req_pct  = (found_required  / total_required  * 100) if total_required  else 75.0
    pref_pct = (found_preferred / total_preferred * 100) if total_preferred else 75.0
    kw_score = round(req_pct * 0.7 + pref_pct * 0.3, 1)

    # 2. Experience (20%): years parsed vs requirement (from experience_parser)
    exp_score_val = exp_r["experience_score"]

    # 3. Education (15%): degree level match (from experience_parser)
    edu_score_val = exp_r["education_score"]

    # 4. Sections Present (15%): key sections parseable + no hard ATS format failures
    sections_score = par_r["score"]

    # 5. Resume Quality (10%): achievement density + bullet strength + summary
    #    Human-facing signal, clearly labeled. Does not simulate ATS behavior.
    quality_score = round(
        achievement_data["achievement_score"] * 0.4
        + bullet_data["bullet_quality_score"] * 0.4
        + summary_data["summary_score"]       * 0.2,
        1,
    )

    overall = round(
        kw_score       * CATEGORY_WEIGHTS["keyword_match"]    / 100
        + exp_score_val * CATEGORY_WEIGHTS["experience"]       / 100
        + edu_score_val * CATEGORY_WEIGHTS["education"]        / 100
        + sections_score * CATEGORY_WEIGHTS["sections_present"] / 100
        + quality_score  * CATEGORY_WEIGHTS["resume_quality"]   / 100,
        1,
    )

    # Hard floor for resumes missing >50% of required keywords
    req_miss_ratio = (total_required - found_required) / (total_required or 1)
    if req_miss_ratio > 0.5:
        penalty = int((req_miss_ratio - 0.5) * 40)
        overall = max(0, overall - penalty)

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
    suggestions += achievement_data["suggestions"]
    suggestions += cert_data["suggestions"]
    suggestions += title_data["suggestions"]
    suggestions += context_data["suggestions"]
    suggestions += contact_data["suggestions"]
    suggestions += career_data["suggestions"]
    suggestions += bullet_data["suggestions"]
    suggestions += struct_data["suggestions"]
    suggestions += summary_data["suggestions"]
    suggestions += skill_exp_data["suggestions"]
    suggestions += readability_data["suggestions"]
    suggestions += page_data["suggestions"]

    return {
        "overall_score": overall,
        "grade": grade,
        "categories": {
            "keyword_match": {
                "label": "Keyword Match",
                "score": kw_score,
                "weight": int(CATEGORY_WEIGHTS["keyword_match"]),
                "description": (
                    f"{found_required} of {total_required} required · "
                    f"{found_preferred} of {total_preferred} preferred"
                ),
            },
            "experience": {
                "label": "Experience",
                "score": exp_score_val,
                "weight": int(CATEGORY_WEIGHTS["experience"]),
                "description": (
                    f"{exp_r['total_years']} yrs found"
                    + (f" vs {exp_r['required_years']} required" if exp_r["required_years"] else "")
                ),
            },
            "education": {
                "label": "Education",
                "score": edu_score_val,
                "weight": int(CATEGORY_WEIGHTS["education"]),
                "description": "Degree level vs JD requirement",
            },
            "sections_present": {
                "label": "ATS Parsability",
                "score": sections_score,
                "weight": int(CATEGORY_WEIGHTS["sections_present"]),
                "description": (
                    f"Missing: {', '.join(par_r['sections_missing'])}"
                    if par_r["sections_missing"]
                    else "All key sections detected"
                ),
            },
            "resume_quality": {
                "label": "Resume Quality",
                "score": quality_score,
                "weight": int(CATEGORY_WEIGHTS["resume_quality"]),
                "description": (
                    f"{achievement_data['quant_count']} quantified bullets · "
                    f"{achievement_data['strong_verb_count']} strong verbs · "
                    f"{'summary found' if summary_data['summary_found'] else 'no summary'}"
                ),
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
        "achievement_data": {
            "quant_count": achievement_data["quant_count"],
            "total_bullets": achievement_data["total_bullets"],
            "strong_verb_count": achievement_data["strong_verb_count"],
            "weak_verb_count": achievement_data["weak_verb_count"],
            "quant_score": achievement_data["quant_score"],
            "verb_score": achievement_data["verb_score"],
        },
        "cert_data": {
            "resume_certs": cert_data["resume_certs"],
            "jd_certs": cert_data["jd_certs"],
            "matched": cert_data["matched"],
            "missing": cert_data["missing"],
        },
        "title_data": {
            "jd_title": title_data["jd_title"],
            "best_match": title_data["best_match"],
            "match_ratio": title_data["match_ratio"],
        },
        "context_data": {
            "passive_keywords": context_data["passive_keywords"],
            "active_count": context_data["active_count"],
            "passive_count": context_data["passive_count"],
        },
        "contact_data": contact_data,
        "career_data": {
            "gaps": career_data["gaps"],
            "max_gap_months": career_data["max_gap_months"],
            "avg_tenure_months": career_data["avg_tenure_months"],
            "short_tenure_roles": career_data["short_tenure_roles"],
        },
        "bullet_data": {
            "total_bullets": bullet_data["total_bullets"],
            "short_bullets": bullet_data["short_bullets"],
            "long_bullets": bullet_data["long_bullets"],
            "star_bullets": bullet_data["star_bullets"],
            "duplicate_pairs": bullet_data["duplicate_pairs"],
            "tense_issues": bullet_data["tense_issues"],
            "soft_skills_found": bullet_data["soft_skills_found"],
        },
        "structure_data": {
            "estimated_pages": struct_data["estimated_pages"],
            "expected_pages": struct_data["expected_pages"],
            "detected_section_order": struct_data["detected_section_order"],
        },
        "summary_data": {
            "summary_found": summary_data["summary_found"],
            "keywords_in_summary": summary_data.get("keywords_in_summary", []),
            "has_years_claim": summary_data.get("has_years_claim", False),
            "summary_word_count": summary_data.get("summary_word_count", 0),
        },
        "skill_exp_data": {
            "resume_skill_years": skill_exp_data["resume_skill_years"],
            "jd_requirements": skill_exp_data["jd_requirements"],
            "met": skill_exp_data["met"],
            "unmet": skill_exp_data["unmet"],
        },
        "readability_data": {
            "flesch_kincaid": readability_data["flesch_kincaid"],
            "repeated_phrases": readability_data["repeated_phrases"],
            "gpa": readability_data["gpa"],
            "date_format_score": readability_data["date_format_score"],
        },
        "page_data": {
            "keywords_on_page1": page_data["keywords_on_page1"],
            "keywords_missing_p1": page_data["keywords_missing_p1"],
            "known_companies_found": page_data["known_companies_found"],
            "skill_grouping_score": page_data["skill_grouping_score"],
        },
        "resume_text": resume_text,
    }
