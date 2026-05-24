"""
Weekly email digest: sent every Monday at 08:00 UTC.
Pulls last-7-day stats, nudges, streak, and DSA progress for every user
who has email and has digest_enabled (defaults True for all users).

Uses Resend REST API via httpx (already a project dependency).
No extra library needed.
"""
import datetime as dt
import html
import logging
from textwrap import dedent

import asyncpg
import httpx

from app.config import settings
from app.database import pool

log = logging.getLogger("email_digest")

_RESEND_SEND_URL = "https://api.resend.com/emails"


async def send_weekly_digest_for_all() -> None:
    if not settings.digest_enabled:
        log.info("digest.skipped digest_enabled=False")
        return
    api_key = settings.resend_api_key.get_secret_value()
    if not api_key:
        log.warning("digest.skipped no RESEND_API_KEY configured")
        return

    # Collect all data while holding the connection, then release before HTTP
    user_payloads: list[dict] = []
    async with pool().acquire() as conn:
        users = await conn.fetch(
            """
            SELECT id, email, display_name
            FROM users
            WHERE deleted_at IS NULL
              AND email IS NOT NULL
              AND email != ''
            ORDER BY id
            """
        )
        log.info("digest.starting user_count=%d", len(users))
        for user in users:
            try:
                payload = await _collect_user_data(conn, dict(user))
                user_payloads.append(payload)
            except Exception as exc:  # noqa: BLE001
                log.exception("digest.collect_failed user_id=%d error=%s", user["id"], exc)

    # Send emails after releasing the DB connection
    async with httpx.AsyncClient(timeout=30.0) as client:
        for payload in user_payloads:
            try:
                await _send_email(client, api_key, payload)
            except Exception as exc:  # noqa: BLE001
                log.exception("digest.send_failed user_id=%d error=%s", payload["user_id"], exc)
    log.info("digest.done")


async def send_digest_for_user(user_id: int) -> None:
    """Send the weekly digest to a single user. Used for dev testing."""
    api_key = settings.resend_api_key.get_secret_value()
    if not api_key:
        log.warning("digest.skipped no RESEND_API_KEY configured")
        return

    async with pool().acquire() as conn:
        user = await conn.fetchrow(
            "SELECT id, email, display_name FROM users WHERE id = $1 AND deleted_at IS NULL",
            user_id,
        )
        if not user or not user["email"]:
            log.warning("digest.skipped user_id=%d no email", user_id)
            return
        payload = await _collect_user_data(conn, dict(user))

    async with httpx.AsyncClient(timeout=30.0) as client:
        await _send_email(client, api_key, payload)


async def _collect_user_data(conn: asyncpg.Connection, user: dict) -> dict:
    user_id: int = user["id"]
    today = dt.date.today()
    seven_days_ago = today - dt.timedelta(days=7)

    stats = await conn.fetchrow(
        """
        SELECT
          COUNT(*) AS applied,
          COUNT(*) FILTER (WHERE status IN ('Screening','Interview')) AS progressed,
          COUNT(*) FILTER (WHERE status = 'Offer') AS offers,
          COUNT(*) FILTER (WHERE status = 'Ghosted') AS ghosted
        FROM applications
        WHERE user_id = $1
          AND deleted_at IS NULL
          AND applied_date >= $2
        """,
        user_id,
        seven_days_ago,
    )

    gamify = await conn.fetchrow(
        "SELECT xp, level, streak_days FROM gamify_state WHERE user_id = $1",
        user_id,
    )

    dsa = await conn.fetchrow(
        """
        SELECT
          COUNT(*) AS solved_this_week,
          COUNT(*) FILTER (WHERE difficulty = 'hard') AS hard_count
        FROM dsa_problems
        WHERE user_id = $1
          AND deleted_at IS NULL
          AND solved_at >= $2
        """,
        user_id,
        dt.datetime.combine(seven_days_ago, dt.time.min, tzinfo=dt.timezone.utc),
    )

    nudge_rows = await conn.fetch(
        """
        SELECT message
        FROM nudges
        WHERE user_id = $1
          AND deleted_at IS NULL
          AND read_at IS NULL
          AND acted_at IS NULL
          AND (snoozed_until IS NULL OR snoozed_until < $2)
        ORDER BY severity DESC, fired_on_date ASC
        LIMIT 3
        """,
        user_id,
        today,
    )

    return {
        "user_id": user_id,
        "email": user["email"],
        "name": html.escape((user["display_name"] or "").split(" ")[0] or "there"),
        "week_start": seven_days_ago.strftime("%b %d"),
        "week_end": today.strftime("%b %d, %Y"),
        "today": today,
        "applied": int(stats["applied"]),
        "progressed": int(stats["progressed"]),
        "offers": int(stats["offers"]),
        "ghosted": int(stats["ghosted"]),
        "streak": int(gamify["streak_days"]) if gamify else 0,
        "xp": int(gamify["xp"]) if gamify else 0,
        "level": int(gamify["level"]) if gamify else 1,
        "dsa_solved": int(dsa["solved_this_week"]),
        "dsa_hard": int(dsa["hard_count"]),
        "nudges": [r["message"] for r in nudge_rows],
    }


