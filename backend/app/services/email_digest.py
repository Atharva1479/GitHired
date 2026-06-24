"""
Weekly email digest: sent every Sunday at 08:00 UTC.
Pulls last-7-day stats, upcoming interview-stage apps, pending nudges,
streak, and DSA progress for every user who has email set.

Uses Resend REST API via httpx (already a project dependency).
"""
import datetime as dt
import html

import asyncpg
import httpx
import structlog

from app.config import settings

log = structlog.get_logger("email_digest")

_RESEND_SEND_URL = "https://api.resend.com/emails"

# Statuses that represent an active interview in the pipeline
_INTERVIEW_STATUSES = ("Screening", "Phone Screen", "Interview", "Technical", "HR")


async def send_weekly_digest_for_all() -> None:
    if not settings.digest_enabled:
        log.info("digest.skipped digest_enabled=False")
        return
    api_key = settings.resend_api_key.get_secret_value()
    if not api_key:
        log.warning("digest.skipped no RESEND_API_KEY configured")
        return

    user_payloads: list[dict] = []
    async with (await _get_pool()).acquire() as conn:
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
        log.info("digest.starting", user_count=len(users))
        for user in users:
            try:
                payload = await _collect_user_data(conn, dict(user))
                user_payloads.append(payload)
            except Exception as exc:  # noqa: BLE001
                log.exception("digest.collect_failed", user_id=user["id"], error=str(exc))

    async with httpx.AsyncClient(timeout=30.0) as client:
        for payload in user_payloads:
            try:
                await _send_email(client, api_key, payload)
            except Exception as exc:  # noqa: BLE001
                log.exception("digest.send_failed", user_id=payload["user_id"], error=str(exc))
    log.info("digest.done")


async def send_digest_for_user(user_id: int) -> None:
    """Send the weekly digest to a single user. Useful for manual testing."""
    api_key = settings.resend_api_key.get_secret_value()
    if not api_key:
        log.warning("digest.skipped no RESEND_API_KEY configured")
        return

    async with (await _get_pool()).acquire() as conn:
        user = await conn.fetchrow(
            "SELECT id, email, display_name FROM users WHERE id = $1 AND deleted_at IS NULL",
            user_id,
        )
        if not user or not user["email"]:
            log.warning("digest.skipped", user_id=user_id, reason="no_email")
            return
        payload = await _collect_user_data(conn, dict(user))

    async with httpx.AsyncClient(timeout=30.0) as client:
        await _send_email(client, api_key, payload)


async def _get_pool():
    from app.database import pool
    return pool()


async def _collect_user_data(conn: asyncpg.Connection, user: dict) -> dict:
    user_id = user["id"]
    today = dt.date.today()
    seven_days_ago = today - dt.timedelta(days=7)

    # Applications sent this week
    stats = await conn.fetchrow(
        """
        SELECT
          COUNT(*) AS applied,
          COUNT(*) FILTER (WHERE status IN ('Screening','Phone Screen','Interview','Technical','HR')) AS progressed,
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

    # Upcoming interviews: apps currently in interview pipeline (all time, active)
    interview_rows = await conn.fetch(
        """
        SELECT company, role, status, applied_date
        FROM applications
        WHERE user_id = $1
          AND deleted_at IS NULL
          AND status = ANY($2::text[])
        ORDER BY applied_date DESC
        LIMIT 5
        """,
        user_id,
        list(_INTERVIEW_STATUSES),
    )

    # Follow-ups due: unread, unacted nudges
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
        LIMIT 4
        """,
        user_id,
        today,
    )

    # Progress: streak, XP, level
    gamify = await conn.fetchrow(
        "SELECT xp, level, streak_days FROM gamify_state WHERE user_id = $1",
        user_id,
    )

    # DSA activity this week
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

    return {
        "user_id": user_id,
        "email": user["email"],
        "name": html.escape((user["display_name"] or "").split(" ")[0] or "there"),
        "week_start": seven_days_ago.strftime("%b %d"),
        "week_end": today.strftime("%b %d, %Y"),
        "today": today,
        # Weekly stats
        "applied": int(stats["applied"]),
        "progressed": int(stats["progressed"]),
        "offers": int(stats["offers"]),
        "ghosted": int(stats["ghosted"]),
        # Upcoming interviews
        "interviews": [
            {
                "company": html.escape(r["company"]),
                "role": html.escape(r["role"]),
                "status": html.escape(r["status"]),
            }
            for r in interview_rows
        ],
        # Follow-ups
        "nudges": [r["message"] for r in nudge_rows],
        # Progress
        "streak": int(gamify["streak_days"]) if gamify else 0,
        "xp": int(gamify["xp"]) if gamify else 0,
        "level": int(gamify["level"]) if gamify else 1,
        "dsa_solved": int(dsa["solved_this_week"]),
        "dsa_hard": int(dsa["hard_count"]),
    }


