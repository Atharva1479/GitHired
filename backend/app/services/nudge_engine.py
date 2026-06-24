from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

import asyncpg

from app.models import ApplicationOut, ApplicationStatus, ReferralOut
from app.repositories import applications as apps_repo
from app.repositories import nudges as nudges_repo
from app.repositories import referrals as refs_repo


@dataclass(frozen=True)
class NudgeCandidate:
    type: str
    reference_type: str
    reference_id: int | None
    severity: str
    message: str


def evaluate_application_rules(
    app: ApplicationOut, today: date
) -> Iterable[NudgeCandidate]:
    days_since_applied = (today - app.applied_date).days
    days_since_update = (today - app.last_updated.date()).days

    # R1
    if app.status == ApplicationStatus.applied and days_since_applied >= 7 and app.follow_up_count == 0:
        yield NudgeCandidate(
            type="application_followup",
            reference_type="application",
            reference_id=app.id,
            severity="due",
            message=(
                f"Follow up with {app.company} for {app.role} â€” "
                f"{days_since_applied} days, no response."
            ),
        )

    # R2
    if app.status == ApplicationStatus.applied and days_since_applied >= 14:
        yield NudgeCandidate(
            type="application_stale",
            reference_type="application",
            reference_id=app.id,
            severity="overdue",
            message=(
                f"Consider marking {app.company} as Ghosted â€” "
                f"{days_since_applied} days without movement."
            ),
        )

    # R3
    if app.status in (ApplicationStatus.screening, ApplicationStatus.interview) and days_since_update >= 5:
        yield NudgeCandidate(
            type="application_interview_stale",
            reference_type="application",
            reference_id=app.id,
            severity="due",
            message=(
                f"No update from {app.company} in {days_since_update} days. "
                "Follow up?"
            ),
        )


def evaluate_referral_rules(
    ref: ReferralOut, today: date
) -> Iterable[NudgeCandidate]:
    days_since_sent = (today - ref.connection_sent_date).days
    days_since_update = (today - ref.last_updated.date()).days

    # R5
    if ref.connection_status == "Request Sent" and days_since_sent >= 3:
        yield NudgeCandidate(
            type="referral_check",
            reference_type="referral",
            reference_id=ref.id,
            severity="due",
            message=(
                f"{ref.name} at {ref.company} likely accepted your invite. "
                "Send the referral message."
            ),
        )

    # R6
    if ref.connection_status == "Request Sent" and days_since_sent >= 7:
        yield NudgeCandidate(
            type="referral_unaccepted",
            reference_type="referral",
            reference_id=ref.id,
            severity="info",
            message=(
                f"{ref.name} hasn't accepted in {days_since_sent} days. "
                "Try an alternate contact or move on."
            ),
        )

    # R7
    if ref.connection_status == "Accepted" and days_since_update >= 2:
        yield NudgeCandidate(
            type="referral_ask",
            reference_type="referral",
            reference_id=ref.id,
            severity="due",
            message=(
                f"You haven't messaged {ref.name} at {ref.company} yet. "
                "Send the ask."
            ),
        )

    # R8
    if (
        ref.connection_status == "Msg Sent"
        and ref.referral_msg_sent_date is not None
        and (today - ref.referral_msg_sent_date).days >= 5
    ):
        days_since_msg = (today - ref.referral_msg_sent_date).days
        yield NudgeCandidate(
            type="referral_followup",
            reference_type="referral",
            reference_id=ref.id,
            severity="due",
            message=(
                f"No reply from {ref.name} at {ref.company} "
                f"in {days_since_msg} days. Send a gentle follow-up."
            ),
        )


def evaluate_weekly_volume(weekly_count: int) -> Iterable[NudgeCandidate]:
    # R4
    if weekly_count < 5:
        yield NudgeCandidate(
            type="apply_more",
            reference_type="user",
            reference_id=None,
            severity="info",
            message=(
                f"You've applied to {weekly_count} role"
                f"{'s' if weekly_count != 1 else ''} this week. Aim for 5+."
            ),
        )


async def run_all_checks(
    conn: asyncpg.Connection, user_id: int, today: date
) -> int:
    apps = await apps_repo.list_applications(conn, user_id)
    refs = await refs_repo.list_referrals(conn, user_id)
    weekly_count = await apps_repo.count_created_within(conn, user_id, days=7)

    candidates: list[NudgeCandidate] = []
    for app in apps:
        candidates.extend(evaluate_application_rules(app, today))
    for ref in refs:
        candidates.extend(evaluate_referral_rules(ref, today))
    candidates.extend(evaluate_weekly_volume(weekly_count))

    batch = [
        (c.type, c.reference_type, c.reference_id, c.severity, c.message)
        for c in candidates
    ]
    return await nudges_repo.insert_many(conn, user_id, batch, today)

