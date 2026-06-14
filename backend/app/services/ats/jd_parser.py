import re

REQUIRED_MARKERS = [
    "requirements", "required", "must have", "must-have", "qualifications",
    "what you need", "you will need", "minimum qualifications",
    "basic qualifications", "what we're looking for", "what we are looking for",
    "you have", "you bring",
]
PREFERRED_MARKERS = [
    "preferred", "nice to have", "nice-to-have", "bonus", "plus",
    "desired", "ideal", "additional", "advantageous", "not required but",
    "would be great", "good to have", "good-to-have", "great to have",
    "great-to-have", "added advantage", "is a plus", "will be a plus",
]
RESPONSIBILITIES_MARKERS = [
    "responsibilities", "what you'll do", "what you will do", "the role",
    "your role", "day to day", "duties", "about the role", "you will",
    "in this role", "what you do", "key responsibilities", "your responsibilities",
    "role overview",
]
IGNORE_MARKERS = [
    "about us", "about the company", "who we are", "benefits",
    "perks", "compensation", "equal opportunity", "eeo", "diversity",
    "our culture", "why join", "job summary", "about the job",
    "about this role", "overview", "position summary", "role summary",
]


def _detect_section(line: str) -> str | None:
    clean = line.strip().lower().rstrip(":").strip()
    if len(clean) > 80 or not clean:
        return None
    # Preferred checked before required: "good-to-have qualifications" contains both
    # "good-to-have" (preferred) and "qualifications" (required) — preferred wins.
    for m in PREFERRED_MARKERS:
        if m in clean:
            return "preferred"
    for m in REQUIRED_MARKERS:
        if m in clean:
            return "required"
    for m in RESPONSIBILITIES_MARKERS:
        if m in clean:
            return "context"
    for m in IGNORE_MARKERS:
        if m in clean:
            return "ignore"
    return None


def _extract_title(text: str) -> str:
    for line in text.split("\n")[:8]:
        stripped = line.strip()
        if not stripped:
            continue
        lower = stripped.lower()
        for marker in ["position:", "role:", "title:", "job title:"]:
            if lower.startswith(marker):
                return stripped.split(":", 1)[-1].strip()
        # First short non-sentence line is likely the title
        if len(stripped) < 80 and len(stripped.split()) <= 8:
            return stripped
    return ""


def parse_jd(jd_text: str) -> dict[str, str]:
    jd_title = _extract_title(jd_text)
    lines = jd_text.split("\n")

    sections: dict[str, list[str]] = {
        "required": [], "preferred": [], "context": [], "ignored": []
    }
    current = "required"  # default if no sections detected

    has_structure = False
    for line in lines:
        detected = _detect_section(line)
        if detected:
            has_structure = True
            current = detected
        else:
            if current != "ignore":
                sections[current].append(line)

    if not has_structure:
        # Unstructured JD — treat everything as required
        sections["required"] = lines

    return {
        "required_text": "\n".join(sections["required"]).strip(),
        "preferred_text": "\n".join(sections["preferred"]).strip(),
        "context_text": "\n".join(sections["context"]).strip(),
        "full_text": jd_text,
        "jd_title": jd_title,
    }
