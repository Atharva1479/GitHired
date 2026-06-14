import re

_MULTI_COL_RE = re.compile(r'[ \t]{8,}([A-Za-z])')
# "Languages:    Java, Python" — skills table label-value pair, NOT multi-column
_SKILLS_LABEL_RE = re.compile(r'^\s*[\w][\w\s,&/]+:\s{4,}', re.IGNORECASE)


def _detect_multi_column(text: str) -> bool:
    # True two-column layout: both the content before AND after the large gap are
    # substantial (≥25 chars each). This excludes:
    #   - "Languages:    Java, Python…" (label-value skills table)
    #   - "IQ Innovation Hub LLP    May 2025 – Present" (company+date row, date ≤18 chars)
    # A genuine two-column resume has two full-length text blocks side by side.
    def _is_two_col(line: str) -> bool:
        if _SKILLS_LABEL_RE.match(line):
            return False
        m = _MULTI_COL_RE.search(line)
        if not m:
            return False
        before = line[:m.start()].strip()
        after = line[m.end() - 1:].strip()   # include the letter that matched
        return len(before) >= 15 and len(after) >= 25

    lines_with_gap = sum(1 for line in text.split('\n') if len(line) > 40 and _is_two_col(line))
    return lines_with_gap > 5


def _detect_special_chars(text: str) -> bool:
    special = sum(1 for c in text if ord(c) > 9000)
    return special > 10


def _detect_very_short_lines(text: str) -> bool:
    lines = [l for l in text.split('\n') if l.strip()]
    if not lines:
        return False
    short = sum(1 for l in lines if len(l.strip()) < 20)
    return short / len(lines) > 0.45


def check_parsability(resume_text: str, resume_parsed: dict) -> dict:
    ats_risks: list[str] = []
    sections_found = [
        s for s, v in resume_parsed.items() if v and len(str(v).strip()) > 20
    ]
    required_sections = ["experience", "education", "skills"]
    sections_missing = [
        s for s in required_sections if not resume_parsed.get(s, "").strip()
    ]

    # Base score: deduct for missing sections and each risk (10 pts each)
    score = 100 - len(sections_missing) * 20

    if len(resume_text.split()) < 150:
        ats_risks.append(
            "Very short resume or image-based PDF — ATS cannot extract content"
        )

    if not re.search(r'[\w.+-]+@[\w-]+\.[a-z]{2,}', resume_text):
        ats_risks.append(
            "No email address found — ATS cannot create candidate profile"
        )

    if not re.search(r'[\+\(]?[\d\s\-\(\)]{7,15}', resume_text):
        ats_risks.append("No phone number detected")

    if "skills" not in sections_found:
        ats_risks.append(
            "No Skills section — ATS gives this section 2.5× keyword weight"
        )

    if resume_text.count("|") > 8 or resume_text.count("│") > 4:
        ats_risks.append(
            "Pipe characters suggest table formatting — convert to bullet points"
        )
        score -= 20

    # Deduct 10 pts for each of the base risks collected so far
    score -= len(ats_risks) * 10

    # New hard-format checks with explicit penalties
    if _detect_multi_column(resume_text):
        ats_risks.append(
            "HARD WARNING: Multi-column layout detected — most ATS parse this as garbled text. "
            "Switch to a single-column format."
        )
        score -= 25

    if _detect_special_chars(resume_text):
        ats_risks.append(
            "Special Unicode/graphical characters detected — ATS may fail to parse them."
        )
        score -= 10

    if _detect_very_short_lines(resume_text):
        ats_risks.append(
            "Many very short lines detected — possible header/footer or decorative section "
            "dividers that ATS may misparse."
        )
        score -= 8

    score = max(0, score)

    return {
        "score": score,
        "sections_found": sections_found,
        "sections_missing": sections_missing,
        "ats_risks": ats_risks,
    }
