"""Regression tests for Gemini error classification.

The error text from google-generativeai is huge and nondeterministic;
the user must never see it. These tests pin the classifier's behaviour
for the shapes we know about.
"""
from __future__ import annotations

import google.api_core.exceptions as gx

from app.services.pilot_agent import (
    _classify_gemini_error,
    _parse_retry_delay_seconds,
)


def test_quota_with_retry_delay_returns_clean_reply() -> None:
    msg = (
        "429 You exceeded your current quota, please check your plan and "
        "billing details. Quota exceeded for metric "
        "generativelanguage.googleapis.com/generate_content_free_tier_requests."
        " Please retry in 32.349924605s. retry_delay { seconds: 32 }"
    )
    exc = gx.ResourceExhausted(msg)
    outcome, reply = _classify_gemini_error(exc)
    assert outcome == "quota_exhausted"
    # User-facing must not contain raw exception bits.
    assert "google" not in reply.lower()
    assert "metric" not in reply.lower()
    assert "429" not in reply
    # But MUST tell the user a concrete wait time.
    assert "32 seconds" in reply or "32 second" in reply


def test_parse_retry_delay_seconds_from_string() -> None:
    exc = gx.ResourceExhausted("retry_delay { seconds: 45 }")
    assert _parse_retry_delay_seconds(exc) == 45


def test_parse_retry_delay_returns_none_when_absent() -> None:
    exc = gx.ResourceExhausted("no delay info here")
    assert _parse_retry_delay_seconds(exc) is None


def test_parse_retry_delay_ignores_absurd_values() -> None:
    # > 1 day — clearly not a real retry delay; we'd never wait that long.
    exc = gx.ResourceExhausted("retry_delay { seconds: 9999999 }")
    assert _parse_retry_delay_seconds(exc) is None


def test_quota_without_retry_delay_falls_back_to_generic_hint() -> None:
    exc = gx.ResourceExhausted("You exceeded your current quota")
    outcome, reply = _classify_gemini_error(exc)
    assert outcome == "quota_exhausted"
    assert "billing" in reply.lower() or "hour" in reply.lower()


def test_long_retry_delay_calls_out_daily_cap() -> None:
    """A retry_delay > 5 minutes is almost always the daily free-tier cap."""
    exc = gx.ResourceExhausted("retry_delay { seconds: 3600 }")
    outcome, reply = _classify_gemini_error(exc)
    assert outcome == "quota_exhausted"
    assert "daily" in reply.lower()


def test_short_retry_delay_suggests_lite_model() -> None:
    """A short retry_delay on a quota error means the per-minute cap;
    the most useful hint is to switch model."""
    exc = gx.ResourceExhausted("retry_delay { seconds: 30 }")
    outcome, reply = _classify_gemini_error(exc)
    assert outcome == "quota_exhausted"
    assert "lite" in reply.lower() or "paid" in reply.lower()


def test_auth_error_classified() -> None:
    exc = gx.PermissionDenied("403 The caller does not have permission")
    outcome, reply = _classify_gemini_error(exc)
    assert outcome == "auth_error"
    assert "api key" in reply.lower() or "credentials" in reply.lower()


def test_unavailable_classified() -> None:
    exc = gx.ServiceUnavailable("503 backend unavailable")
    outcome, reply = _classify_gemini_error(exc)
    assert outcome == "upstream_unavailable"


def test_unknown_error_falls_back_to_generic() -> None:
    exc = RuntimeError("something totally unexpected")
    outcome, reply = _classify_gemini_error(exc)
    assert outcome == "error"
    # Must still be a clean human sentence — no traceback bits.
    assert "Traceback" not in reply
    assert "RuntimeError" not in reply
