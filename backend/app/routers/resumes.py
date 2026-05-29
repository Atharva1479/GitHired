from __future__ import annotations

from pathlib import Path

import asyncpg
from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse

from app.config import settings
from app.deps import get_db, get_user_id
from app.models import ResumeOut, SkillGap, SkillGapResult
from app.repositories import resumes as repo
from app.services.ats.text_extractor import extract_text_from_bytes
from app.services.skill_gap import analyze_gap, extract_role_keywords

router = APIRouter(prefix="/resumes", tags=["resumes"])


def _resume_file_path(user_id: int, resume_id: int) -> Path:
    return settings.upload_dir / str(user_id) / "resumes" / f"{resume_id}.pdf"


@router.post("", response_model=ResumeOut, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    name: str = Form(...),
    role_tag: str = Form(...),
    file: UploadFile = File(...),
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
):
    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(415, "PDF only")

    body = await file.read(settings.max_upload_bytes + 1)
    if len(body) > settings.max_upload_bytes:
        raise HTTPException(413, f"Max {settings.max_upload_bytes} bytes")

    parsed_text = await extract_text_from_bytes(body, file.filename or "resume.pdf")
    original = (Path(file.filename or "resume.pdf").name[:200]) if file.filename else "resume.pdf"

    resume = await repo.create_resume(conn, user_id, name.strip(), role_tag.strip(), original, parsed_text)

    path = _resume_file_path(user_id, resume.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)

    return resume


@router.get("", response_model=list[ResumeOut])
async def list_resumes(
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
):
    return await repo.list_resumes(conn, user_id)


@router.get("/{resume_id}/file")
async def get_resume_file(
    resume_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
):
    resume = await repo.get_resume(conn, resume_id, user_id)
    if not resume:
        raise HTTPException(404, "Resume not found")
    path = _resume_file_path(user_id, resume_id)
    if not path.exists():
        raise HTTPException(404, "File not found on disk")
    return FileResponse(path, media_type="application/pdf", filename=resume.file_name)


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
    resume_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> Response:
    resume = await repo.get_resume(conn, resume_id, user_id)
    if not resume:
        raise HTTPException(404, "Resume not found")
    await repo.soft_delete_resume(conn, resume_id, user_id)
    path = _resume_file_path(user_id, resume_id)
    if path.exists():
        path.unlink()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{resume_id}/gap", response_model=SkillGapResult)
async def get_skill_gap(
    resume_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
):
    resume = await repo.get_resume(conn, resume_id, user_id)
    if not resume:
        raise HTTPException(404, "Resume not found")

    resume_text = await repo.get_resume_text(conn, resume_id, user_id)
    if not resume_text:
        raise HTTPException(422, "Resume text could not be extracted")

    keywords = extract_role_keywords(resume.role_tag)
    jd_texts = await repo.get_jd_texts_for_role(conn, user_id, keywords)

    raw_gaps = analyze_gap(resume_text, jd_texts)
    gaps = [SkillGap(**g) for g in raw_gaps[:30]]

    return SkillGapResult(
        resume_id=resume.id,
        resume_name=resume.name,
        role_tag=resume.role_tag,
        matched_jobs=len(jd_texts),
        gaps=gaps,
    )
