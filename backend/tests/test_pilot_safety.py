"""Crisis-language detection unit tests.

The detector runs on every user message — false positives interrupt the
job-hunt flow and false negatives let a real crisis slip through. Both
matter, so we test both directions explicitly.
"""
from __future__ import annotations

from app.services.pilot_safety import check_message


# ── must trigger ─────────────────────────────────────────────────────


def test_explicit_suicidal_ideation_triggers() -> None:
    d = check_message("I want to kill myself.")
    assert d.triggered
    assert d.matched_pattern is not None


def test_self_harm_phrasing_triggers() -> None:
    d = check_message("I keep thinking about self harm.")
    assert d.triggered


def test_dont_want_to_live_triggers() -> None:
    d = check_message("I just don't want to live anymore.")
    assert d.triggered


def test_end_it_all_triggers() -> None:
    d = check_message("Honestly I just want to end it all.")
    assert d.triggered


def test_suicidal_word_triggers() -> None:
    d = check_message("I'm having suicidal thoughts after this rejection.")
    assert d.triggered


# ── must NOT trigger (job-hunt false friends) ───────────────────────


def test_kill_it_interview_does_not_trigger() -> None:
    """Common job-hunt idiom — must stay quiet."""
    d = check_message("I'm going to kill it on the Stripe interview tomorrow.")
    assert not d.triggered


def test_dead_market_does_not_trigger() -> None:
    d = check_message("The market for junior devs feels dead right now.")
    assert not d.triggered


def test_rejection_pain_does_not_trigger() -> None:
    d = check_message("Got rejected from Anthropic, it hurts.")
    assert not d.triggered


def test_burnout_does_not_trigger() -> None:
    d = check_message("I'm burned out from applying.")
    assert not d.triggered


def test_empty_message_does_not_trigger() -> None:
    assert not check_message("").triggered
    assert not check_message("   ").triggered


# ── preamble shape ──────────────────────────────────────────────────


def test_preamble_only_when_triggered() -> None:
    assert check_message("hello").preamble() == ""
    assert "CRISIS OVERRIDE" in check_message("I want to die").preamble()


def test_preamble_points_to_real_resource() -> None:
    """The hardcoded helpline reference must always be present so the
    model can't accidentally hallucinate a different number."""
    preamble = check_message("I want to kill myself").preamble()
    assert "988" in preamble
    assert "findahelpline" in preamble
