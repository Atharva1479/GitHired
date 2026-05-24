from pathlib import Path
from typing import Literal

import asyncpg
from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from fastapi.responses import FileResponse

from app.config import settings
from app.deps import get_db, get_user_id
from app.exceptions import NotFound
from app.repositories import applications as repo
from app.repositories.events import emit

router = APIRouter()

FileKind = Literal["jd", "resume", "cover_letter"]
_KIND_TO_ATTR = {
    "jd": "jd_file_name",
    "resume": "resume_file_name",
    "cover_letter": "cover_letter_file_name",
}


def _file_path(user_id: int, app_id: int, kind: FileKind) -> Path:
    base: Path = settings.upload_dir
    return base / str(user_id) / str(app_id) / f"{kind}.pdf"


def _safe_filename(raw: str) -> str:
    name = Path(raw).name.replace("\\", "").strip() or "file.pdf"
    if not name.lower().endswith(".pdf"):
        name = f"{name}.pdf"
    return name[:200]


@router.post("/{app_id}/files/{kind}", status_code=status.HTTP_201_CREATED)
async def upload_file(
    app_id: int,
    kind: FileKind,
    file: UploadFile = File(...),
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
):
    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        return Response(
            status_code=415,
            content=f'{{"type":"unsupported_media","title":"PDF only","detail":"got {file.content_type}","status":415}}',
            media_type="application/json",
        )

    await repo.get_application(conn, app_id, user_id)  # 404 if missing
    body = await file.read(settings.max_upload_bytes + 1)
    if len(body) > settings.max_upload_bytes:
        return Response(
            status_code=413,
            content=f'{{"type":"too_large","title":"File too large","detail":"max {settings.max_upload_bytes} bytes","status":413}}',
            media_type="application/json",
        )

    path = _file_path(user_id, app_id, kind)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)

    original = _safe_filename(file.filename or f"{kind}.pdf")
    async with conn.transaction():
        out = await repo.set_file_name(conn, app_id, user_id, kind, original)
        await emit(conn, user_id, "application.file_uploaded", {
            "application_id": app_id, "kind": kind, "file_name": original,
        })
    return out


@router.get("/{app_id}/files/{kind}")
async def get_file(
    app_id: int,
    kind: FileKind,
    download: bool = Query(default=False),
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
):
    app = await repo.get_application(conn, app_id, user_id)
    original = getattr(app, _KIND_TO_ATTR[kind])
    if not original:
        raise NotFound(f"{kind} file not set")

    path = _file_path(user_id, app_id, kind)
    if not path.exists():
        raise NotFound(f"{kind} file missing on disk")

    return FileResponse(
        path,
        media_type="application/pdf",
        filename=original,
        content_disposition_type="attachment" if download else "inline",
    )


@router.delete("/{app_id}/files/{kind}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    app_id: int,
    kind: FileKind,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> Response:
    await repo.get_application(conn, app_id, user_id)
    path = _file_path(user_id, app_id, kind)
    if path.exists():
        path.unlink()
    async with conn.transaction():
        await repo.set_file_name(conn, app_id, user_id, kind, None)
        await emit(conn, user_id, "application.file_deleted", {
            "application_id": app_id, "kind": kind,
        })
    return Response(status_code=status.HTTP_204_NO_CONTENT)
