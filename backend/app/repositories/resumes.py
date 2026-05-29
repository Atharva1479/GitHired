from __future__ import annotations

import asyncpg

from app.models import ResumeOut


async def create_resume(
    conn: asyncpg.Connection,
    user_id: int,
    name: str,
    role_tag: str,
    file_name: str,
    parsed_text: str,
) -> ResumeOut:
    row = await conn.fetchrow(
        """
        INSERT INTO resumes (user_id, name, role_tag, file_name, parsed_text)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, user_id, name, role_tag, file_name, created_at
        """,
        user_id, name, role_tag, file_name, parsed_text,
    )
    return ResumeOut.model_validate(dict(row))


async def list_resumes(conn: asyncpg.Connection, user_id: int) -> list[ResumeOut]:
    rows = await conn.fetch(
        """
        SELECT id, user_id, name, role_tag, file_name, created_at
        FROM resumes
        WHERE user_id = $1 AND deleted_at IS NULL
        ORDER BY created_at DESC
        """,
        user_id,
    )
    return [ResumeOut.model_validate(dict(r)) for r in rows]


async def get_resume(
    conn: asyncpg.Connection, resume_id: int, user_id: int
) -> ResumeOut | None:
    row = await conn.fetchrow(
        """
        SELECT id, user_id, name, role_tag, file_name, created_at
        FROM resumes
        WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL
        """,
        resume_id, user_id,
    )
    return ResumeOut.model_validate(dict(row)) if row else None


async def get_resume_text(
    conn: asyncpg.Connection, resume_id: int, user_id: int
) -> str | None:
    row = await conn.fetchrow(
        "SELECT parsed_text FROM resumes WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL",
        resume_id, user_id,
    )
    return row["parsed_text"] if row else None


async def soft_delete_resume(
    conn: asyncpg.Connection, resume_id: int, user_id: int
) -> None:
    await conn.execute(
        "UPDATE resumes SET deleted_at = now() WHERE id = $1 AND user_id = $2",
        resume_id, user_id,
    )


async def get_jd_texts_for_role(
    conn: asyncpg.Connection, user_id: int, role_keywords: list[str]
) -> list[str]:
    """Return jd_text for active applications whose role matches any keyword."""
    if not role_keywords:
        return []
    conditions = " OR ".join(f"role ILIKE ${i+2}" for i in range(len(role_keywords)))
    params: list = [user_id] + [f"%{kw}%" for kw in role_keywords]
    rows = await conn.fetch(
        f"""
        SELECT jd_text FROM applications
        WHERE user_id = $1
          AND deleted_at IS NULL
          AND jd_text IS NOT NULL
          AND jd_text != ''
          AND ({conditions})
        """,
        *params,
    )
    return [r["jd_text"] for r in rows]
