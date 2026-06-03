"""Transactional email helpers via Resend."""
from __future__ import annotations

import asyncio
from typing import Any

import structlog

from app.config import settings

log = structlog.get_logger("email_service")


async def send_job_alert_email(
    to_email: str,
    user_name: str,
    jobs: list[dict[str, Any]],
) -> None:
    """Send a daily job alert digest email via Resend.

    No-ops when RESEND_API_KEY is not configured.
    """
    api_key = settings.resend_api_key.get_secret_value()
    if not api_key:
        log.debug("email.skipped", reason="no resend key")
        return

    import resend  # type: ignore[import]
    resend.api_key = api_key

    job_html = "".join(
        f"""
        <div style="margin-bottom:16px;padding:16px;border:1px solid #e5e7eb;border-radius:8px;">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <strong style="font-size:15px;">{j['title']}</strong>
            <span style="font-size:12px;color:#10b981;font-weight:600;">{j['freshness_label']}</span>
          </div>
          <p style="margin:4px 0;color:#6b7280;">{j['company']} · {j.get('location') or 'Remote'}</p>
          <p style="margin:4px 0;font-size:13px;color:#9ca3af;">Est. applicants: {j['est_applicants']}</p>
          <a href="{j['apply_url']}" style="display:inline-block;margin-top:8px;padding:6px 16px;background:#4f46e5;color:white;border-radius:6px;text-decoration:none;font-size:13px;">Apply Now</a>
        </div>
        """
        for j in jobs
    )

    html_body = f"""
    <div style="font-family:Inter,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
      <h2 style="color:#111827;">Hi {user_name}, {len(jobs)} fresh job{'s' if len(jobs) != 1 else ''} matched your alerts today 🔥</h2>
      <p style="color:#6b7280;">These are recent postings — apply fast for the best shortlisting chances.</p>
      {job_html}
      <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
      <p style="font-size:12px;color:#9ca3af;">GitHired · <a href="http://localhost:3000/jobs">View all jobs</a></p>
    </div>
    """

    await asyncio.to_thread(
        resend.Emails.send,
        {
            "from": "GitHired <alerts@githired.app>",
            "to": [to_email],
            "subject": f"🔥 {len(jobs)} fresh job matches for you today",
            "html": html_body,
        },
    )
