import re

SECTION_PATTERNS: dict[str, list[str]] = {
    "summary": [
        "summary", "objective", "profile", "about me", "professional summary",
        "career objective", "overview",
    ],
    "experience": [
        "experience", "work experience", "employment", "work history", "career",
        "professional experience", "employment history",
    ],
    "education": [
        "education", "academic background", "academic history", "qualifications",
        "academic qualifications",
    ],
    "skills": [
        "skills", "technical skills", "core competencies", "technologies", "expertise",
        "proficiencies", "tech stack", "competencies",
    ],
    "certifications": [
        "certifications", "certificates", "licenses", "accreditations",
        "professional development", "credentials",
    ],
    "projects": [
        "projects", "personal projects", "key projects", "notable projects", "portfolio",
    ],
}


def _is_section_heading(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or len(stripped) > 60:
        return None
    words = stripped.split()
    if len(words) > 6:
        return None
    clean = re.sub(r'[^a-zA-Z\s]', ' ', stripped).lower().strip()
    for section, patterns in SECTION_PATTERNS.items():
        for pattern in patterns:
            if pattern == clean or clean.startswith(pattern):
                return section
    return None


def parse_resume(text: str) -> dict[str, str]:
    lines = text.split("\n")
    result: dict[str, list[str]] = {s: [] for s in SECTION_PATTERNS}
    result["contact"] = []
    result["other"] = []

    # Everything before the first detected section heading = contact block.
    # Do NOT hardcode a line count — compact resumes have sections as early as line 3.
    current_section = "contact"

    for line in lines:
        detected = _is_section_heading(line)
        if detected:
            current_section = detected
        else:
            result.get(current_section, result["other"]).append(line)

    return {k: "\n".join(v).strip() for k, v in result.items()}
