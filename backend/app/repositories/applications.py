from datetime import date

import asyncpg

from app.exceptions import NotFound
from app.models import ApplicationCreate, ApplicationOut, ApplicationUpdate

_COLS = """
    id, company, role, source, status, applied_date, last_updated,
    jd_url, salary_discussed, contact_name, contact_linkedin,
    fit_score, notes, follow_up_count, last_followed_up_at, created_at,
    jd_text, jd_file_name, resume_file_name, cover_letter_file_name
"""


def _row_to_out(row: asyncpg.Record) -> ApplicationOut:
    return ApplicationOut.model_validate(dict(row))


async def list_applications(
    conn: asyncpg.Connection,
    user_id: int,
    *,
    status: str | None = None,
    source: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 200,
) -> list[ApplicationOut]:
    clauses = ["user_id = $1", "deleted_at IS NULL"]
    args: list[object] = [user_id]
    if status:
        clauses.append(f"status = ${len(args) + 1}")
        args.append(status)
    if source:
        clauses.append(f"source = ${len(args) + 1}")
        args.append(source)
    if date_from:
        clauses.append(f"applied_date >= ${len(args) + 1}")
        args.append(date_from)
    if date_to:
        clauses.append(f"applied_date <= ${len(args) + 1}")
        args.append(date_to)
    args.append(limit)
    sql = (
        f"SELECT {_COLS} FROM applications "
        f"WHERE {' AND '.join(clauses)} "
        f"ORDER BY last_updated DESC LIMIT ${len(args)}"
    )
    rows = await conn.fetch(sql, *args)
    return [_row_to_out(r) for r in rows]


async def get_application(
    conn: asyncpg.Connection, app_id: int, user_id: int
) -> ApplicationOut:
    row = await conn.fetchrow(
        f"SELECT {_COLS} FROM applications "
        "WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL",
        app_id, user_id,
    )
    if not row:
        raise NotFound(f"application id={app_id}")
    return _row_to_out(row)


async def create_application(
    conn: asyncpg.Connection, user_id: int, data: ApplicationCreate
) -> ApplicationOut:
    row = await conn.fetchrow(
        f"""
        INSERT INTO applications (
            user_id, company, role, source, applied_date,
            jd_url, jd_text, salary_discussed, contact_name, contact_linkedin,
            fit_score, notes
        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
        RETURNING {_COLS}
        """,
        user_id,
        data.company,
        data.role,
        data.source,
        data.applied_date,
        str(data.jd_url) if data.jd_url else None,
        data.jd_text,
        data.salary_discussed,
        data.contact_name,
        str(data.contact_linkedin) if data.contact_linkedin else None,
        data.fit_score,
        data.notes,
    )
    return _row_to_out(row)


async def update_application(
    conn: asyncpg.Connection,
    app_id: int,
    user_id: int,
    patch: ApplicationUpdate,
) -> tuple[ApplicationOut, ApplicationOut]:
    """Returns (before, after). Caller uses the diff for event emission."""
    before = await get_application(conn, app_id, user_id)

    fields = patch.model_dump(exclude_unset=True)
    if not fields:
        return before, before

    sets: list[str] = []
    args: list[object] = []
    for key, value in fields.items():
        sets.append(f"{key} = ${len(args) + 1}")
        if key in {"jd_url", "contact_linkedin"} and value is not None:
            value = str(value)
        args.append(value)
    sets.append("last_updated = NOW()")

    args.extend([app_id, user_id])
    row = await conn.fetchrow(
        f"UPDATE applications SET {', '.join(sets)} "
        f"WHERE id = ${len(args) - 1} AND user_id = ${len(args)} "
        f"AND deleted_at IS NULL RETURNING {_COLS}",
        *args,
    )
    if not row:
        raise NotFound(f"application id={app_id}")
    return before, _row_to_out(row)


async def soft_delete_application(
    conn: asyncpg.Connection, app_id: int, user_id: int
) -> None:
    result = await conn.execute(
        "UPDATE applications SET deleted_at = NOW() "
        "WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL",
        app_id, user_id,
    )
    if result.endswith(" 0"):
        raise NotFound(f"application id={app_id}")


_FILE_COL = {
    "jd": "jd_file_name",
    "resume": "resume_file_name",
    "cover_letter": "cover_letter_file_name",
}


async def set_file_name(
    conn: asyncpg.Connection,
    app_id: int,
    user_id: int,
    kind: str,
    file_name: str | None,
) -> ApplicationOut:
    col = _FILE_COL[kind]
    row = await conn.fetchrow(
        f"UPDATE applications SET {col} = $1, last_updated = NOW() "
        f"WHERE id = $2 AND user_id = $3 AND deleted_at IS NULL "
        f"RETURNING {_COLS}",
        file_name, app_id, user_id,
    )
    if not row:
        raise NotFound(f"application id={app_id}")
    return _row_to_out(row)


async def count_created_within(
    conn: asyncpg.Connection, user_id: int, *, days: int
) -> int:
    val = await conn.fetchval(
        "SELECT COUNT(*) FROM applications "
        "WHERE user_id = $1 AND deleted_at IS NULL "
        f"AND created_at >= NOW() - INTERVAL '{int(days)} days'",
        user_id,
    )
    return int(val or 0)


async def increment_followup(
    conn: asyncpg.Connection, app_id: int, user_id: int
) -> ApplicationOut:
    row = await conn.fetchrow(
        f"""
        UPDATE applications
        SET follow_up_count = follow_up_count + 1,
            last_followed_up_at = NOW(),
            last_updated = NOW()
        WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL
        RETURNING {_COLS}
        """,
        app_id, user_id,
    )
    if not row:
        raise NotFound(f"application id={app_id}")
    return _row_to_out(row)