async def _send_email(client: httpx.AsyncClient, api_key: str, payload: dict) -> None:
    user_id = payload["user_id"]
    email: str = payload["email"]
    today = payload["today"]

    html_body = _build_html(payload)

    resp = await client.post(
        _RESEND_SEND_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "from": settings.resend_from_email,
            "to": [email],
            "subject": f"Your week in review — {today.strftime('%b %d')} 📊",
            "html": html_body,
        },
    )
    if resp.status_code >= 400:
        log.error(
            "digest.resend_error",
            user_id=user_id,
            status=resp.status_code,
            body=resp.text[:200],
        )
    else:
        local, domain = email.split("@", 1)
        masked = local[:2] + "***@" + domain
        log.info("digest.sent", user_id=user_id, email=masked)


def _build_html(p: dict) -> str:
    name = p["name"]
    week_start = p["week_start"]
    week_end = p["week_end"]
    applied = p["applied"]
    progressed = p["progressed"]
    offers = p["offers"]
    ghosted = p["ghosted"]
    interviews: list[dict] = p["interviews"]
    nudges: list[str] = p["nudges"]
    streak = p["streak"]
    xp = p["xp"]
    level = p["level"]
    dsa_solved = p["dsa_solved"]
    dsa_hard = p["dsa_hard"]
    frontend_url = settings.frontend_url

    # ── Response rate pill ────────────────────────────────────────────
    if applied > 0:
        rate = round((progressed / applied) * 100)
        rate_color = "#16a34a" if rate >= 20 else "#d97706" if rate >= 10 else "#94a3b8"
        response_rate_html = f"""
        <p style="margin:14px 0 0;font-size:12px;color:#64748b;text-align:right">
          Response rate this week:&nbsp;
          <strong style="color:{rate_color}">{rate}%</strong>
        </p>"""
    else:
        response_rate_html = ""

    # ── Upcoming interviews block ──────────────────────────────────────
    STATUS_COLORS = {
        "Screening":    ("#dbeafe", "#2563eb"),
        "Phone Screen": ("#dbeafe", "#2563eb"),
        "Interview":    ("#ede9fe", "#7c3aed"),
        "Technical":    ("#fef3c7", "#d97706"),
        "HR":           ("#dcfce7", "#16a34a"),
    }
    if interviews:
        rows = []
        for iv in interviews:
            bg, fg = STATUS_COLORS.get(iv["status"], ("#f1f5f9", "#475569"))
            rows.append(f"""
            <tr>
              <td style="padding:10px 0;border-bottom:1px solid #f1f5f9">
                <table width="100%" cellpadding="0" cellspacing="0">
                  <tr>
                    <td>
                      <div style="font-size:13px;font-weight:600;color:#0f172a">{iv['company']}</div>
                      <div style="font-size:12px;color:#64748b;margin-top:2px">{iv['role']}</div>
                    </td>
                    <td align="right">
                      <span style="display:inline-block;background:{bg};color:{fg};font-size:10px;font-weight:700;padding:3px 10px;border-radius:20px;text-transform:uppercase;letter-spacing:0.04em">{iv['status']}</span>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>""")
        # Remove last border
        interviews_inner = f"""
        <table width="100%" cellpadding="0" cellspacing="0">
          {"".join(rows)}
        </table>
        <p style="margin:12px 0 0;font-size:11px;color:#94a3b8">
          {len(interviews)} active interview{'' if len(interviews)==1 else 's'} in your pipeline
        </p>"""
    else:
        interviews_inner = """
        <p style="font-size:13px;color:#94a3b8;margin:0;text-align:center;padding:8px 0">
          No active interviews right now — keep applying! 💪
        </p>"""

    # ── Nudges / follow-ups block ──────────────────────────────────────
    if nudges:
        items = "".join(
            f"""<tr>
              <td style="padding:8px 0;border-bottom:1px solid #fef9c3">
                <table width="100%" cellpadding="0" cellspacing="0">
                  <tr>
                    <td width="20" style="vertical-align:top;padding-top:1px">
                      <span style="font-size:14px">⚡</span>
                    </td>
                    <td style="padding-left:8px;font-size:13px;color:#92400e;line-height:1.5">{html.escape(n)}</td>
                  </tr>
                </table>
              </td>
            </tr>"""
            for n in nudges
        )
        nudges_inner = f'<table width="100%" cellpadding="0" cellspacing="0">{items}</table>'
    else:
        nudges_inner = """
        <p style="font-size:13px;color:#65a30d;margin:0;text-align:center;padding:8px 0">
          ✅&nbsp; You're all caught up — no follow-ups pending!
        </p>"""

    # ── DSA label ─────────────────────────────────────────────────────
    dsa_label = f"{dsa_solved} solved"
    if dsa_hard:
        dsa_label += f" · {dsa_hard} hard"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Your JobPilot Week in Review</title>
