import re


def check_parsability(resume_text: str, resume_parsed: dict) -> dict:
    ats_risks: list[str] = []
    sections_found = [
        s for s, v in resume_parsed.items() if v and len(str(v).strip()) > 20
    ]
    required_sections = ["experience", "education", "skills"]
    sections_missing = [
        s for s in required_sections if not resume_parsed.get(s, "").strip()
    ]

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

    if len(re.findall(r' {3,}', resume_text)) > 10:
        ats_risks.append(
            "Multiple large spaces — possible table layout, ATS will misparse"
        )

    if "skills" not in sections_found:
        ats_risks.append(
            "No Skills section — ATS gives this section 2.5× keyword weight"
        )

    if resume_text.count("|") > 8 or resume_text.count("│") > 4:
        ats_risks.append(
            "Pipe characters suggest table formatting — convert to bullet points"
        )

    score = max(0, 100 - len(sections_missing) * 20 - len(ats_risks) * 10)
    return {
        "score": score,
        "sections_found": sections_found,
        "sections_missing": sections_missing,
        "ats_risks": ats_risks,
    }
