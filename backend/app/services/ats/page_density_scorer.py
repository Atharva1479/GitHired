"""Page-1 keyword density, skill grouping quality, company tier signals."""
from __future__ import annotations
import re

KNOWN_COMPANIES = {
    "google","meta","facebook","amazon","apple","microsoft","netflix","openai",
    "anthropic","deepmind","nvidia","tesla","spacex","stripe","airbnb","uber",
    "lyft","twitter","linkedin","salesforce","adobe","oracle","ibm",
    "atlassian","shopify","square","block","twilio","datadog","snowflake",
    "databricks","palantir","coinbase","robinhood","doordash","instacart",
    "mongodb","elastic","hashicorp","cloudflare","fastly","confluent",
    "infosys","tcs","wipro","hcl","tech mahindra","cognizant","accenture",
    "capgemini","deloitte","pwc","kpmg","ey","mckinsey","bcg","bain",
    "goldman sachs","jp morgan","morgan stanley","blackrock","citadel",
    "two sigma","jane street","optiver","de shaw",
}

_SKILL_GROUP_RE = re.compile(
    r'(?:^|\n)\s*([A-Z][A-Za-z\s]{2,25}):\s*([A-Za-z].{10,})',
    re.MULTILINE,
)
_SKILLS_BLOCK_RE = re.compile(
    r'(?:skills?|technologies|tech stack|competencies)\s*\n([\s\S]{0,800}?)(?=\n[A-Z][A-Za-z\s]{1,25}\n|\Z)',
    re.IGNORECASE,
)

PAGE1_WORDS = 500


def _page1_text(resume_text: str) -> str:
    return " ".join(resume_text.split()[:PAGE1_WORDS])


def _page1_keyword_density(resume_text: str, required_keywords: list[str]) -> tuple[int, list[str], list[str]]:
    page1 = _page1_text(resume_text).lower()
    on_p1 = [k for k in required_keywords if k.lower() in page1]
    missing = [k for k in required_keywords if k.lower() not in page1]
    ratio = len(on_p1) / max(len(required_keywords), 1)
    score = min(100, int(ratio * 120))
    return score, on_p1, missing


def _skill_grouping_score(resume_text: str) -> tuple[int, str | None]:
    skills_m = _SKILLS_BLOCK_RE.search(resume_text)
    if not skills_m:
        return 70, None
    skills_block = skills_m.group(1)
    groups = _SKILL_GROUP_RE.findall(skills_block)
    if len(groups) >= 2:
        return 100, None
    lines = [l.strip() for l in skills_block.split('\n') if l.strip()]
    if len(lines) <= 2 and any(',' in l for l in lines):
        return 65, (
            "Skills listed as an ungrouped comma-separated list. "
            "Group them by category: Languages: | Frameworks: | Cloud: | Tools:"
        )
    return 80, None


def _company_tier_score(resume_text: str) -> tuple[int, list[str]]:
    lower = resume_text.lower()
    found = [c for c in KNOWN_COMPANIES if c in lower]
    score = min(100, 70 + len(found) * 10)
    return score, found


def score_page_density(resume_text: str, required_keywords: list[str]) -> dict:
    p1_score, on_p1, missing_p1 = _page1_keyword_density(resume_text, required_keywords)
    group_score, group_issue = _skill_grouping_score(resume_text)
    tier_score, known_cos = _company_tier_score(resume_text)

    combined = int(p1_score * 0.50 + group_score * 0.30 + tier_score * 0.20)

    suggestions: list[str] = []
    if missing_p1 and len(missing_p1) > len(required_keywords) * 0.4:
        suggestions.append(
            f"{len(missing_p1)} required keywords not on page 1. "
            "ATS weight page 1 higher — move key skills to your summary or first experience role."
        )
    if group_issue:
        suggestions.append(group_issue)
    if not known_cos:
        suggestions.append(
            "No well-known company names detected. If you've worked at recognizable companies, "
            "spell out the full official name — ATS use employer reputation signals."
        )

    return {
        "page_density_score": combined,
        "p1_keyword_score": p1_score,
        "keywords_on_page1": on_p1,
        "keywords_missing_p1": missing_p1,
        "skill_grouping_score": group_score,
        "company_tier_score": tier_score,
        "known_companies_found": known_cos,
        "suggestions": suggestions,
    }
