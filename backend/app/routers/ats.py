from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services.ats.ai_feedback import generate_ats_feedback
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


@router.post("/ai-feedback")
async def ai_feedback(body: ATSFeedbackRequest) -> JSONResponse:
    result = await generate_ats_feedback(body.model_dump())
    return JSONResponse(content=result)


@router.post("/analyze")
async def analyze(
    job_description: str = Form(...),
    file: UploadFile | None = File(None),
    resume_text: str | None = Form(None),
) -> JSONResponse:
    """
    Analyze a resume against a job description and return a comprehensive ATS score.

    Supply either a file upload (.pdf, .docx, .txt) or a raw resume_text string.
    job_description is always required as a plain-text form field.
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
    return JSONResponse(content=result)