async def _send_email(client: httpx.AsyncClient, api_key: str, payload: dict) -> None:
    user_id: int = payload["user_id"]
    email: str = payload["email"]
    today = payload["today"]

    html_body = _build_html(
        name=payload["name"],
        week_start=payload["week_start"],
        week_end=payload["week_end"],
        applied=payload["applied"],
        progressed=payload["progressed"],
        offers=payload["offers"],
        ghosted=payload["ghosted"],
        streak=payload["streak"],
        xp=payload["xp"],
        level=payload["level"],
        dsa_solved=payload["dsa_solved"],
        dsa_hard=payload["dsa_hard"],
        nudges=payload["nudges"],
    )

    resp = await client.post(
        _RESEND_SEND_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "from": settings.resend_from_email,
            "to": [email],
            "subject": f"Your JobPilot week in review — {today.strftime('%b %d')}",
            "html": html_body,
        },
    )
    if resp.status_code >= 400:
        log.error(
            "digest.resend_error user_id=%d status=%d body=%s",
            user_id, resp.status_code, resp.text[:200],
        )
    else:
        local, domain = email.split("@", 1)
        masked = local[:2] + "***@" + domain
        log.info("digest.sent user_id=%d email=%s", user_id, masked)


def _build_html(
    *,
    name: str,
    week_start: str,
    week_end: str,
    applied: int,
    progressed: int,
    offers: int,
    ghosted: int,
    streak: int,
    xp: int,
    level: int,
    dsa_solved: int,
    dsa_hard: int,
    nudges: list[str],
) -> str:
    nudge_items = "".join(
        f'<li style="margin-bottom:8px;color:#475569;">{html.escape(n)}</li>'
        for n in nudges
    ) or '<li style="color:#94a3b8;">No pending nudges — you\'re on top of it! ✅</li>'

    return dedent(f"""
    <!DOCTYPE html>
    <html lang="en">
    <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Your JobPilot Week in Review</title></head>
    <body style="margin:0;padding:0;background:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc;padding:32px 0;">
        <tr><td align="center">
          <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:16px;border:1px solid #e2e8f0;overflow:hidden;max-width:600px;width:100%;">

            <!-- Header -->
            <tr><td style="background:linear-gradient(135deg,#6366f1,#8b5cf6);padding:32px;text-align:center;">
              <div style="font-size:28px;margin-bottom:4px;">✈️</div>
              <h1 style="color:#ffffff;font-size:22px;font-weight:700;margin:0 0 4px;">JobPilot</h1>
              <p style="color:#e0e7ff;font-size:13px;margin:0;">Week in Review · {week_start} – {week_end}</p>
            </td></tr>

            <!-- Greeting -->
            <tr><td style="padding:28px 32px 0;">
              <p style="font-size:16px;color:#1e293b;margin:0 0 4px;font-weight:600;">Hey {name} 👋</p>
              <p style="font-size:14px;color:#64748b;margin:0;">Here's how your job hunt looked this week.</p>
            </td></tr>

            <!-- Application Stats -->
            <tr><td style="padding:24px 32px 0;">
              <h2 style="font-size:14px;color:#6366f1;text-transform:uppercase;letter-spacing:0.05em;margin:0 0 16px;font-weight:600;">📊 Applications This Week</h2>
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="text-align:center;padding:16px;background:#f8fafc;border-radius:12px;border:1px solid #e2e8f0;" width="25%">
                    <div style="font-size:28px;font-weight:700;color:#6366f1;">{applied}</div>
                    <div style="font-size:11px;color:#94a3b8;margin-top:4px;">Applied</div>
                  </td>
                  <td width="8"></td>
                  <td style="text-align:center;padding:16px;background:#f8fafc;border-radius:12px;border:1px solid #e2e8f0;" width="25%">
                    <div style="font-size:28px;font-weight:700;color:#f59e0b;">{progressed}</div>
                    <div style="font-size:11px;color:#94a3b8;margin-top:4px;">Progressed</div>
                  </td>
                  <td width="8"></td>
                  <td style="text-align:center;padding:16px;background:#f8fafc;border-radius:12px;border:1px solid #e2e8f0;" width="25%">
                    <div style="font-size:28px;font-weight:700;color:#10b981;">{offers}</div>
                    <div style="font-size:11px;color:#94a3b8;margin-top:4px;">Offers</div>
                  </td>
                  <td width="8"></td>
                  <td style="text-align:center;padding:16px;background:#f8fafc;border-radius:12px;border:1px solid #e2e8f0;" width="25%">
                    <div style="font-size:28px;font-weight:700;color:#94a3b8;">{ghosted}</div>
                    <div style="font-size:11px;color:#94a3b8;margin-top:4px;">Ghosted</div>
                  </td>
                </tr>
              </table>
            </td></tr>

            <!-- Streak + XP + DSA -->
            <tr><td style="padding:24px 32px 0;">
              <h2 style="font-size:14px;color:#6366f1;text-transform:uppercase;letter-spacing:0.05em;margin:0 0 16px;font-weight:600;">🎮 Your Progress</h2>
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="padding:16px;background:#fff7ed;border-radius:12px;border:1px solid #fed7aa;" width="32%">
                    <div style="font-size:24px;font-weight:700;color:#ea580c;">{streak} 🔥</div>
                    <div style="font-size:11px;color:#94a3b8;margin-top:4px;">Day streak</div>
                  </td>
                  <td width="8"></td>
                  <td style="padding:16px;background:#f0fdf4;border-radius:12px;border:1px solid #bbf7d0;" width="32%">
                    <div style="font-size:24px;font-weight:700;color:#16a34a;">Lv {level}</div>
                    <div style="font-size:11px;color:#94a3b8;margin-top:4px;">{xp:,} XP total</div>
                  </td>
                  <td width="8"></td>
                  <td style="padding:16px;background:#faf5ff;border-radius:12px;border:1px solid #e9d5ff;" width="32%">
                    <div style="font-size:24px;font-weight:700;color:#7c3aed;">{dsa_solved} DSA</div>
                    <div style="font-size:11px;color:#94a3b8;margin-top:4px;">solved this week{' · ' + str(dsa_hard) + ' hard' if dsa_hard else ''}</div>
                  </td>
                </tr>
              </table>
            </td></tr>

            <!-- Nudges -->
            <tr><td style="padding:24px 32px 0;">
              <h2 style="font-size:14px;color:#6366f1;text-transform:uppercase;letter-spacing:0.05em;margin:0 0 12px;font-weight:600;">📌 Follow-up Reminders</h2>
              <ul style="margin:0;padding-left:20px;font-size:13px;line-height:1.6;">
                {nudge_items}
              </ul>
            </td></tr>

            <!-- CTA -->
            <tr><td style="padding:28px 32px 32px;text-align:center;">
              <a href="{settings.frontend_url}/dashboard"
                 style="display:inline-block;background:#6366f1;color:#ffffff;font-size:14px;font-weight:600;padding:12px 28px;border-radius:8px;text-decoration:none;">
                Open JobPilot →
              </a>
              <p style="font-size:11px;color:#94a3b8;margin:16px 0 0;">
                You're getting this because you have an account at JobPilot.
                To stop receiving these emails, visit your
                <a href="{settings.frontend_url}/dashboard" style="color:#94a3b8;">account settings</a>.
              </p>
            </td></tr>

          </table>
        </td></tr>
      </table>
    </body>
    </html>
    """).strip()
