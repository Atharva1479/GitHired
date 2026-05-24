import json
import os
from functools import lru_cache

_DATA_PATH = os.path.join(os.path.dirname(__file__), "../../data/ats/esco_skills.json")


@lru_cache(maxsize=1)
def _load() -> dict:
    with open(_DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_all_skills() -> set[str]:
    data = _load()
    skills: set[str] = set()
    for cat in ["ict_skills", "data_skills", "engineering_skills", "soft_skills"]:
        skills.update(data.get(cat, []))
    return skills


def get_synonym_map() -> dict[str, list[str]]:
    return _load().get("synonyms", {})


def get_degree_keywords() -> list[str]:
    return _load().get("degree_keywords", [])


def get_occupation_skills(jd_title: str) -> list[str]:
    if not jd_title:
        return []
    try:
        from rapidfuzz import process
    except ImportError:
        return []
    occupations: dict[str, list[str]] = _load().get("occupation_skills", {})
    if not occupations:
        return []
    result = process.extractOne(jd_title, list(occupations.keys()), score_cutoff=72)
    if result:
        return occupations[result[0]]
    return []