</head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">

<table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:40px 16px;">
<tr><td align="center">

  <!-- ── MAIN CARD ─────────────────────────────────────────── -->
  <table width="600" cellpadding="0" cellspacing="0"
         style="background:#ffffff;border-radius:20px;border:1px solid #e2e8f0;overflow:hidden;max-width:600px;width:100%;box-shadow:0 4px 32px rgba(15,23,42,0.07);">

    <!-- HEADER -->
    <tr>
      <td style="background:linear-gradient(135deg,#4f46e5 0%,#7c3aed 100%);padding:40px 40px 36px;text-align:center;">
        <div style="display:inline-block;background:rgba(255,255,255,0.18);border-radius:16px;padding:12px 16px;margin-bottom:18px;">
          <span style="font-size:24px;line-height:1;">✈️</span>
        </div>
        <h1 style="color:#ffffff;font-size:26px;font-weight:800;margin:0 0 8px;letter-spacing:-0.02em;">JobPilot</h1>
        <p style="color:#c7d2fe;font-size:13px;margin:0;font-weight:500;letter-spacing:0.02em;">
          Week in Review &nbsp;·&nbsp; {week_start} – {week_end}
        </p>
      </td>
    </tr>

    <!-- GREETING -->
    <tr>
      <td style="padding:32px 40px 0;">
        <h2 style="font-size:19px;color:#0f172a;margin:0 0 6px;font-weight:700;">
          Hey {name}! 👋
        </h2>
        <p style="font-size:14px;color:#64748b;margin:0;line-height:1.65;">
          Here's your job search snapshot for the week. Stay consistent — every application brings you closer.
        </p>
      </td>
    </tr>

    <!-- DIVIDER -->
    <tr><td style="padding:24px 40px 0;"><div style="height:1px;background:#f1f5f9;"></div></td></tr>

    <!-- ── SECTION 1: Applications This Week ────────────────── -->
    <tr>
      <td style="padding:24px 40px 0;">
        <p style="font-size:11px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#6366f1;margin:0 0 16px;">
          📊 &nbsp;Applications This Week
        </p>

        <table width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <!-- Applied -->
            <td width="25%" style="padding:0 5px 0 0;">
              <div style="background:#fafafa;border:1.5px solid #e2e8f0;border-top:3px solid #6366f1;border-radius:12px;padding:16px 10px;text-align:center;">
                <div style="font-size:32px;font-weight:800;color:#4f46e5;line-height:1;">{applied}</div>
                <div style="font-size:10px;color:#94a3b8;margin-top:6px;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;">Applied</div>
              </div>
            </td>
            <!-- Progressed -->
            <td width="25%" style="padding:0 5px;">
              <div style="background:#fffbeb;border:1.5px solid #fde68a;border-top:3px solid #f59e0b;border-radius:12px;padding:16px 10px;text-align:center;">
                <div style="font-size:32px;font-weight:800;color:#d97706;line-height:1;">{progressed}</div>
                <div style="font-size:10px;color:#94a3b8;margin-top:6px;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;">Moved Up</div>
              </div>
            </td>
            <!-- Offers -->
            <td width="25%" style="padding:0 5px;">
              <div style="background:#f0fdf4;border:1.5px solid #bbf7d0;border-top:3px solid #22c55e;border-radius:12px;padding:16px 10px;text-align:center;">
                <div style="font-size:32px;font-weight:800;color:#16a34a;line-height:1;">{offers}</div>
                <div style="font-size:10px;color:#94a3b8;margin-top:6px;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;">Offers</div>
              </div>
            </td>
            <!-- Ghosted -->
            <td width="25%" style="padding:0 0 0 5px;">
              <div style="background:#fafafa;border:1.5px solid #e2e8f0;border-top:3px solid #cbd5e1;border-radius:12px;padding:16px 10px;text-align:center;">
                <div style="font-size:32px;font-weight:800;color:#cbd5e1;line-height:1;">{ghosted}</div>
                <div style="font-size:10px;color:#94a3b8;margin-top:6px;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;">Ghosted</div>
              </div>
            </td>
          </tr>
        </table>
        {response_rate_html}
      </td>
    </tr>

    <!-- ── SECTION 2: Upcoming Interviews ───────────────────── -->
    <tr>
      <td style="padding:28px 40px 0;">
        <p style="font-size:11px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#6366f1;margin:0 0 14px;">
          🎙️ &nbsp;Interviews in Pipeline
        </p>
        <div style="background:#f8fafc;border:1.5px solid #e2e8f0;border-radius:14px;padding:16px 20px;">
          {interviews_inner}
        </div>
      </td>
    </tr>

    <!-- ── SECTION 3: Follow-ups Due ─────────────────────────── -->
    <tr>
      <td style="padding:28px 40px 0;">
        <p style="font-size:11px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#6366f1;margin:0 0 14px;">
          📌 &nbsp;Follow-up Reminders
        </p>
        <div style="background:#fefce8;border:1.5px solid #fef08a;border-radius:14px;padding:16px 20px;">
          {nudges_inner}
        </div>
      </td>
    </tr>

    <!-- ── SECTION 4: Progress ───────────────────────────────── -->
    <tr>
      <td style="padding:28px 40px 0;">
        <p style="font-size:11px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#6366f1;margin:0 0 14px;">
          🎮 &nbsp;Your Progress
        </p>
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <!-- Streak -->
            <td width="33%" style="padding:0 5px 0 0;">
              <div style="background:#fff7ed;border:1.5px solid #fed7aa;border-radius:14px;padding:20px 12px;text-align:center;">
                <div style="font-size:26px;font-weight:800;color:#ea580c;line-height:1;">{streak}&nbsp;🔥</div>
                <div style="font-size:10px;color:#94a3b8;margin-top:8px;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;">Day Streak</div>
              </div>
            </td>
            <!-- Level + XP -->
            <td width="33%" style="padding:0 5px;">
              <div style="background:#f0fdf4;border:1.5px solid #bbf7d0;border-radius:14px;padding:20px 12px;text-align:center;">
                <div style="font-size:26px;font-weight:800;color:#16a34a;line-height:1;">Lv&nbsp;{level}</div>
                <div style="font-size:10px;color:#94a3b8;margin-top:8px;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;">{xp:,} XP</div>
              </div>
            </td>
            <!-- DSA -->
            <td width="33%" style="padding:0 0 0 5px;">
              <div style="background:#faf5ff;border:1.5px solid #e9d5ff;border-radius:14px;padding:20px 12px;text-align:center;">
                <div style="font-size:26px;font-weight:800;color:#7c3aed;line-height:1;">{dsa_solved}</div>
                <div style="font-size:10px;color:#94a3b8;margin-top:8px;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;">{dsa_label}</div>
              </div>
            </td>
          </tr>
        </table>
      </td>
    </tr>

    <!-- CTA BUTTON -->
    <tr>
      <td style="padding:36px 40px;text-align:center;">
        <a href="{frontend_url}/dashboard"
           style="display:inline-block;background:linear-gradient(135deg,#4f46e5 0%,#7c3aed 100%);color:#ffffff;font-size:14px;font-weight:700;padding:14px 36px;border-radius:12px;text-decoration:none;letter-spacing:0.01em;box-shadow:0 4px 14px rgba(99,102,241,0.35);">
          Open JobPilot &rarr;
        </a>
      </td>
    </tr>

    <!-- FOOTER -->
    <tr>
      <td style="background:#f8fafc;border-top:1px solid #e2e8f0;padding:20px 40px;text-align:center;">
        <p style="font-size:11px;color:#94a3b8;margin:0;line-height:1.9;">
          You're getting this weekly digest because you have a JobPilot account.<br>
          <a href="{frontend_url}/settings" style="color:#94a3b8;text-decoration:underline;">Manage email preferences</a>
          &nbsp;&middot;&nbsp;
          <a href="{frontend_url}/settings" style="color:#94a3b8;text-decoration:underline;">Unsubscribe</a>
        </p>
      </td>
    </tr>

  </table>
  <!-- end main card -->

  <p style="font-size:11px;color:#94a3b8;margin:20px 0 0;text-align:center;">
    JobPilot &middot; Your AI-powered job search co-pilot
  </p>

</td></tr>
</table>

</body>
</html>"""
