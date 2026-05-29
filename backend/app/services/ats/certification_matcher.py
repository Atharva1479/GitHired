"""Extract certifications from resume and match against JD mentions."""
from __future__ import annotations
import re

KNOWN_CERTS: list[str] = [
    # Cloud — AWS
    "aws certified", "aws solutions architect", "aws developer",
    "aws sysops", "aws devops", "aws cloud practitioner", "aws data analytics",
    "aws machine learning",
    # Cloud — GCP / Azure
    "google cloud", "gcp professional", "azure administrator",
    "azure developer", "azure solutions architect", "azure devops",
    "microsoft certified",
    # DevOps / Infra
    "cka", "ckad", "cks", "certified kubernetes",
    "docker certified", "terraform associate", "hashicorp certified",
    "red hat", "rhce", "rhcsa",
    # Project / Agile
    "pmp", "prince2", "csm", "safe agilist", "scrum master",
    "certified product owner", "cppo", "psm",
    # Security
    "cissp", "ceh", "oscp", "cism", "cisa",
    "comptia security", "comptia network", "comptia a+",
    # Data / ML
    "tensorflow developer", "databricks certified",
    "snowflake certified", "tableau desktop", "power bi",
    # Other
    "salesforce", "servicenow", "oracle certified", "java se",
    "istqb", "six sigma",
]

_NUMBERED_CERT_RE = re.compile(r'\b[A-Z]{2,8}[-\s]?\d{3,6}\b')


def _extract_certs(text: str) -> list[str]:
    lower  = text.lower()
    found  = [c for c in KNOWN_CERTS if c in lower]
    found += _NUMBERED_CERT_RE.findall(text)
    return list(dict.fromkeys(found))


def score_certifications(resume_text: str, jd_text: str) -> dict:
    """Compare resume certifications against JD-required certifications."""
    resume_certs = _extract_certs(resume_text)
    jd_certs     = _extract_certs(jd_text)

    if not jd_certs:
        return {
            "cert_score": 100,
            "resume_certs": resume_certs,
            "jd_certs": [],
            "matched": [],
            "missing": [],
            "suggestions": [],
        }

    matched = [
        c for c in jd_certs
        if any(c in rc or rc in c for rc in resume_certs)
    ]
    missing = [c for c in jd_certs if c not in matched]
    score   = int(len(matched) / len(jd_certs) * 100)

    suggestions: list[str] = []
    if missing:
        names = ", ".join(m.upper() for m in missing[:3])
        suggestions.append(
            f"JD requires certifications not on your resume: {names}. "
            "Add them if you hold them, or note them as in-progress."
        )

    return {
        "cert_score": score,
        "resume_certs": resume_certs,
        "jd_certs": jd_certs,
        "matched": matched,
        "missing": missing,
        "suggestions": suggestions,
    }
