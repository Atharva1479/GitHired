from datetime import date, datetime, timedelta, timezone
from typing import Any

import pytest

from app.models import ApplicationOut, ReferralOut
from app.services.nudge_engine import (
    evaluate_application_rules,
    evaluate_referral_rules,
    evaluate_weekly_volume,
)

TODAY = date(2026, 5, 15)


def _app(**over: Any) -> ApplicationOut:
    base = dict(
        id=1, company="X", role="Eng", source="LinkedIn", status="Applied",
        applied_date=TODAY,
        last_updated=datetime(2026, 5, 15, tzinfo=timezone.utc),
        jd_url=None, salary_discussed=None, contact_name=None, contact_linkedin=None,
        fit_score=None, notes=None, follow_up_count=0, last_followed_up_at=None,
        created_at=datetime(2026, 5, 15, tzinfo=timezone.utc),
        jd_text=None, jd_file_name=None, resume_file_name=None,
        cover_letter_file_name=None,
    )
    base.update(over)
    return ApplicationOut.model_validate(base)


def _ref(**over: Any) -> ReferralOut:
    base = dict(
        id=1, name="N", company="X", target_role="Eng",
        role_at_company=None, linkedin_url=None, mutual_context=None,
        connection_sent_date=TODAY,
        connection_status="Request Sent",
        referral_msg_sent_date=None, reply_date=None, outcome=None, notes=None,
        last_updated=datetime(2026, 5, 15, tzinfo=timezone.utc),
        created_at=datetime(2026, 5, 15, tzinfo=timezone.utc),
    )
    base.update(over)
    return ReferralOut.model_validate(base)


def _types(it):
    return [c.type for c in it]


# ---- R1: application_followup (7d, 0 follow-ups) ----------------------------
@pytest.mark.parametrize("days,fc,expected", [
    (6, 0, False),
    (7, 0, True),
    (8, 0, True),
    (7, 1, False),   # already followed up
])
def test_r1_application_followup(days, fc, expected):
    app = _app(applied_date=TODAY - timedelta(days=days), follow_up_count=fc)
    has = "application_followup" in _types(evaluate_application_rules(app, TODAY))
    assert has is expected


# ---- R2: application_stale (14d) -------------------------------------------
@pytest.mark.parametrize("days,expected", [
    (13, False),
    (14, True),
    (20, True),
])
def test_r2_application_stale(days, expected):
    app = _app(applied_date=TODAY - timedelta(days=days))
    has = "application_stale" in _types(evaluate_application_rules(app, TODAY))
    assert has is expected


def test_r2_does_not_fire_for_terminal_status():
    app = _app(
        status="Rejected", applied_date=TODAY - timedelta(days=30),
    )
    assert "application_stale" not in _types(evaluate_application_rules(app, TODAY))


# ---- R3: application_interview_stale (5d since last_updated) ---------------
@pytest.mark.parametrize("status,days,expected", [
    ("Screening", 4, False),
    ("Screening", 5, True),
    ("Interview", 6, True),
    ("Applied", 10, False),
    ("Offer", 10, False),
])
def test_r3_interview_stale(status, days, expected):
    app = _app(
        status=status,
        last_updated=datetime.combine(TODAY - timedelta(days=days), datetime.min.time(), tzinfo=timezone.utc),
    )
    has = "application_interview_stale" in _types(evaluate_application_rules(app, TODAY))
    assert has is expected


# ---- R4: apply_more (< 5 in last 7 days) -----------------------------------
@pytest.mark.parametrize("n,expected", [(0, True), (4, True), (5, False), (10, False)])
def test_r4_apply_more(n, expected):
    has = bool(list(evaluate_weekly_volume(n)))
    assert has is expected


# ---- R5: referral_check (3d after request, Request Sent) -------------------
@pytest.mark.parametrize("days,status,expected", [
    (2, "Request Sent", False),
    (3, "Request Sent", True),
    (5, "Request Sent", True),
    (3, "Accepted", False),
])
def test_r5_referral_check(days, status, expected):
    ref = _ref(
        connection_sent_date=TODAY - timedelta(days=days),
        connection_status=status,
    )
    has = "referral_check" in _types(evaluate_referral_rules(ref, TODAY))
    assert has is expected


# ---- R6: referral_unaccepted (7d, still Request Sent) ----------------------
@pytest.mark.parametrize("days,expected", [(6, False), (7, True), (10, True)])
def test_r6_referral_unaccepted(days, expected):
    ref = _ref(connection_sent_date=TODAY - timedelta(days=days))
    has = "referral_unaccepted" in _types(evaluate_referral_rules(ref, TODAY))
    assert has is expected


# ---- R7: referral_ask (Accepted, 2d since update) --------------------------
@pytest.mark.parametrize("status,days,expected", [
    ("Accepted", 1, False),
    ("Accepted", 2, True),
    ("Request Sent", 2, False),
])
def test_r7_referral_ask(status, days, expected):
    ref = _ref(
        connection_status=status,
        last_updated=datetime.combine(TODAY - timedelta(days=days), datetime.min.time(), tzinfo=timezone.utc),
    )
    has = "referral_ask" in _types(evaluate_referral_rules(ref, TODAY))
    assert has is expected


# ---- R8: referral_followup (Msg Sent, 5d since msg date) -------------------
@pytest.mark.parametrize("days,expected", [(4, False), (5, True), (10, True)])
def test_r8_referral_followup(days, expected):
    ref = _ref(
        connection_status="Msg Sent",
        referral_msg_sent_date=TODAY - timedelta(days=days),
    )
    has = "referral_followup" in _types(evaluate_referral_rules(ref, TODAY))
    assert has is expected


def test_r8_skips_when_no_msg_date():
    ref = _ref(connection_status="Msg Sent", referral_msg_sent_date=None)
    assert "referral_followup" not in _types(evaluate_referral_rules(ref, TODAY))
