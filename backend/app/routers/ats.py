from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.deps import get_user_id
from app.services.ats.ai_feedback import generate_ats_feedback
from app.services.ats.resume_tailor import generate_tailor_suggestions
from app.services.ats.scorer import analyze_resume
from app.services.ats.text_extractor import extract_text_from_bytes

router = APIRouter()


class ATSFeedbackRequest(BaseModel):
    overall_score: float
    required_missing: list[str] = []
    preferred_missing: list[str] = []
    sections_found: list[str] = []
    sections_missing: list[str] = []
    ats_risks: list[str] = []
    suggestions: list[str] = []


class ATSTailorRequest(BaseModel):
    resume_text: str
    jd_text: str
    required_missing: list[str] = []
    preferred_missing: list[str] = []


@router.post("/ai-feedback")
async def ai_feedback(
    body: ATSFeedbackRequest,
    user_id: int = Depends(get_user_id),
) -> JSONResponse:
    result = await generate_ats_feedback(body.model_dump())
    return JSONResponse(content=result)


@router.post("/tailor")
async def tailor_resume(
    body: ATSTailorRequest,
    user_id: int = Depends(get_user_id),
) -> JSONResponse:
    """Rewrite specific resume bullets to incorporate missing ATS keywords.

    Returns a list of {section, original, rewritten, keywords_added, rationale} objects.
    Requires resume_text >= 50 chars and at least one missing keyword.
    """
    if len(body.resume_text.strip()) < 50:
        raise HTTPException(400, "resume_text too short")
    if not body.required_missing and not body.preferred_missing:
        return JSONResponse(content={"suggestions": []})

    suggestions = await generate_tailor_suggestions(
        resume_text=body.resume_text,
        jd_text=body.jd_text,
        required_missing=body.required_missing,
        preferred_missing=body.preferred_missing,
    )
    return JSONResponse(content={"suggestions": suggestions})


@router.post("/analyze")
async def analyze(
    job_description: str = Form(...),
    file: UploadFile | None = File(None),
    resume_text: str | None = Form(None),
    user_id: int = Depends(get_user_id),
) -> JSONResponse:
    """
    Analyze a resume against a job description and return a comprehensive ATS score.

    Supply either a file upload (.pdf, .docx, .txt) or a raw resume_text string.
    job_description is always required as a plain-text form field.
    Also returns resume_text (extracted from file or passed directly) so the
    client can use it for the resume tailor feature without re-uploading.
    """
    if not file and not resume_text:
        raise HTTPException(400, "Provide either a file or resume_text")
    if not job_description.strip():
        raise HTTPException(400, "job_description is required")

    if file:
        content = await file.read()
        if len(content) > 5 * 1024 * 1024:
            raise HTTPException(400, "File exceeds 5 MB limit")
        text = await extract_text_from_bytes(content, file.filename or "")
    else:
        text = resume_text or ""
        if len(text.strip()) < 50:
            raise HTTPException(400, "resume_text too short")

    result = await analyze_resume(text, job_description)
    result["resume_text"] = text   # included for resume tailor feature
    return JSONResponse(content=result)
