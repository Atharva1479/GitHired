"""Score contact information completeness."""
from __future__ import annotations
import re

_EMAIL_RE    = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
_PHONE_RE    = re.compile(r'[\+\(]?[\d\s\-\(\)]{7,15}\d')
_LINKEDIN_RE = re.compile(r'linkedin\.com/in/[\w\-]+', re.IGNORECASE)
_GITHUB_RE   = re.compile(r'github\.com/[\w\-]+', re.IGNORECASE)
_LOCATION_RE = re.compile(
    r'\b(?:[A-Z][a-z]+(?:\s[A-Z][a-z]+)?),\s*(?:[A-Z]{2}|[A-Z][a-z]+)\b'
    r'|\b(?:Remote|Hybrid|On-?site)\b',
    re.IGNORECASE,
)


def score_contact(resume_text: str, is_tech_role: bool = True) -> dict:
    contact_block = resume_text[:800]

    has_email    = bool(_EMAIL_RE.search(contact_block))
    has_phone    = bool(_PHONE_RE.search(contact_block))
    has_linkedin = bool(_LINKEDIN_RE.search(contact_block))
    has_github   = bool(_GITHUB_RE.search(contact_block))
    has_location = bool(_LOCATION_RE.search(contact_block))

    fields = {
        "email":    (has_email,    20, "Email address"),
        "phone":    (has_phone,    20, "Phone number"),
        "linkedin": (has_linkedin, 25, "LinkedIn URL (linkedin.com/in/...)"),
        "location": (has_location, 15, "City/State or Remote"),
        "github":   (has_github,   20 if is_tech_role else 10, "GitHub URL"),
    }

    total_weight = sum(w for _, (_, w, _) in fields.items())
    earned = sum(w for _, (present, w, _) in fields.items() if present)
    score = int(earned / total_weight * 100)

    missing = [label for _, (present, _, label) in fields.items() if not present]
    suggestions: list[str] = []
    if missing:
        suggestions.append(
            f"Contact section missing: {', '.join(missing)}. "
            "ATS systems extract and score contact completeness."
        )
    if not has_linkedin:
        suggestions.append("Add your LinkedIn URL — most ATS use it to verify identity and pull additional profile data.")
    if is_tech_role and not has_github:
        suggestions.append("GitHub URL strongly recommended for tech roles — add it to your contact section.")

    return {
        "contact_score": score,
        "has_email": has_email,
        "has_phone": has_phone,
        "has_linkedin": has_linkedin,
        "has_github": has_github,
        "has_location": has_location,
        "missing_fields": missing,
        "suggestions": suggestions,
    }
