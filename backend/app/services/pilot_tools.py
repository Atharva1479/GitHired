"""Pilot agent tools — read-only Phase 1.

Each tool is an async handler that takes (args: dict, ctx: ToolContext) and
returns a JSON-serialisable dict. Every tool filters by ctx.user_id at the
SQL layer — the model can never read another user's rows.

Tool definitions (the JSON schemas the model sees) live alongside the
handlers in TOOLS so adding a new tool is one entry in one file.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import secrets
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

import asyncpg
import structlog
from pydantic import ValidationError

from app.models import (
    ApplicationCreate,
    ApplicationUpdate,
    ReferralCreate,
    ReferralUpdate,
    StudySectionCreate,
    StudySubsectionCreate,
    StudyTopicCreate,
)
from app.repositories import applications as apps_repo
from app.repositories import drafts as drafts_repo
from app.repositories import referrals as refs_repo
from app.repositories import study as study_repo
from app.repositories.events import emit
from app.services import gamify
from app.services import study_ai
from app.services.gemini_service import (
    build_followup_email_prompt,
    build_referral_ask_prompt,
    build_referral_followup_prompt,
    generate_or_fallback,
)

log = structlog.get_logger("pilot.tools")

# Voice STT + silence detection + a follow-up Gemini round-trip eats
# real wall-clock time before the user's "yes" actually reaches the
# agent. 60s was leaving most flows expired. 5 minutes is generous
# without inviting replay weirdness — the token is still single-use,
# user-bound, and args-bound.
CONFIRM_TTL_SECONDS = 300

# ---------------------------------------------------------------------------
# Tool execution context
# ---------------------------------------------------------------------------


@dataclass
class ToolContext:
    user_id: int
    conn: asyncpg.Connection


Handler = Callable[[dict[str, Any], ToolContext], Awaitable[dict[str, Any]]]


Preview = Callable[[dict[str, Any], "ToolContext"], Awaitable[str]]
ConfirmsDecider = Callable[[dict[str, Any]], bool]


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Handler
    side_effects: bool = False
    confirms: bool | ConfirmsDecider = False
    preview: Preview | None = None


# ---------------------------------------------------------------------------
# Read handlers
# ---------------------------------------------------------------------------


async def _get_profile(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    row = await ctx.conn.fetchrow(
        "SELECT id, email, display_name, timezone, created_at "
        "FROM users WHERE id = $1 AND deleted_at IS NULL",
        ctx.user_id,
    )
    if not row:
        return {"error": "profile_not_found"}
    return {
        "id": row["id"],
        "email": row["email"],
        "display_name": row["display_name"],
        "first_name": (row["display_name"] or "").split(" ")[0] or "there",
        "timezone": row["timezone"],
        "member_since": row["created_at"].date().isoformat(),
    }


_PERIOD_INTERVAL = {
    "today": "1 day",
    "week": "7 days",
    "month": "30 days",
    "all": None,
}


async def _get_stats(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    period = (args.get("period") or "week").lower()
    if period not in _PERIOD_INTERVAL:
        return {"error": f"period must be one of: {list(_PERIOD_INTERVAL)}"}
    interval = _PERIOD_INTERVAL[period]
    where_window = (
        ""
        if interval is None
        else f"AND created_at >= NOW() - INTERVAL '{interval}'"
    )
    app_row = await ctx.conn.fetchrow(
        f"""
        SELECT
          COUNT(*) AS total,
          COUNT(*) FILTER (WHERE status = 'Applied') AS applied,
          COUNT(*) FILTER (WHERE status = 'Screening') AS screening,
          COUNT(*) FILTER (WHERE status = 'Interview') AS interview,
          COUNT(*) FILTER (WHERE status = 'Offer') AS offers,
          COUNT(*) FILTER (WHERE status = 'Rejected') AS rejected,
          COUNT(*) FILTER (WHERE status = 'Ghosted') AS ghosted
        FROM applications
        WHERE user_id = $1 AND deleted_at IS NULL {where_window}
        """,
        ctx.user_id,
    )
    ref_row = await ctx.conn.fetchrow(
        f"""
        SELECT
          COUNT(*) AS total,
          COUNT(*) FILTER (WHERE connection_status = 'Referred') AS referred
        FROM referral_contacts
        WHERE user_id = $1 AND deleted_at IS NULL {where_window}
        """,
        ctx.user_id,
    )
    a_total = int(app_row["total"]) if app_row else 0
    a_closed = int((app_row["rejected"] or 0) + (app_row["ghosted"] or 0) + (app_row["offers"] or 0)) if app_row else 0
    a_responded = a_closed - int(app_row["ghosted"] or 0) if app_row else 0
    return {
        "period": period,
        "applications": {
            "total": a_total,
            "applied": int(app_row["applied"]) if app_row else 0,
            "screening": int(app_row["screening"]) if app_row else 0,
            "interview": int(app_row["interview"]) if app_row else 0,
            "offers": int(app_row["offers"]) if app_row else 0,
            "rejected": int(app_row["rejected"]) if app_row else 0,
            "ghosted": int(app_row["ghosted"]) if app_row else 0,
            "response_rate_pct": (
                round((a_responded / a_closed) * 100) if a_closed else None
            ),
        },
        "referrals": {
            "total": int(ref_row["total"]) if ref_row else 0,
            "successful_referrals": int(ref_row["referred"]) if ref_row else 0,
        },
    }


async def _get_xp_state(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    state = await gamify.get_state(ctx.conn, ctx.user_id)
    return {
        "level": state.level,
        "xp": state.xp,
        "xp_into_level": state.xp_into_level,
        "xp_for_level": state.xp_for_level,
        "streak_days": state.streak,
        "longest_streak_days": state.longest_streak,
        "freezes_banked": state.freezes,
        "daily_quests": [
            {
                "title": q["title"],
                "progress": q["progress"],
                "target": q["target"],
                "completed": q["completed"],
                "reward_xp": q["reward_xp"],
            }
            for q in state.daily_quests
        ],
        "weekly_quests": [
            {
                "title": q["title"],
                "progress": q["progress"],
                "target": q["target"],
                "completed": q["completed"],
                "reward_xp": q["reward_xp"],
            }
            for q in state.weekly_quests
        ],
    }


_APP_LIST_COLS = (
    "id, company, role, status, source, applied_date, last_updated, "
    "contact_name, fit_score"
)


def _serialise_app(row: asyncpg.Record) -> dict[str, Any]:
    return {
        "id": row["id"],
        "company": row["company"],
        "role": row["role"],
        "status": row["status"],
        "source": row["source"],
        "applied_date": row["applied_date"].isoformat(),
        "last_updated": row["last_updated"].isoformat(),
        "contact_name": row["contact_name"],
        "fit_score": row["fit_score"],
    }


async def _list_applications(
    args: dict[str, Any], ctx: ToolContext
) -> dict[str, Any]:
    company = args.get("company")
    status_ = args.get("status")
    source = args.get("source")
    limit = max(1, min(int(args.get("limit") or 20), 100))

    clauses = ["user_id = $1", "deleted_at IS NULL"]
    vals: list[Any] = [ctx.user_id]
    if company:
        clauses.append(f"company ILIKE ${len(vals) + 1}")
        vals.append(f"%{company}%")
    if status_:
        clauses.append(f"status = ${len(vals) + 1}")
        vals.append(status_)
    if source:
        clauses.append(f"source = ${len(vals) + 1}")
        vals.append(source)
    vals.append(limit)

    rows = await ctx.conn.fetch(
        f"SELECT {_APP_LIST_COLS} FROM applications "
        f"WHERE {' AND '.join(clauses)} "
        f"ORDER BY last_updated DESC LIMIT ${len(vals)}",
        *vals,
    )
    return {
        "count": len(rows),
        "applications": [_serialise_app(r) for r in rows],
    }


async def _get_application(
    args: dict[str, Any], ctx: ToolContext
) -> dict[str, Any]:
    app_id = args.get("id")
    company = args.get("company")
    role = args.get("role")

    if app_id is not None:
        row = await ctx.conn.fetchrow(
            f"SELECT {_APP_LIST_COLS}, jd_url, jd_text, notes, salary_discussed, "
            f"follow_up_count, last_followed_up_at, created_at "
            f"FROM applications WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL",
            int(app_id), ctx.user_id,
        )
        if not row:
            return {"error": "not_found", "id": int(app_id)}
        return {"application": _full_app(row)}

    if not company:
        return {"error": "must provide id or company"}

    clauses = ["user_id = $1", "deleted_at IS NULL", "company ILIKE $2"]
    vals: list[Any] = [ctx.user_id, f"%{company}%"]
    if role:
        clauses.append(f"role ILIKE ${len(vals) + 1}")
        vals.append(f"%{role}%")

    rows = await ctx.conn.fetch(
        f"SELECT {_APP_LIST_COLS}, jd_url, jd_text, notes, salary_discussed, "
        f"follow_up_count, last_followed_up_at, created_at "
        f"FROM applications WHERE {' AND '.join(clauses)} "
        f"ORDER BY last_updated DESC LIMIT 5",
        *vals,
    )
    if not rows:
        return {"error": "not_found", "company": company, "role": role}
    if len(rows) > 1:
        return {
            "ambiguous": True,
            "candidates": [_serialise_app(r) for r in rows],
            "hint": "Ask the user which one — never guess.",
        }
    return {"application": _full_app(rows[0])}


def _full_app(row: asyncpg.Record) -> dict[str, Any]:
    base = _serialise_app(row)
    base.update(
        {
            "jd_url": row["jd_url"],
            "jd_text": row["jd_text"],
            "notes": row["notes"],
            "salary_discussed": row["salary_discussed"],
            "follow_up_count": row["follow_up_count"],
            "last_followed_up_at": (
                row["last_followed_up_at"].isoformat()
                if row["last_followed_up_at"]
                else None
            ),
            "created_at": row["created_at"].isoformat(),
        }
    )
    return base


_REF_LIST_COLS = (
    "id, name, company, target_role, role_at_company, connection_status, "
    "connection_sent_date, referral_msg_sent_date, reply_date, outcome, "
    "last_updated"
)


def _serialise_ref(row: asyncpg.Record) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "company": row["company"],
        "target_role": row["target_role"],
        "role_at_company": row["role_at_company"],
        "connection_status": row["connection_status"],
        "connection_sent_date": row["connection_sent_date"].isoformat(),
        "referral_msg_sent_date": (
            row["referral_msg_sent_date"].isoformat()
            if row["referral_msg_sent_date"]
            else None
        ),
        "reply_date": (
            row["reply_date"].isoformat() if row["reply_date"] else None
        ),
        "outcome": row["outcome"],
        "last_updated": row["last_updated"].isoformat(),
    }


async def _list_referrals(
    args: dict[str, Any], ctx: ToolContext
) -> dict[str, Any]:
    company = args.get("company")
    status_ = args.get("connection_status")
    limit = max(1, min(int(args.get("limit") or 20), 100))

    clauses = ["user_id = $1", "deleted_at IS NULL"]
    vals: list[Any] = [ctx.user_id]
    if company:
        clauses.append(f"company ILIKE ${len(vals) + 1}")
        vals.append(f"%{company}%")
    if status_:
        clauses.append(f"connection_status = ${len(vals) + 1}")
        vals.append(status_)
    vals.append(limit)

    rows = await ctx.conn.fetch(
        f"SELECT {_REF_LIST_COLS} FROM referral_contacts "
        f"WHERE {' AND '.join(clauses)} "
        f"ORDER BY last_updated DESC LIMIT ${len(vals)}",
        *vals,
    )
    return {
        "count": len(rows),
        "referrals": [_serialise_ref(r) for r in rows],
    }


async def _get_referral(
    args: dict[str, Any], ctx: ToolContext
) -> dict[str, Any]:
    ref_id = args.get("id")
    name = args.get("name")

    if ref_id is not None:
        row = await ctx.conn.fetchrow(
            f"SELECT {_REF_LIST_COLS}, mutual_context, linkedin_url, notes, "
            f"created_at "
            f"FROM referral_contacts WHERE id = $1 AND user_id = $2 "
            f"AND deleted_at IS NULL",
            int(ref_id), ctx.user_id,
        )
        if not row:
            return {"error": "not_found", "id": int(ref_id)}
        return {"referral": _full_ref(row)}

    if not name:
        return {"error": "must provide id or name"}

    rows = await ctx.conn.fetch(
        f"SELECT {_REF_LIST_COLS}, mutual_context, linkedin_url, notes, "
        f"created_at FROM referral_contacts "
        f"WHERE user_id = $1 AND deleted_at IS NULL AND name ILIKE $2 "
        f"ORDER BY last_updated DESC LIMIT 5",
        ctx.user_id, f"%{name}%",
    )
    if not rows:
        return {"error": "not_found", "name": name}
    if len(rows) > 1:
        return {
            "ambiguous": True,
            "candidates": [_serialise_ref(r) for r in rows],
            "hint": "Ask the user which one — never guess.",
        }
    return {"referral": _full_ref(rows[0])}


def _full_ref(row: asyncpg.Record) -> dict[str, Any]:
    base = _serialise_ref(row)
    base.update(
        {
            "mutual_context": row["mutual_context"],
            "linkedin_url": row["linkedin_url"],
            "notes": row["notes"],
            "created_at": row["created_at"].isoformat(),
        }
    )
    return base


async def _list_recent_activity(
    args: dict[str, Any], ctx: ToolContext
) -> dict[str, Any]:
    days = max(1, min(int(args.get("days") or 7), 30))
    limit = max(1, min(int(args.get("limit") or 20), 50))
    rows = await ctx.conn.fetch(
        """
        SELECT id, event_type, payload, occurred_at FROM events
        WHERE user_id = $1 AND deleted_at IS NULL
          AND occurred_at >= NOW() - ($2::int * INTERVAL '1 day')
        ORDER BY occurred_at DESC LIMIT $3
        """,
        ctx.user_id, days, limit,
    )
    out: list[dict[str, Any]] = []
    for r in rows:
        payload = r["payload"]
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                payload = {}
        out.append(
            {
                "event_type": r["event_type"],
                "payload": payload or {},
                "occurred_at": r["occurred_at"].isoformat(),
            }
        )
    return {"days": days, "count": len(out), "events": out}


async def _list_pending_nudges(
    args: dict[str, Any], ctx: ToolContext
) -> dict[str, Any]:
    today = dt.date.today()
    rows = await ctx.conn.fetch(
        """
        SELECT id, type, reference_type, reference_id, severity, message,
               fired_on_date
        FROM nudges
        WHERE user_id = $1
          AND deleted_at IS NULL
          AND read_at IS NULL AND acted_at IS NULL
          AND (snoozed_until IS NULL OR snoozed_until < $2)
          AND fired_on_date <= $2
        ORDER BY CASE severity
                   WHEN 'overdue' THEN 0
                   WHEN 'due'     THEN 1
                   ELSE 2
                 END,
                 fired_on_date ASC LIMIT 30
        """,
        ctx.user_id, today,
    )
    return {
        "count": len(rows),
        "nudges": [
            {
                "id": r["id"],
                "type": r["type"],
                "reference_type": r["reference_type"],
                "reference_id": r["reference_id"],
                "severity": r["severity"],
                "message": r["message"],
                "fired_on_date": r["fired_on_date"].isoformat(),
            }
            for r in rows
        ],
    }


async def _list_drafts(
    args: dict[str, Any], ctx: ToolContext
) -> dict[str, Any]:
    entity_type = args.get("entity_type")
    entity_id = args.get("entity_id")
    limit = max(1, min(int(args.get("limit") or 10), 25))

    if entity_type and entity_id:
        rows = await ctx.conn.fetch(
            """
            SELECT id, entity_type, entity_id, draft_type, content, model,
                   fallback, created_at
            FROM drafts
            WHERE user_id = $1 AND deleted_at IS NULL
              AND entity_type = $2 AND entity_id = $3
            ORDER BY created_at DESC LIMIT $4
            """,
            ctx.user_id, entity_type, int(entity_id), limit,
        )
    else:
        rows = await ctx.conn.fetch(
            """
            SELECT id, entity_type, entity_id, draft_type, content, model,
                   fallback, created_at
            FROM drafts WHERE user_id = $1 AND deleted_at IS NULL
            ORDER BY created_at DESC LIMIT $2
            """,
            ctx.user_id, limit,
        )
    return {
        "count": len(rows),
        "drafts": [
            {
                "id": r["id"],
                "entity_type": r["entity_type"],
                "entity_id": r["entity_id"],
                "draft_type": r["draft_type"],
                "content": r["content"],
                "model": r["model"],
                "fallback_used": r["fallback"],
                "created_at": r["created_at"].isoformat(),
            }
            for r in rows
        ],
    }


async def _list_achievements(
    args: dict[str, Any], ctx: ToolContext
) -> dict[str, Any]:
    only = args.get("unlocked")  # None | True | False
    items = await gamify.list_achievements(ctx.conn, ctx.user_id)
    if only is True:
        items = [x for x in items if x["unlocked_at"]]
    elif only is False:
        items = [x for x in items if not x["unlocked_at"]]
    return {"count": len(items), "achievements": items}


# ---------------------------------------------------------------------------
# Confirmation rail
# ---------------------------------------------------------------------------


def _hash_args(user_id: int, tool_name: str, args: dict[str, Any]) -> str:
    clean = {k: v for k, v in args.items() if k != "confirm_token"}
    canon = json.dumps(clean, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(
        f"{user_id}:{tool_name}:{canon}".encode()
    ).hexdigest()[:32]


async def _issue_confirmation(
    name: str, args: dict[str, Any], ctx: ToolContext, summary: str
) -> dict[str, Any]:
    token = secrets.token_urlsafe(16)
    h = _hash_args(ctx.user_id, name, args)
    # Persist the original args (sans confirm_token) so the agent's brief
    # context on the next turn can show the model exactly what action to
    # re-call and which token to attach. Otherwise the model has no way
    # to recover the token from the prior turn's tool result.
    clean_args = {k: v for k, v in args.items() if k != "confirm_token"}
    expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(
        seconds=CONFIRM_TTL_SECONDS
    )
    await ctx.conn.execute(
        """
        INSERT INTO pilot_confirmations
            (token, user_id, tool_name, args_hash, expires_at, args)
        VALUES ($1, $2, $3, $4, $5, $6::jsonb)
        """,
        token, ctx.user_id, name, h, expires_at,
        json.dumps(clean_args, default=str),
    )
    return {
        "needs_confirmation": True,
        "summary": summary,
        "confirm_token": token,
        "expires_in_seconds": CONFIRM_TTL_SECONDS,
        "hint": (
            "Paste 'summary' to the user and ask for yes/no. If they "
            "agree, call this tool again with the same args plus this "
            "confirm_token. If they decline, do not call again."
        ),
    }


async def _consume_confirmation(
    token: str, name: str, args: dict[str, Any], ctx: ToolContext
) -> bool:
    # Soft-delete the token: atomic UPDATE … RETURNING gives one-shot
    # consumption (a second attempt finds deleted_at IS NOT NULL and
    # returns no row). We keep the row so audits can trace which token
    # authorised which destructive action.
    h = _hash_args(ctx.user_id, name, args)
    row = await ctx.conn.fetchrow(
        """
        UPDATE pilot_confirmations
        SET deleted_at = NOW()
        WHERE token = $1 AND user_id = $2 AND tool_name = $3
          AND args_hash = $4 AND expires_at > NOW()
          AND deleted_at IS NULL
        RETURNING token
        """,
        token, ctx.user_id, name, h,
    )
    return row is not None


# ---------------------------------------------------------------------------
# Write handlers
# ---------------------------------------------------------------------------


_VALID_SOURCES = {"LinkedIn", "Naukri", "Referral", "CompanySite", "Other"}
_VALID_STATUSES = {"Applied", "Screening", "Interview", "Offer", "Rejected", "Ghosted"}
_FINAL_APP_STATUSES = {"Rejected", "Ghosted", "Offer"}
_VALID_CONN_STATUSES = {
    "Request Sent", "Accepted", "Msg Sent", "Replied", "Referred", "Dropped",
}


def _parse_date(value: Any) -> dt.date | None:
    if value is None or value == "":
        return None
    if isinstance(value, dt.date):
        return value
    try:
        return dt.date.fromisoformat(str(value))
    except ValueError:
        return None


async def _add_application(
    args: dict[str, Any], ctx: ToolContext
) -> dict[str, Any]:
    company = (args.get("company") or "").strip()
    role = (args.get("role") or "").strip()
    if not company or not role:
        return {"error": "missing required fields: company and role"}
    source = (args.get("source") or "Other").strip()
    if source not in _VALID_SOURCES:
        return {"error": f"source must be one of: {sorted(_VALID_SOURCES)}"}
    applied_date = _parse_date(args.get("applied_date")) or dt.date.today()

    try:
        payload = ApplicationCreate(
            company=company,
            role=role,
            source=source,  # type: ignore[arg-type]
            applied_date=applied_date,
            jd_url=args.get("jd_url") or None,
            jd_text=args.get("jd_text") or None,
            contact_name=args.get("contact_name") or None,
            notes=args.get("notes") or None,
        )
    except ValidationError as e:
        return {"error": f"validation: {e.errors()[0].get('msg', 'invalid input')}"}

    async with ctx.conn.transaction():
        app = await apps_repo.create_application(ctx.conn, ctx.user_id, payload)
        await emit(ctx.conn, ctx.user_id, "application.created", {
            "application_id": app.id, "company": app.company, "role": app.role,
            "source": "pilot",
        })
        await gamify.record_event(
            ctx.conn, ctx.user_id, "app.added",
            ref_type="application", ref_id=app.id,
        )
    return {
        "ok": True,
        "application": {
            "id": app.id,
            "company": app.company,
            "role": app.role,
            "status": app.status,
            "source": app.source,
            "applied_date": app.applied_date.isoformat(),
        },
    }


def _build_app_patch(args: dict[str, Any]) -> ApplicationUpdate | dict[str, Any]:
    fields: dict[str, Any] = {}
    for key in (
        "company", "role", "source", "applied_date", "status", "notes",
        "fit_score", "salary_discussed", "contact_name", "contact_linkedin",
        "jd_url", "jd_text",
    ):
        if key in args and args[key] is not None:
            fields[key] = args[key]
    if "applied_date" in fields:
        d = _parse_date(fields["applied_date"])
        if d is None:
            return {"error": "applied_date must be ISO-8601 (YYYY-MM-DD)"}
        fields["applied_date"] = d
    if "status" in fields and fields["status"] not in _VALID_STATUSES:
        return {"error": f"status must be one of: {sorted(_VALID_STATUSES)}"}
    if "source" in fields and fields["source"] not in _VALID_SOURCES:
        return {"error": f"source must be one of: {sorted(_VALID_SOURCES)}"}
    try:
        return ApplicationUpdate(**fields)
    except ValidationError as e:
        return {"error": f"validation: {e.errors()[0].get('msg', 'invalid input')}"}


async def _update_application(
    args: dict[str, Any], ctx: ToolContext
) -> dict[str, Any]:
    app_id = args.get("id")
    if not app_id:
        return {"error": "missing id"}
    patch = _build_app_patch({k: v for k, v in args.items() if k != "id"})
    if isinstance(patch, dict):
        return patch  # error envelope

    try:
        async with ctx.conn.transaction():
            before, after = await apps_repo.update_application(
                ctx.conn, int(app_id), ctx.user_id, patch,
            )
            if before.status != after.status:
                await emit(ctx.conn, ctx.user_id, "application.status_changed", {
                    "application_id": int(app_id),
                    "from": before.status, "to": after.status,
                    "source": "pilot",
                })
                event_key = gamify.STATUS_EVENT_KEY.get(after.status)
                if event_key:
                    await gamify.record_event(
                        ctx.conn, ctx.user_id, event_key,
                        ref_type=f"status:{after.status}", ref_id=int(app_id),
                    )
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)[:160]}

    return {
        "ok": True,
        "application": {
            "id": after.id,
            "company": after.company,
            "role": after.role,
            "status": after.status,
            "source": after.source,
        },
    }


async def _move_application_status(
    args: dict[str, Any], ctx: ToolContext
) -> dict[str, Any]:
    app_id = args.get("id")
    new_status = args.get("new_status") or args.get("status")
    if not app_id or not new_status:
        return {"error": "missing id or new_status"}
    return await _update_application(
        {"id": app_id, "status": new_status}, ctx,
    )


async def _delete_application(
    args: dict[str, Any], ctx: ToolContext
) -> dict[str, Any]:
    app_id = args.get("id")
    if not app_id:
        return {"error": "missing id"}
    try:
        async with ctx.conn.transaction():
            await apps_repo.soft_delete_application(ctx.conn, int(app_id), ctx.user_id)
            await emit(ctx.conn, ctx.user_id, "application.deleted", {
                "application_id": int(app_id), "source": "pilot",
            })
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)[:160]}
    return {"ok": True, "id": int(app_id)}


async def _add_note_to_application(
    args: dict[str, Any], ctx: ToolContext
) -> dict[str, Any]:
    app_id = args.get("id")
    text = (args.get("text") or "").strip()
    if not app_id or not text:
        return {"error": "missing id or text"}
    try:
        existing = await apps_repo.get_application(ctx.conn, int(app_id), ctx.user_id)
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)[:160]}
    today = dt.date.today().isoformat()
    combined = (
        f"{existing.notes.rstrip()}\n\n[{today}] {text}"
        if existing.notes else f"[{today}] {text}"
    )
    return await _update_application({"id": app_id, "notes": combined}, ctx)


async def _add_referral(
    args: dict[str, Any], ctx: ToolContext
) -> dict[str, Any]:
    name = (args.get("name") or "").strip()
    company = (args.get("company") or "").strip()
    target_role = (args.get("target_role") or "").strip()
    if not name or not company or not target_role:
        return {"error": "missing required: name, company, target_role"}
    connection_sent_date = (
        _parse_date(args.get("connection_sent_date")) or dt.date.today()
    )
    try:
        payload = ReferralCreate(
            name=name,
            company=company,
            target_role=target_role,
            connection_sent_date=connection_sent_date,
            role_at_company=args.get("role_at_company") or None,
            linkedin_url=args.get("linkedin_url") or None,
            mutual_context=args.get("mutual_context") or None,
            notes=args.get("notes") or None,
        )
    except ValidationError as e:
        return {"error": f"validation: {e.errors()[0].get('msg', 'invalid input')}"}

    async with ctx.conn.transaction():
        ref = await refs_repo.create_referral(ctx.conn, ctx.user_id, payload)
        await emit(ctx.conn, ctx.user_id, "referral.created", {
            "referral_id": ref.id, "name": ref.name, "company": ref.company,
            "source": "pilot",
        })
        await gamify.record_event(
            ctx.conn, ctx.user_id, "referral.added",
            ref_type="referral", ref_id=ref.id,
        )
    return {
        "ok": True,
        "referral": {
            "id": ref.id,
            "name": ref.name,
            "company": ref.company,
            "target_role": ref.target_role,
            "connection_status": ref.connection_status,
        },
    }


async def _update_referral(
    args: dict[str, Any], ctx: ToolContext
) -> dict[str, Any]:
    ref_id = args.get("id")
    if not ref_id:
        return {"error": "missing id"}
    fields: dict[str, Any] = {}
    for key in (
        "name", "company", "target_role", "role_at_company",
        "linkedin_url", "mutual_context", "connection_status",
        "referral_msg_sent_date", "reply_date", "outcome", "notes",
    ):
        if key in args and args[key] is not None:
            fields[key] = args[key]
    if "connection_status" in fields and fields["connection_status"] not in _VALID_CONN_STATUSES:
        return {"error": f"connection_status must be one of: {sorted(_VALID_CONN_STATUSES)}"}
    for date_key in ("referral_msg_sent_date", "reply_date"):
        if date_key in fields:
            d = _parse_date(fields[date_key])
            if d is None:
                return {"error": f"{date_key} must be ISO-8601 (YYYY-MM-DD)"}
            fields[date_key] = d
    try:
        patch = ReferralUpdate(**fields)
    except ValidationError as e:
        return {"error": f"validation: {e.errors()[0].get('msg', 'invalid input')}"}
    try:
        async with ctx.conn.transaction():
            before, after = await refs_repo.update_referral(
                ctx.conn, int(ref_id), ctx.user_id, patch,
            )
            if before.connection_status != after.connection_status:
                await emit(ctx.conn, ctx.user_id, "referral.status_changed", {
                    "referral_id": int(ref_id),
                    "from": before.connection_status,
                    "to": after.connection_status,
                    "source": "pilot",
                })
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)[:160]}
    return {
        "ok": True,
        "referral": {
            "id": after.id,
            "name": after.name,
            "company": after.company,
            "connection_status": after.connection_status,
        },
    }


async def _delete_referral(
    args: dict[str, Any], ctx: ToolContext
) -> dict[str, Any]:
    ref_id = args.get("id")
    if not ref_id:
        return {"error": "missing id"}
    try:
        async with ctx.conn.transaction():
            await refs_repo.soft_delete_referral(ctx.conn, int(ref_id), ctx.user_id)
            await emit(ctx.conn, ctx.user_id, "referral.deleted", {
                "referral_id": int(ref_id), "source": "pilot",
            })
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)[:160]}
    return {"ok": True, "id": int(ref_id)}


async def _mark_referral(
    args: dict[str, Any], ctx: ToolContext, action: str,
) -> dict[str, Any]:
    ref_id = args.get("id")
    if not ref_id:
        return {"error": "missing id"}
    fn_map = {
        "accepted": refs_repo.mark_accepted,
        "sent": refs_repo.mark_sent,
        "replied": refs_repo.mark_replied,
    }
    event_map = {
        "accepted": "referral.accepted",
        "sent": "referral.message_sent",
        "replied": "referral.replied",
    }
    try:
        async with ctx.conn.transaction():
            ref = await fn_map[action](ctx.conn, int(ref_id), ctx.user_id)
            await emit(ctx.conn, ctx.user_id, event_map[action], {
                "referral_id": int(ref_id), "source": "pilot",
            })
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)[:160]}
    return {
        "ok": True,
        "referral": {
            "id": ref.id,
            "name": ref.name,
            "connection_status": ref.connection_status,
        },
    }


async def _link_referral_to_application(
    args: dict[str, Any], ctx: ToolContext
) -> dict[str, Any]:
    ref_id = args.get("referral_id")
    app_id = args.get("application_id")
    if not ref_id or not app_id:
        return {"error": "missing referral_id or application_id"}
    try:
        async with ctx.conn.transaction():
            await refs_repo.link_application(
                ctx.conn, int(ref_id), int(app_id), ctx.user_id,
            )
            await emit(ctx.conn, ctx.user_id, "referral.linked", {
                "referral_id": int(ref_id),
                "application_id": int(app_id),
                "source": "pilot",
            })
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)[:160]}
    return {"ok": True, "referral_id": int(ref_id), "application_id": int(app_id)}


async def _unlink_referral_from_application(
    args: dict[str, Any], ctx: ToolContext
) -> dict[str, Any]:
    ref_id = args.get("referral_id")
    app_id = args.get("application_id")
    if not ref_id or not app_id:
        return {"error": "missing referral_id or application_id"}
    try:
        await refs_repo.unlink_application(
            ctx.conn, int(ref_id), int(app_id), ctx.user_id,
        )
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)[:160]}
    return {"ok": True}


async def _generate_followup_draft(
    args: dict[str, Any], ctx: ToolContext
) -> dict[str, Any]:
    app_id = args.get("application_id")
    if not app_id:
        return {"error": "missing application_id"}
    try:
        app = await apps_repo.get_application(ctx.conn, int(app_id), ctx.user_id)
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)[:160]}
    days_elapsed = (dt.date.today() - app.applied_date).days
    prompt = build_followup_email_prompt(
        company=app.company, role=app.role,
        days_elapsed=days_elapsed,
        contact_name=app.contact_name,
    )
    text, model, pt, ot, fb = await generate_or_fallback(
        draft_type="followup_email",
        prompt=prompt,
        company=app.company, role=app.role,
        days_elapsed=days_elapsed, contact_name=app.contact_name,
    )
    async with ctx.conn.transaction():
        draft = await drafts_repo.insert(
            ctx.conn, ctx.user_id,
            entity_type="application", entity_id=int(app_id),
            draft_type="followup_email",
            content=text, model=model,
            prompt_tokens=pt, output_tokens=ot, fallback=fb,
        )
        await gamify.record_event(
            ctx.conn, ctx.user_id, "draft.sent",
            ref_type="draft", ref_id=draft.id,
        )
    return {
        "ok": True,
        "draft": {
            "id": draft.id,
            "content": draft.content,
            "fallback_used": draft.fallback,
        },
    }


async def _generate_referral_ask(
    args: dict[str, Any], ctx: ToolContext
) -> dict[str, Any]:
    ref_id = args.get("referral_id")
    if not ref_id:
        return {"error": "missing referral_id"}
    try:
        ref = await refs_repo.get_referral(ctx.conn, int(ref_id), ctx.user_id)
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)[:160]}
    prompt = build_referral_ask_prompt(
        name=ref.name, company=ref.company,
        target_role=ref.target_role,
        mutual_context=ref.mutual_context,
    )
    text, model, pt, ot, fb = await generate_or_fallback(
        draft_type="referral_ask",
        prompt=prompt,
        name=ref.name, company=ref.company, target_role=ref.target_role,
    )
    async with ctx.conn.transaction():
        draft = await drafts_repo.insert(
            ctx.conn, ctx.user_id,
            entity_type="referral", entity_id=int(ref_id),
            draft_type="referral_ask",
            content=text, model=model,
            prompt_tokens=pt, output_tokens=ot, fallback=fb,
        )
        await gamify.record_event(
            ctx.conn, ctx.user_id, "draft.sent",
            ref_type="draft", ref_id=draft.id,
        )
    return {
        "ok": True,
        "draft": {"id": draft.id, "content": draft.content, "fallback_used": draft.fallback},
    }


# ---------------------------------------------------------------------------
# Previews — used to summarise destructive actions before confirmation
# ---------------------------------------------------------------------------


async def _preview_delete_application(
    args: dict[str, Any], ctx: ToolContext
) -> str:
    app_id = args.get("id")
    try:
        app = await apps_repo.get_application(ctx.conn, int(app_id), ctx.user_id)
    except Exception:
        return f"Delete application id={app_id} (lookup failed)"
    return (
        f"Delete the {app.company} {app.role} application "
        f"(currently {app.status}, applied {app.applied_date.isoformat()})?"
    )


async def _preview_delete_referral(
    args: dict[str, Any], ctx: ToolContext
) -> str:
    ref_id = args.get("id")
    try:
        ref = await refs_repo.get_referral(ctx.conn, int(ref_id), ctx.user_id)
    except Exception:
        return f"Delete referral id={ref_id} (lookup failed)"
    return f"Delete referral contact {ref.name} ({ref.company})?"


async def _preview_finalize_application(
    args: dict[str, Any], ctx: ToolContext
) -> str:
    app_id = args.get("id")
    new_status = args.get("status") or args.get("new_status") or "?"
    try:
        app = await apps_repo.get_application(ctx.conn, int(app_id), ctx.user_id)
    except Exception:
        return f"Mark application id={app_id} as {new_status}?"
    return (
        f"Move {app.company} {app.role} from {app.status} to {new_status}?"
    )


def _confirm_status_is_final(args: dict[str, Any]) -> bool:
    status = args.get("status") or args.get("new_status")
    return status in _FINAL_APP_STATUSES


# ---------------------------------------------------------------------------
# Study tracker helpers — by-name lookups + gamify merge
# ---------------------------------------------------------------------------


def _study_merge(base: gamify.XpResult, extra: gamify.XpResult) -> None:
    """Accumulate extra into base in-place (same as router._merge)."""
    if extra.duplicate:
        return
    base.xp_gained += extra.xp_gained
    base.unlocked.extend(extra.unlocked)
    base.quest_completed.extend(extra.quest_completed)
    base.quests_progressed.extend(extra.quests_progressed)
    if extra.new_level is not None:
        base.new_level = extra.new_level


async def _resolve_section(
    conn: asyncpg.Connection,
    user_id: int,
    section_id: Any,
    section_name: Any,
) -> tuple[int | None, dict | None]:
    """Resolve section_id or section_name → (id, None) or (None, error_dict)."""
    if section_id is not None:
        return int(section_id), None
    if not section_name:
        return None, {"error": "must provide section_id or section_name"}
    rows = await conn.fetch(
        "SELECT id, name FROM study_sections "
        "WHERE user_id=$1 AND deleted_at IS NULL AND name ILIKE $2 "
        "ORDER BY position ASC, id ASC LIMIT 5",
        user_id, f"%{section_name}%",
    )
    if not rows:
        return None, {"error": "not_found", "section_name": section_name}
    if len(rows) > 1:
        return None, {
            "ambiguous": True,
            "candidates": [{"id": r["id"], "name": r["name"]} for r in rows],
            "hint": "Ask the user which section — never guess.",
        }
    return int(rows[0]["id"]), None


async def _resolve_subsection(
    conn: asyncpg.Connection,
    user_id: int,
    subsection_id: Any,
    section_id: int | None,
    subsection_name: Any,
) -> tuple[int | None, dict | None]:
    """Resolve subsection_id or (section_id + name) → (id, None) or (None, error)."""
    if subsection_id is not None:
        return int(subsection_id), None
    if not subsection_name:
        return None, {"error": "must provide subsection_id or subsection_name"}
    clauses = ["user_id=$1", "deleted_at IS NULL", "name ILIKE $2"]
    vals: list[Any] = [user_id, f"%{subsection_name}%"]
    if section_id is not None:
        clauses.append(f"section_id=${len(vals) + 1}")
        vals.append(section_id)
    rows = await conn.fetch(
        f"SELECT id, name FROM study_subsections WHERE {' AND '.join(clauses)} "
        "ORDER BY position ASC, id ASC LIMIT 5",
        *vals,
    )
    if not rows:
        return None, {"error": "not_found", "subsection_name": subsection_name}
    if len(rows) > 1:
        return None, {
            "ambiguous": True,
            "candidates": [{"id": r["id"], "name": r["name"]} for r in rows],
            "hint": "Ask the user which subsection — never guess.",
        }
    return int(rows[0]["id"]), None


async def _resolve_topic(
    conn: asyncpg.Connection,
    user_id: int,
    topic_id: Any,
    title: Any,
    subsection_id: int | None = None,
    section_id: int | None = None,
) -> tuple[int | None, dict | None]:
    """Resolve topic_id or title → (id, None) or (None, error)."""
    if topic_id is not None:
        return int(topic_id), None
    if not title:
        return None, {"error": "must provide topic_id or title"}
    clauses = ["user_id=$1", "deleted_at IS NULL", "title ILIKE $2"]
    vals: list[Any] = [user_id, f"%{title}%"]
    if subsection_id is not None:
        clauses.append(f"subsection_id=${len(vals) + 1}")
        vals.append(subsection_id)
    elif section_id is not None:
        clauses.append(
            f"subsection_id IN (SELECT id FROM study_subsections "
            f"WHERE section_id=${len(vals) + 1} AND deleted_at IS NULL)"
        )
        vals.append(section_id)
    rows = await conn.fetch(
        f"SELECT id, title FROM study_topics WHERE {' AND '.join(clauses)} "
        "ORDER BY position ASC, id ASC LIMIT 5",
        *vals,
    )
    if not rows:
        return None, {"error": "not_found", "title": title}
    if len(rows) > 1:
        return None, {
            "ambiguous": True,
            "candidates": [{"id": r["id"], "title": r["title"]} for r in rows],
            "hint": "Ask the user which topic — never guess.",
        }
    return int(rows[0]["id"]), None


# ---------------------------------------------------------------------------
# Study tracker — read handlers
# ---------------------------------------------------------------------------


async def _list_study_plan(
    args: dict[str, Any], ctx: ToolContext
) -> dict[str, Any]:
    plan = await study_repo.list_plan(ctx.conn, ctx.user_id)
    return {
        "sections": [
            {
                "id": s.id,
                "name": s.name,
                "subsections": [
                    {
                        "id": sub.id,
                        "name": sub.name,
                        "topics": [
                            {
                                "id": t.id,
                                "title": t.title,
                                "status": t.status,
                                "revision_count": t.revision_count,
                            }
                            for t in sub.topics
                        ],
                    }
                    for sub in s.subsections
                ],
            }
            for s in plan.sections
        ],
    }


async def _get_study_progress(
    args: dict[str, Any], ctx: ToolContext
) -> dict[str, Any]:
    return await study_repo.progress(ctx.conn, ctx.user_id)


async def _list_due_topics(
    args: dict[str, Any], ctx: ToolContext
) -> dict[str, Any]:
    days_stale = max(1, min(int(args.get("days_stale") or 14), 365))
    rows = await ctx.conn.fetch(
        """
        SELECT st.id, st.title, st.status, st.revision_count, st.last_revised_at,
               ss.name AS subsection_name, sec.name AS section_name
        FROM study_topics st
        JOIN study_subsections ss  ON ss.id  = st.subsection_id
        JOIN study_sections    sec ON sec.id = ss.section_id
        WHERE st.user_id = $1 AND st.deleted_at IS NULL
          AND st.status IN ('done','mastered')
          AND (
              st.last_revised_at IS NULL
              OR st.last_revised_at < NOW() - ($2::int * INTERVAL '1 day')
          )
        ORDER BY st.last_revised_at ASC NULLS FIRST
        LIMIT 20
        """,
        ctx.user_id, days_stale,
    )
    return {
        "count": len(rows),
        "topics": [
            {
                "id": r["id"],
                "title": r["title"],
                "status": r["status"],
                "revision_count": r["revision_count"],
                "last_revised_at": (
                    r["last_revised_at"].isoformat() if r["last_revised_at"] else None
                ),
                "subsection": r["subsection_name"],
                "section": r["section_name"],
            }
            for r in rows
        ],
    }


# ---------------------------------------------------------------------------
# Study tracker — write handlers
# ---------------------------------------------------------------------------


async def _add_study_section(
    args: dict[str, Any], ctx: ToolContext
) -> dict[str, Any]:
    name = (args.get("name") or "").strip()
    if not name:
        return {"error": "missing name"}
    async with ctx.conn.transaction():
        sec = await study_repo.create_section(
            ctx.conn, ctx.user_id, StudySectionCreate(name=name)
        )
        await gamify.record_event(
            ctx.conn, ctx.user_id, "study.section_added",
            ref_type="study_section", ref_id=sec.id,
        )
    return {"ok": True, "section": {"id": sec.id, "name": sec.name}}


async def _add_study_subsection(
    args: dict[str, Any], ctx: ToolContext
) -> dict[str, Any]:
    name = (args.get("name") or "").strip()
    if not name:
        return {"error": "missing name"}
    sec_id, err = await _resolve_section(
        ctx.conn, ctx.user_id, args.get("section_id"), args.get("section_name")
    )
    if err:
        return err
    try:
        sub = await study_repo.create_subsection(
            ctx.conn, sec_id, ctx.user_id, StudySubsectionCreate(name=name)
        )
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)[:160]}
    return {"ok": True, "subsection": {"id": sub.id, "name": sub.name, "section_id": sub.section_id}}


async def _add_study_topic(
    args: dict[str, Any], ctx: ToolContext
) -> dict[str, Any]:
    title = (args.get("title") or "").strip()
    if not title:
        return {"error": "missing title"}
    notes = args.get("notes") or None

    sub_id_raw = args.get("subsection_id")
    section_name = args.get("section_name")
    subsection_name = args.get("subsection_name")

    if sub_id_raw is not None:
        sub_id, err = int(sub_id_raw), None
    elif section_name and subsection_name:
        sec_id, err = await _resolve_section(ctx.conn, ctx.user_id, None, section_name)
        if err:
            return err
        sub_id, err = await _resolve_subsection(
            ctx.conn, ctx.user_id, None, sec_id, subsection_name
        )
    else:
        return {"error": "must provide subsection_id or (section_name + subsection_name)"}

    if err:
        return err
    try:
        topic = await study_repo.create_topic(
            ctx.conn, sub_id, ctx.user_id, StudyTopicCreate(title=title, notes=notes)
        )
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)[:160]}
    return {"ok": True, "topic": {"id": topic.id, "title": topic.title, "status": topic.status}}


async def _update_study_topic(
    args: dict[str, Any], ctx: ToolContext
) -> dict[str, Any]:
    from app.models import StudyTopicUpdate

    topic_id = args.get("topic_id") or args.get("id")
    if not topic_id:
        return {"error": "missing topic_id"}
    fields: dict[str, Any] = {}
    for key in ("title", "notes", "kind", "status"):
        if key in args and args[key] is not None:
            fields[key] = args[key]
    if not fields:
        return {"error": "no fields to update"}
    try:
        topic = await study_repo.update_topic(
            ctx.conn, int(topic_id), ctx.user_id, StudyTopicUpdate(**fields)
        )
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)[:160]}
    return {"ok": True, "topic": {"id": topic.id, "title": topic.title, "status": topic.status}}


async def _mark_topic_revised(
    args: dict[str, Any], ctx: ToolContext
) -> dict[str, Any]:
    # Resolve section/subsection context for finer-grained title lookups.
    sec_id: int | None = None
    sub_id: int | None = None
    if args.get("section_name"):
        sec_id_r, err = await _resolve_section(
            ctx.conn, ctx.user_id, None, args["section_name"]
        )
        if err:
            return err
        sec_id = sec_id_r
    if args.get("subsection_name") and sec_id is not None:
        sub_id_r, err = await _resolve_subsection(
            ctx.conn, ctx.user_id, None, sec_id, args["subsection_name"]
        )
        if err:
            return err
        sub_id = sub_id_r

    topic_id, err = await _resolve_topic(
        ctx.conn, ctx.user_id,
        args.get("topic_id"), args.get("title"),
        subsection_id=sub_id, section_id=sec_id,
    )
    if err:
        return err

    try:
        async with ctx.conn.transaction():
            updated = await study_repo.revise_topic(ctx.conn, topic_id, ctx.user_id)
            event_key = (
                "study.topic_revised_first"
                if updated.revision_count == 1
                else "study.topic_revised_again"
            )
            gam = await gamify.record_event(
                ctx.conn, ctx.user_id, event_key,
                ref_type="topic",
                ref_id=updated.id * 1000 + updated.revision_count,
            )
            if updated.status == "mastered":
                m_gam = await gamify.record_event(
                    ctx.conn, ctx.user_id, "study.topic_mastered",
                    ref_type="topic", ref_id=updated.id,
                )
                _study_merge(gam, m_gam)
            if await study_repo.is_subsection_complete(
                ctx.conn, updated.subsection_id, ctx.user_id
            ):
                sub = await study_repo.get_subsection(
                    ctx.conn, updated.subsection_id, ctx.user_id
                )
                sub_gam = await gamify.record_event(
                    ctx.conn, ctx.user_id, "study.subsection_completed",
                    ref_type="subsection", ref_id=updated.subsection_id,
                )
                _study_merge(gam, sub_gam)
                if await study_repo.is_section_complete(
                    ctx.conn, sub.section_id, ctx.user_id
                ):
                    sec_gam = await gamify.record_event(
                        ctx.conn, ctx.user_id, "study.section_completed",
                        ref_type="section", ref_id=sub.section_id,
                    )
                    _study_merge(gam, sec_gam)
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)[:160]}

    msg = f"Marked '{updated.title}' as revised (revision #{updated.revision_count})."
    if updated.status == "mastered":
        msg += " Topic mastered! ⭐"
    return {
        "ok": True,
        "topic": {
            "id": updated.id,
            "title": updated.title,
            "status": updated.status,
            "revision_count": updated.revision_count,
        },
        "xp_gained": gam.xp_gained,
        "unlocked": gam.unlocked,
        "quest_completed": gam.quest_completed,
        "new_level": gam.new_level,
        "message": msg,
    }


async def _unmark_study_topic(
    args: dict[str, Any], ctx: ToolContext
) -> dict[str, Any]:
    topic_id, err = await _resolve_topic(
        ctx.conn, ctx.user_id, args.get("topic_id"), args.get("title")
    )
    if err:
        return err
    try:
        topic = await study_repo.unmark_topic(ctx.conn, topic_id, ctx.user_id)
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)[:160]}
    return {
        "ok": True,
        "topic": {"id": topic.id, "title": topic.title, "status": topic.status},
        "message": f"Reset '{topic.title}' to todo. Revision count preserved.",
    }


async def _delete_study_section(
    args: dict[str, Any], ctx: ToolContext
) -> dict[str, Any]:
    sec_id = args.get("id")
    if not sec_id:
        return {"error": "missing id"}
    try:
        async with ctx.conn.transaction():
            await study_repo.soft_delete_section(ctx.conn, int(sec_id), ctx.user_id)
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)[:160]}
    return {"ok": True, "id": int(sec_id)}


async def _delete_study_subsection(
    args: dict[str, Any], ctx: ToolContext
) -> dict[str, Any]:
    sub_id = args.get("id")
    if not sub_id:
        return {"error": "missing id"}
    try:
        async with ctx.conn.transaction():
            await study_repo.soft_delete_subsection(ctx.conn, int(sub_id), ctx.user_id)
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)[:160]}
    return {"ok": True, "id": int(sub_id)}


async def _delete_study_topic(
    args: dict[str, Any], ctx: ToolContext
) -> dict[str, Any]:
    topic_id = args.get("id")
    if not topic_id:
        return {"error": "missing id"}
    try:
        await study_repo.soft_delete_topic(ctx.conn, int(topic_id), ctx.user_id)
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)[:160]}
    return {"ok": True, "id": int(topic_id)}


async def _preview_delete_study_section(
    args: dict[str, Any], ctx: ToolContext
) -> str:
    sec_id = args.get("id")
    try:
        sec = await study_repo.get_section(ctx.conn, int(sec_id), ctx.user_id)
        return f"Delete section '{sec.name}' and all its subsections and topics?"
    except Exception:
        return f"Delete study section id={sec_id}?"


async def _preview_delete_study_subsection(
    args: dict[str, Any], ctx: ToolContext
) -> str:
    sub_id = args.get("id")
    try:
        sub = await study_repo.get_subsection(ctx.conn, int(sub_id), ctx.user_id)
        return f"Delete subsection '{sub.name}' and all its topics?"
    except Exception:
        return f"Delete study subsection id={sub_id}?"


async def _preview_delete_study_topic(
    args: dict[str, Any], ctx: ToolContext
) -> str:
    topic_id = args.get("id")
    try:
        topic = await study_repo.get_topic(ctx.conn, int(topic_id), ctx.user_id)
        return f"Delete topic '{topic.title}'?"
    except Exception:
        return f"Delete study topic id={topic_id}?"


async def _preview_generate_study_plan(
    args: dict[str, Any], ctx: ToolContext
) -> str:
    role = (args.get("role") or "Software Developer").strip()
    companies = args.get("target_companies")
    co_str = f" targeting {', '.join(companies)}" if companies else ""
    return (
        f"Generate and apply a full study plan for '{role}'{co_str}? "
        "This will create multiple sections, subsections, and topics in your plan."
    )


async def _generate_study_plan(
    args: dict[str, Any], ctx: ToolContext
) -> dict[str, Any]:
    role = (args.get("role") or "Software Developer").strip()
    target_companies = args.get("target_companies") or None
    # Pass existing section names to avoid duplication.
    existing_sections = await study_repo.list_sections(ctx.conn, ctx.user_id)
    existing_names = [s.name for s in existing_sections] or None
    try:
        plan = await study_ai.generate_plan(role, target_companies, existing_names)
    except Exception as e:  # noqa: BLE001
        return {"error": f"AI generation failed: {str(e)[:200]}"}

    created: list[str] = []
    total_topics = 0
    for sec_preview in plan.sections:
        sec = await study_repo.create_section(
            ctx.conn, ctx.user_id, StudySectionCreate(name=sec_preview.name)
        )
        await gamify.record_event(
            ctx.conn, ctx.user_id, "study.section_added",
            ref_type="study_section", ref_id=sec.id,
        )
        for sub_preview in sec_preview.subsections:
            sub = await study_repo.create_subsection(
                ctx.conn, sec.id, ctx.user_id, StudySubsectionCreate(name=sub_preview.name)
            )
            for t_preview in sub_preview.topics:
                await study_repo.create_topic(
                    ctx.conn, sub.id, ctx.user_id,
                    StudyTopicCreate(title=t_preview.title, notes=t_preview.notes),
                )
                total_topics += 1
        created.append(sec.name)

    return {
        "ok": True,
        "sections_created": len(created),
        "total_topics": total_topics,
        "section_names": created,
        "message": (
            f"Created {len(created)} sections with {total_topics} topics for '{role}'."
        ),
    }


async def _preview_generate_topics_for_subsection(
    args: dict[str, Any], ctx: ToolContext
) -> str:
    sub_id = args.get("subsection_id")
    count = int(args.get("count") or 10)
    try:
        sub = await study_repo.get_subsection(ctx.conn, int(sub_id), ctx.user_id)
        return f"Generate {count} AI topics for subsection '{sub.name}' and add them to your plan?"
    except Exception:
        return f"Generate {count} AI topics for subsection id={sub_id}?"


async def _generate_topics_for_subsection(
    args: dict[str, Any], ctx: ToolContext
) -> dict[str, Any]:
    sub_id = args.get("subsection_id")
    count = max(1, min(int(args.get("count") or 10), 30))
    hint = args.get("hint") or None
    if not sub_id:
        return {"error": "missing subsection_id"}
    try:
        sub = await study_repo.get_subsection(ctx.conn, int(sub_id), ctx.user_id)
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)[:160]}

    # Get parent section name for the prompt.
    sec_row = await ctx.conn.fetchrow(
        "SELECT name FROM study_sections WHERE id=$1 AND deleted_at IS NULL",
        sub.section_id,
    )
    section_name = sec_row["name"] if sec_row else "Unknown"

    try:
        result = await study_ai.generate_topics(section_name, sub.name, count, hint)
    except Exception as e:  # noqa: BLE001
        return {"error": f"AI generation failed: {str(e)[:200]}"}

    created = 0
    for t_preview in result.topics:
        await study_repo.create_topic(
            ctx.conn, int(sub_id), ctx.user_id,
            StudyTopicCreate(title=t_preview.title, notes=t_preview.notes),
        )
        created += 1
    return {
        "ok": True,
        "subsection": sub.name,
        "topics_added": created,
        "message": f"Added {created} topics to '{sub.name}'.",
    }


# ---------------------------------------------------------------------------
# DSA tracker — read handler
# ---------------------------------------------------------------------------


async def _get_dsa_progress(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    diff_rows = await ctx.conn.fetch(
        """
        SELECT difficulty, COUNT(*) AS cnt
        FROM dsa_problems
        WHERE user_id = $1 AND deleted_at IS NULL
        GROUP BY difficulty
        """,
        ctx.user_id,
    )
    by_difficulty: dict[str, int] = {r["difficulty"]: int(r["cnt"]) for r in diff_rows}
    total_solved = sum(by_difficulty.values())

    topic_rows = await ctx.conn.fetch(
        """
        SELECT
            p.topic,
            COUNT(DISTINCT p.id) AS cnt,
            COUNT(DISTINCT p.id) FILTER (WHERE a.id IS NOT NULL) AS analyzed
        FROM dsa_problems p
        LEFT JOIN dsa_analyses a ON a.problem_id = p.id AND a.user_id = p.user_id
        WHERE p.user_id = $1 AND p.deleted_at IS NULL
        GROUP BY p.topic
        ORDER BY cnt DESC
        """,
        ctx.user_id,
    )

    analyzed_count: int = await ctx.conn.fetchval(
        "SELECT COUNT(DISTINCT problem_id) FROM dsa_analyses WHERE user_id = $1",
        ctx.user_id,
    ) or 0

    streak_days: int = await ctx.conn.fetchval(
        """
        WITH daily AS (
            SELECT DISTINCT DATE(solved_at AT TIME ZONE 'UTC') AS d
            FROM dsa_problems
            WHERE user_id = $1 AND deleted_at IS NULL
        ),
        numbered AS (
            SELECT d, ROW_NUMBER() OVER (ORDER BY d DESC) AS rn FROM daily
        )
        SELECT COUNT(*) FROM numbered
        WHERE d = (CURRENT_DATE - (rn - 1) * INTERVAL '1 day')::date
        """,
        ctx.user_id,
    ) or 0

    recent_rows = await ctx.conn.fetch(
        """
        SELECT title, topic, difficulty, solved_at
        FROM dsa_problems
        WHERE user_id = $1 AND deleted_at IS NULL
        ORDER BY solved_at DESC LIMIT 5
        """,
        ctx.user_id,
    )

    strong_topics = [r["topic"] for r in topic_rows if int(r["cnt"]) >= 5]
    needs_practice = [r["topic"] for r in topic_rows if int(r["cnt"]) < 3]

    return {
        "total_solved": total_solved,
        "by_difficulty": by_difficulty,
        "analyzed_count": analyzed_count,
        "streak_days": int(streak_days),
        "topics": [
            {"topic": r["topic"], "count": int(r["cnt"]), "analyzed": int(r["analyzed"])}
            for r in topic_rows
        ],
        "strong_topics": strong_topics,
        "needs_more_practice": needs_practice[:5],
        "recent_problems": [
            {
                "title": r["title"],
                "topic": r["topic"],
                "difficulty": r["difficulty"],
                "solved_at": r["solved_at"].isoformat(),
            }
            for r in recent_rows
        ],
    }


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

_STR = {"type": "string"}
_INT = {"type": "integer"}
_BOOL = {"type": "boolean"}

TOOLS: list[Tool] = [
    Tool(
        name="get_profile",
        description=(
            "Get the signed-in user's display name, email, timezone, and "
            "member-since date. Use when the user asks who they are to Pilot."
        ),
        parameters={"type": "object", "properties": {}},
        handler=_get_profile,
    ),
    Tool(
        name="get_stats",
        description=(
            "Aggregate counts (applications, referrals, response rate) for "
            "the user over a given period. Use whenever the user asks 'how "
            "many', 'how am I doing', 'my progress', 'today\'s progress', "
            "'what did I do today', 'this week\'s progress', 'my stats', "
            "or 'give me a summary'."
        ),
        parameters={
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "enum": ["today", "week", "month", "all"],
                    "description": "Time window for the aggregation.",
                }
            },
            "required": ["period"],
        },
        handler=_get_stats,
    ),
    Tool(
        name="get_xp_state",
        description=(
            "Get gamification state: current level, XP, streak, freezes, and "
            "today's daily plus weekly quests with their progress."
        ),
        parameters={"type": "object", "properties": {}},
        handler=_get_xp_state,
    ),
    Tool(
        name="list_applications",
        description=(
            "List the user's job applications. Optional filters narrow the "
            "result by company name (substring match, case insensitive), "
            "status, or source. Default returns the 20 most recently updated."
        ),
        parameters={
            "type": "object",
            "properties": {
                "company": {"type": "string", "description": "Company substring filter."},
                "status": {
                    "type": "string",
                    "enum": [
                        "Applied", "Screening", "Interview", "Offer",
                        "Rejected", "Ghosted",
                    ],
                },
                "source": {
                    "type": "string",
                    "enum": [
                        "LinkedIn", "Naukri", "Referral", "CompanySite", "Other",
                    ],
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": 100},
            },
        },
        handler=_list_applications,
    ),
    Tool(
        name="get_application",
        description=(
            "Fetch the full record of a single application, including JD "
            "text, notes, and follow-up history. Pass either 'id' or "
            "'company' (and optionally 'role') to locate the row. If "
            "multiple matches are found the tool returns 'ambiguous: true' "
            "with candidates — ask the user which one, never guess."
        ),
        parameters={
            "type": "object",
            "properties": {
                "id": _INT,
                "company": _STR,
                "role": _STR,
            },
        },
        handler=_get_application,
    ),
    Tool(
        name="list_referrals",
        description=(
            "List the user's referral contacts. Optional filters by company "
            "or connection_status."
        ),
        parameters={
            "type": "object",
            "properties": {
                "company": _STR,
                "connection_status": {
                    "type": "string",
                    "enum": [
                        "Request Sent", "Accepted", "Msg Sent", "Replied",
                        "Referred", "Dropped",
                    ],
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": 100},
            },
        },
        handler=_list_referrals,
    ),
    Tool(
        name="get_referral",
        description=(
            "Fetch a single referral contact by id or by name (substring "
            "match). Returns ambiguous candidates if multiple match — ask "
            "the user to clarify."
        ),
        parameters={
            "type": "object",
            "properties": {"id": _INT, "name": _STR},
        },
        handler=_get_referral,
    ),
    Tool(
        name="list_recent_activity",
        description=(
            "Recent events on the user's account (applications added, "
            "statuses changed, referrals updated, drafts generated). "
            "Defaults to the last 7 days, max 30."
        ),
        parameters={
            "type": "object",
            "properties": {
                "days": {"type": "integer", "minimum": 1, "maximum": 30},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
            },
        },
        handler=_list_recent_activity,
    ),
    Tool(
        name="list_pending_nudges",
        description=(
            "Today's pending nudges for the user — follow-ups that are due, "
            "stale applications, referrals waiting on a reply. Already-read, "
            "acted-on, and snoozed nudges are excluded."
        ),
        parameters={"type": "object", "properties": {}},
        handler=_list_pending_nudges,
    ),
    Tool(
        name="list_drafts",
        description=(
            "Recent AI-generated drafts (follow-up emails, referral asks). "
            "Optional filter by entity_type ('application' or 'referral') "
            "and entity_id to scope to a single record."
        ),
        parameters={
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "enum": ["application", "referral"],
                },
                "entity_id": _INT,
                "limit": {"type": "integer", "minimum": 1, "maximum": 25},
            },
        },
        handler=_list_drafts,
    ),
    Tool(
        name="list_achievements",
        description=(
            "Full list of achievements with unlocked state. Pass "
            "'unlocked: true' for only-unlocked or 'unlocked: false' for "
            "only-locked."
        ),
        parameters={
            "type": "object",
            "properties": {"unlocked": _BOOL},
        },
        handler=_list_achievements,
    ),

    # ── Write tools ──────────────────────────────────────────────────────

    Tool(
        name="add_application",
        description=(
            "Create a new job application. Required: company, role. "
            "Optional: source (defaults to 'Other'), applied_date "
            "(defaults to today), jd_url, jd_text, contact_name, notes. "
            "Returns the created row with its id."
        ),
        parameters={
            "type": "object",
            "properties": {
                "company": _STR, "role": _STR,
                "source": {"type": "string", "enum": sorted(_VALID_SOURCES)},
                "applied_date": {"type": "string", "description": "ISO-8601 YYYY-MM-DD"},
                "jd_url": _STR, "jd_text": _STR,
                "contact_name": _STR, "notes": _STR,
            },
            "required": ["company", "role"],
        },
        handler=_add_application,
        side_effects=True,
    ),
    Tool(
        name="update_application",
        description=(
            "Update fields on an existing application. Pass 'id' plus any "
            "of: company, role, source, applied_date, status, notes, "
            "fit_score, salary_discussed, contact_name, contact_linkedin, "
            "jd_url, jd_text. Moves to Rejected/Ghosted/Offer require "
            "confirmation."
        ),
        parameters={
            "type": "object",
            "properties": {
                "id": _INT,
                "company": _STR, "role": _STR,
                "source": {"type": "string", "enum": sorted(_VALID_SOURCES)},
                "applied_date": _STR,
                "status": {"type": "string", "enum": sorted(_VALID_STATUSES)},
                "notes": _STR, "fit_score": _INT,
                "salary_discussed": _STR,
                "contact_name": _STR, "contact_linkedin": _STR,
                "jd_url": _STR, "jd_text": _STR,
            },
            "required": ["id"],
        },
        handler=_update_application,
        side_effects=True,
        confirms=_confirm_status_is_final,
        preview=_preview_finalize_application,
    ),
    Tool(
        name="move_application_status",
        description=(
            "Move an application's status. Convenience around "
            "update_application that only changes the status. Final "
            "statuses (Rejected/Ghosted/Offer) require confirmation."
        ),
        parameters={
            "type": "object",
            "properties": {
                "id": _INT,
                "new_status": {
                    "type": "string", "enum": sorted(_VALID_STATUSES),
                },
            },
            "required": ["id", "new_status"],
        },
        handler=_move_application_status,
        side_effects=True,
        confirms=lambda args: (args.get("new_status") in _FINAL_APP_STATUSES),
        preview=_preview_finalize_application,
    ),
    Tool(
        name="delete_application",
        description=(
            "Soft-delete an application by id. Always requires "
            "confirmation."
        ),
        parameters={
            "type": "object",
            "properties": {"id": _INT},
            "required": ["id"],
        },
        handler=_delete_application,
        side_effects=True,
        confirms=True,
        preview=_preview_delete_application,
    ),
    Tool(
        name="add_note_to_application",
        description=(
            "Append a dated note to an application's notes field. The new "
            "note is prepended with today's date in [YYYY-MM-DD] format."
        ),
        parameters={
            "type": "object",
            "properties": {"id": _INT, "text": _STR},
            "required": ["id", "text"],
        },
        handler=_add_note_to_application,
        side_effects=True,
    ),
    Tool(
        name="add_referral",
        description=(
            "Create a new referral contact. Required: name, company, "
            "target_role. Optional: role_at_company, linkedin_url, "
            "mutual_context, notes, connection_sent_date (defaults to today)."
        ),
        parameters={
            "type": "object",
            "properties": {
                "name": _STR, "company": _STR, "target_role": _STR,
                "role_at_company": _STR, "linkedin_url": _STR,
                "mutual_context": _STR, "notes": _STR,
                "connection_sent_date": _STR,
            },
            "required": ["name", "company", "target_role"],
        },
        handler=_add_referral,
        side_effects=True,
    ),
    Tool(
        name="update_referral",
        description=(
            "Update fields on an existing referral contact by id. Pass any "
            "of: name, company, target_role, role_at_company, linkedin_url, "
            "mutual_context, connection_status, referral_msg_sent_date, "
            "reply_date, outcome, notes."
        ),
        parameters={
            "type": "object",
            "properties": {
                "id": _INT,
                "name": _STR, "company": _STR, "target_role": _STR,
                "role_at_company": _STR, "linkedin_url": _STR,
                "mutual_context": _STR,
                "connection_status": {
                    "type": "string", "enum": sorted(_VALID_CONN_STATUSES),
                },
                "referral_msg_sent_date": _STR, "reply_date": _STR,
                "outcome": {
                    "type": "string", "enum": ["Referred", "NoResponse", "Declined"],
                },
                "notes": _STR,
            },
            "required": ["id"],
        },
        handler=_update_referral,
        side_effects=True,
    ),
    Tool(
        name="delete_referral",
        description="Soft-delete a referral contact. Always requires confirmation.",
        parameters={
            "type": "object",
            "properties": {"id": _INT},
            "required": ["id"],
        },
        handler=_delete_referral,
        side_effects=True,
        confirms=True,
        preview=_preview_delete_referral,
    ),
    Tool(
        name="mark_referral_accepted",
        description="Mark a referral as Accepted (their LinkedIn request was accepted).",
        parameters={
            "type": "object", "properties": {"id": _INT}, "required": ["id"],
        },
        handler=lambda args, ctx: _mark_referral(args, ctx, "accepted"),
        side_effects=True,
    ),
    Tool(
        name="mark_referral_sent",
        description="Mark a referral message as sent.",
        parameters={
            "type": "object", "properties": {"id": _INT}, "required": ["id"],
        },
        handler=lambda args, ctx: _mark_referral(args, ctx, "sent"),
        side_effects=True,
    ),
    Tool(
        name="mark_referral_replied",
        description="Mark a referral contact as having replied to the message.",
        parameters={
            "type": "object", "properties": {"id": _INT}, "required": ["id"],
        },
        handler=lambda args, ctx: _mark_referral(args, ctx, "replied"),
        side_effects=True,
    ),
    Tool(
        name="link_referral_to_application",
        description=(
            "Link a referral contact to an application — useful when the "
            "referral helped land the role."
        ),
        parameters={
            "type": "object",
            "properties": {
                "referral_id": _INT,
                "application_id": _INT,
            },
            "required": ["referral_id", "application_id"],
        },
        handler=_link_referral_to_application,
        side_effects=True,
    ),
    Tool(
        name="unlink_referral_from_application",
        description="Remove a referral↔application link.",
        parameters={
            "type": "object",
            "properties": {
                "referral_id": _INT,
                "application_id": _INT,
            },
            "required": ["referral_id", "application_id"],
        },
        handler=_unlink_referral_from_application,
        side_effects=True,
    ),
    Tool(
        name="generate_followup_draft",
        description=(
            "Generate and save an AI follow-up email draft for an "
            "application. Returns the draft text — the user can copy "
            "and send it themselves."
        ),
        parameters={
            "type": "object",
            "properties": {"application_id": _INT},
            "required": ["application_id"],
        },
        handler=_generate_followup_draft,
        side_effects=True,
    ),
    Tool(
        name="generate_referral_ask",
        description=(
            "Generate and save an AI referral-ask DM for a referral "
            "contact. Returns the draft text."
        ),
        parameters={
            "type": "object",
            "properties": {"referral_id": _INT},
            "required": ["referral_id"],
        },
        handler=_generate_referral_ask,
        side_effects=True,
    ),

    # ── DSA Practice tracker ─────────────────────────────────────────────

    Tool(
        name="get_dsa_progress",
        description=(
            "Get the user's DSA (Data Structures & Algorithms) practice progress: "
            "total problems solved, breakdown by difficulty (easy/medium/hard), "
            "per-topic problem counts, AI-analyzed count, current streak days, "
            "and the 5 most recently solved problems. Also returns which topics "
            "look strong (5+ problems) vs need more practice (<3 problems). "
            "Use when the user asks about their DSA practice, coding interview "
            "prep, or algorithm skills. "
            "IMPORTANT — READ ONLY: You cannot add, log, or create a DSA problem "
            "via voice. If the user asks you to log a problem, politely explain "
            "that this must be done manually from the DSA Practice page in the app "
            "because logging requires pasting code, a link, and description that "
            "voice input cannot capture accurately."
        ),
        parameters={"type": "object", "properties": {}},
        handler=_get_dsa_progress,
    ),

    # ── Study tracker — read tools ────────────────────────────────────────

    Tool(
        name="list_study_plan",
        description=(
            "Return the full study plan tree: sections → subsections → topics "
            "with their status and revision count. Use when the user asks "
            "what topics they have, what they've revised, or how their plan looks."
        ),
        parameters={"type": "object", "properties": {}},
        handler=_list_study_plan,
    ),
    Tool(
        name="get_study_progress",
        description=(
            "Aggregate study stats: total topics, todo/done/mastered counts, "
            "revisions this week, and topics due for review."
        ),
        parameters={"type": "object", "properties": {}},
        handler=_get_study_progress,
    ),
    Tool(
        name="list_due_topics",
        description=(
            "List topics that are done or mastered but haven't been revised "
            "recently (default: 14 days). Use when the user asks what they "
            "should review today."
        ),
        parameters={
            "type": "object",
            "properties": {
                "days_stale": {
                    "type": "integer",
                    "description": "Consider a topic stale after this many days (default 14).",
                    "minimum": 1,
                    "maximum": 365,
                }
            },
        },
        handler=_list_due_topics,
    ),

    # ── Study tracker — write tools ───────────────────────────────────────

    Tool(
        name="add_study_section",
        description=(
            "Create a new top-level section in the user's study plan "
            "(e.g. 'Backend', 'System Design'). Returns the created section."
        ),
        parameters={
            "type": "object",
            "properties": {
                "name": _STR,
                "icon": {"type": "string", "description": "Optional emoji."},
            },
            "required": ["name"],
        },
        handler=_add_study_section,
        side_effects=True,
    ),
    Tool(
        name="add_study_subsection",
        description=(
            "Add a subsection under an existing section. Pass either "
            "section_id (exact) or section_name (substring match). "
            "Returns ambiguous candidates if multiple sections match."
        ),
        parameters={
            "type": "object",
            "properties": {
                "name": _STR,
                "section_id": _INT,
                "section_name": _STR,
            },
            "required": ["name"],
        },
        handler=_add_study_subsection,
        side_effects=True,
    ),
    Tool(
        name="add_study_topic",
        description=(
            "Add a topic to a subsection. Pass subsection_id, or pass "
            "section_name + subsection_name for voice-friendly lookup. "
            "Returns ambiguous candidates if multiple subsections match."
        ),
        parameters={
            "type": "object",
            "properties": {
                "title": _STR,
                "notes": {"type": "string", "description": "Short notes or keywords."},
                "subsection_id": _INT,
                "section_name": _STR,
                "subsection_name": _STR,
            },
            "required": ["title"],
        },
        handler=_add_study_topic,
        side_effects=True,
    ),
    Tool(
        name="update_study_topic",
        description=(
            "Update a topic's title, notes, kind (learn/revise), or status. "
            "Pass topic_id (exact)."
        ),
        parameters={
            "type": "object",
            "properties": {
                "topic_id": _INT,
                "title": _STR,
                "notes": _STR,
                "kind": {"type": "string", "enum": ["learn", "revise"]},
                "status": {
                    "type": "string",
                    "enum": ["todo", "in_progress", "done", "mastered"],
                },
            },
            "required": ["topic_id"],
        },
        handler=_update_study_topic,
        side_effects=True,
    ),
    Tool(
        name="mark_topic_revised",
        description=(
            "Mark a topic as revised (increments revision count, awards XP). "
            "Pass topic_id, or title + optional section_name/subsection_name "
            "for voice-friendly lookup. Returns ambiguous candidates if multiple "
            "topics with that title exist."
        ),
        parameters={
            "type": "object",
            "properties": {
                "topic_id": _INT,
                "title": _STR,
                "section_name": _STR,
                "subsection_name": _STR,
            },
        },
        handler=_mark_topic_revised,
        side_effects=True,
    ),
    Tool(
        name="unmark_study_topic",
        description=(
            "Reset a topic's status back to 'todo'. Revision count and XP "
            "are preserved — this only resets the checkbox. Pass topic_id or title."
        ),
        parameters={
            "type": "object",
            "properties": {
                "topic_id": _INT,
                "title": _STR,
            },
        },
        handler=_unmark_study_topic,
        side_effects=True,
    ),
    Tool(
        name="delete_study_section",
        description=(
            "Soft-delete a section and all its subsections and topics. "
            "Always requires confirmation — this is irreversible."
        ),
        parameters={
            "type": "object",
            "properties": {"id": _INT},
            "required": ["id"],
        },
        handler=_delete_study_section,
        side_effects=True,
        confirms=True,
        preview=_preview_delete_study_section,
    ),
    Tool(
        name="delete_study_subsection",
        description=(
            "Soft-delete a subsection and all its topics. "
            "Always requires confirmation."
        ),
        parameters={
            "type": "object",
            "properties": {"id": _INT},
            "required": ["id"],
        },
        handler=_delete_study_subsection,
        side_effects=True,
        confirms=True,
        preview=_preview_delete_study_subsection,
    ),
    Tool(
        name="delete_study_topic",
        description=(
            "Soft-delete a single topic. Always requires confirmation."
        ),
        parameters={
            "type": "object",
            "properties": {"id": _INT},
            "required": ["id"],
        },
        handler=_delete_study_topic,
        side_effects=True,
        confirms=True,
        preview=_preview_delete_study_topic,
    ),
    Tool(
        name="generate_study_plan",
        description=(
            "Generate a full study plan using AI and apply it to the user's "
            "study tracker. Requires confirmation before applying — the "
            "confirmation message summarises what will be created. "
            "Pass the user's role and optionally target companies."
        ),
        parameters={
            "type": "object",
            "properties": {
                "role": {
                    "type": "string",
                    "description": "Engineer role (e.g. 'Full Stack Java Developer').",
                },
                "target_companies": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Companies to tailor the plan for.",
                },
            },
        },
        handler=_generate_study_plan,
        side_effects=True,
        confirms=True,
        preview=_preview_generate_study_plan,
    ),
    Tool(
        name="generate_topics_for_subsection",
        description=(
            "Generate AI topic suggestions for a specific subsection and add "
            "them to the plan. Requires confirmation. Pass subsection_id "
            "and optionally count (1–30, default 10) and a hint string."
        ),
        parameters={
            "type": "object",
            "properties": {
                "subsection_id": _INT,
                "count": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 30,
                    "description": "Number of topics to generate.",
                },
                "hint": {
                    "type": "string",
                    "description": "Focus instruction (e.g. 'interview gotchas').",
                },
            },
            "required": ["subsection_id"],
        },
        handler=_generate_topics_for_subsection,
        side_effects=True,
        confirms=True,
        preview=_preview_generate_topics_for_subsection,
    ),
]

_BY_NAME: dict[str, Tool] = {t.name: t for t in TOOLS}


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


async def dispatch(name: str, args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    tool = _BY_NAME.get(name)
    if tool is None:
        return {"error": f"unknown tool: {name}"}

    args = dict(args or {})
    confirm_token = args.pop("confirm_token", None)

    needs = (
        tool.confirms
        if isinstance(tool.confirms, bool)
        else bool(tool.confirms(args))
    )
    if needs:
        if not confirm_token:
            summary = (
                await tool.preview(args, ctx)
                if tool.preview is not None
                else f"Confirm {tool.name}?"
            )
            return await _issue_confirmation(name, args, ctx, summary)
        ok = await _consume_confirmation(confirm_token, name, args, ctx)
        if not ok:
            return {
                "error": "confirmation token invalid or expired",
                "hint": (
                    "Ask the user to confirm again; you'll be issued a "
                    "fresh token next call."
                ),
            }

    try:
        result = await tool.handler(args, ctx)
    except Exception as e:  # noqa: BLE001
        log.exception("tool.error", tool=name, error=str(e))
        return {"error": f"{type(e).__name__}: {str(e)[:200]}"}
    log.info(
        "tool.ok", tool=name, args=_redact(args),
        side_effects=tool.side_effects, keys=list(result.keys()),
    )
    return result


def _redact(args: dict[str, Any]) -> dict[str, Any]:
    """Strip long fields from logs to keep the structured log tidy."""
    out = {}
    for k, v in args.items():
        if isinstance(v, str) and len(v) > 80:
            out[k] = v[:60] + "…"
        else:
            out[k] = v
    return out
