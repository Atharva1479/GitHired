import asyncpg

from app.exceptions import NotFound
from app.models import (
    ApplicationOut,
    ReferralCreate,
    ReferralOut,
    ReferralUpdate,
)
from app.repositories.applications import _COLS as APP_COLS

_COLS = """
    id, name, company, target_role, role_at_company, linkedin_url,
    mutual_context, connection_sent_date, connection_status,
    referral_msg_sent_date, reply_date, outcome, notes,
    last_updated, created_at
"""

_ALLOWED_REF_UPDATE_COLS = frozenset({
    "name", "company", "target_role", "role_at_company", "linkedin_url",
    "mutual_context", "connection_status", "referral_msg_sent_date",
    "reply_date", "outcome", "notes",
})


def _row_to_out(row: asyncpg.Record) -> ReferralOut:
    return ReferralOut.model_validate(dict(row))


async def list_referrals(
    conn: asyncpg.Connection,
    user_id: int,
    *,
    connection_status: str | None = None,
    limit: int = 200,
) -> list[ReferralOut]:
    clauses = ["user_id = $1", "deleted_at IS NULL"]
    args: list[object] = [user_id]
    if connection_status:
        clauses.append(f"connection_status = ${len(args) + 1}")
        args.append(connection_status)
    args.append(limit)
    sql = (
        f"SELECT {_COLS} FROM referral_contacts "
        f"WHERE {' AND '.join(clauses)} "
        f"ORDER BY last_updated DESC LIMIT ${len(args)}"
    )
    rows = await conn.fetch(sql, *args)
    return [_row_to_out(r) for r in rows]


async def get_referral(
    conn: asyncpg.Connection, ref_id: int, user_id: int
) -> ReferralOut:
    row = await conn.fetchrow(
        f"SELECT {_COLS} FROM referral_contacts "
        "WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL",
        ref_id, user_id,
    )
    if not row:
        raise NotFound(f"referral id={ref_id}")
    return _row_to_out(row)


async def create_referral(
    conn: asyncpg.Connection, user_id: int, data: ReferralCreate
) -> ReferralOut:
    row = await conn.fetchrow(
        f"""
        INSERT INTO referral_contacts (
            user_id, name, company, target_role, role_at_company,
            linkedin_url, mutual_context, connection_sent_date, notes
        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
        RETURNING {_COLS}
        """,
        user_id,
        data.name,
        data.company,
        data.target_role,
        data.role_at_company,
        str(data.linkedin_url) if data.linkedin_url else None,
        data.mutual_context,
        data.connection_sent_date,
        data.notes,
    )
    return _row_to_out(row)


async def update_referral(
    conn: asyncpg.Connection,
    ref_id: int,
    user_id: int,
    patch: ReferralUpdate,
) -> tuple[ReferralOut, ReferralOut]:
    before = await get_referral(conn, ref_id, user_id)

    fields = patch.model_dump(exclude_unset=True)
    if not fields:
        return before, before

    sets: list[str] = []
    args: list[object] = []
    for key, value in fields.items():
        if key not in _ALLOWED_REF_UPDATE_COLS:
            raise ValueError(f"Unexpected column: {key}")
        sets.append(f"{key} = ${len(args) + 1}")
        if key == "linkedin_url" and value is not None:
            value = str(value)
        args.append(value)
    sets.append("last_updated = NOW()")

    args.extend([ref_id, user_id])
    row = await conn.fetchrow(
        f"UPDATE referral_contacts SET {', '.join(sets)} "
        f"WHERE id = ${len(args) - 1} AND user_id = ${len(args)} "
        f"AND deleted_at IS NULL RETURNING {_COLS}",
        *args,
    )
    if not row:
        raise NotFound(f"referral id={ref_id}")
    return before, _row_to_out(row)


async def soft_delete_referral(
    conn: asyncpg.Connection, ref_id: int, user_id: int
) -> None:
    result = await conn.execute(
        "UPDATE referral_contacts SET deleted_at = NOW() "
        "WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL",
        ref_id, user_id,
    )
    if result.endswith(" 0"):
        raise NotFound(f"referral id={ref_id}")


async def _set_status(
    conn: asyncpg.Connection,
    ref_id: int,
    user_id: int,
    new_status: str,
    *,
    set_msg_date: bool = False,
    set_reply_date: bool = False,
) -> ReferralOut:
    extra = ""
    if set_msg_date:
        extra = ", referral_msg_sent_date = CURRENT_DATE"
    elif set_reply_date:
        extra = ", reply_date = CURRENT_DATE"
    row = await conn.fetchrow(
        f"UPDATE referral_contacts "
        f"SET connection_status = $1, last_updated = NOW(){extra} "
        f"WHERE id = $2 AND user_id = $3 AND deleted_at IS NULL "
        f"RETURNING {_COLS}",
        new_status, ref_id, user_id,
    )
    if not row:
        raise NotFound(f"referral id={ref_id}")
    return _row_to_out(row)


async def mark_accepted(conn: asyncpg.Connection, ref_id: int, user_id: int) -> ReferralOut:
    return await _set_status(conn, ref_id, user_id, "Accepted")


async def mark_sent(conn: asyncpg.Connection, ref_id: int, user_id: int) -> ReferralOut:
    return await _set_status(conn, ref_id, user_id, "Msg Sent", set_msg_date=True)


async def mark_replied(conn: asyncpg.Connection, ref_id: int, user_id: int) -> ReferralOut:
    return await _set_status(conn, ref_id, user_id, "Replied", set_reply_date=True)


async def link_application(
    conn: asyncpg.Connection, ref_id: int, app_id: int, user_id: int
) -> None:
    await get_referral(conn, ref_id, user_id)
    # Verify the application belongs to user
    owner = await conn.fetchval(
        "SELECT user_id FROM applications WHERE id = $1 AND deleted_at IS NULL",
        app_id,
    )
    if owner is None or owner != user_id:
        raise NotFound(f"application id={app_id}")
    # Resurrect a previously soft-deleted link if one exists.
    await conn.execute(
        """
        INSERT INTO referral_application_link (referral_id, application_id)
        VALUES ($1, $2)
        ON CONFLICT (referral_id, application_id)
        DO UPDATE SET deleted_at = NULL, linked_at = NOW()
        """,
        ref_id, app_id,
    )


async def unlink_application(
    conn: asyncpg.Connection, ref_id: int, app_id: int, user_id: int
) -> None:
    await get_referral(conn, ref_id, user_id)
    await conn.execute(
        "UPDATE referral_application_link SET deleted_at = NOW() "
        "WHERE referral_id = $1 AND application_id = $2 "
        "AND deleted_at IS NULL",
        ref_id, app_id,
    )


async def list_linked_applications(
    conn: asyncpg.Connection, ref_id: int, user_id: int
) -> list[ApplicationOut]:
    await get_referral(conn, ref_id, user_id)
    rows = await conn.fetch(
        f"""
        SELECT {APP_COLS}
        FROM applications a
        JOIN referral_application_link l ON l.application_id = a.id
        WHERE l.referral_id = $1
          AND a.user_id = $2
          AND a.deleted_at IS NULL
          AND l.deleted_at IS NULL
        ORDER BY a.last_updated DESC
        """,
        ref_id, user_id,
    )
    return [ApplicationOut.model_validate(dict(r)) for r in rows]
