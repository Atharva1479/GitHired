# backend/tests/unit/test_jooble_client.py
"""Unit tests for jooble_client normalise + ID extraction."""
from app.services.jooble_client import _extract_external_id, _normalise, _parse_dt


def test_extract_external_id_from_url():
    assert _extract_external_id("https://jooble.org/desc/-12345678") == "12345678"


def test_extract_external_id_fallback():
    result = _extract_external_id("https://jooble.org/other/link/abc123")
    assert len(result) > 0


def test_normalise_maps_fields():
    raw = {
        "title": "Java Developer",
        "company": "Infosys",
        "location": "Mumbai, India",
        "snippet": "5 years Java Spring Boot experience required.",
        "source": "naukri.com",
        "type": "Full-time",
        "link": "https://jooble.org/desc/-99887766",
        "updated": "2026-06-19T00:00:00.0000000",
    }
    result = _normalise(raw)
    assert result["title"] == "Java Developer"
    assert result["company"] == "Infosys"
    assert result["source"] == "jooble:naukri.com"
    assert result["external_id"] == "99887766"
    assert result["apply_url"] == raw["link"]
    assert result["posted_at"] is not None


def test_normalise_strips_html_from_snippet():
    raw = {
        "title": "Dev", "company": "Co", "location": "India",
        "snippet": "<p>Hello <b>World</b></p>",
        "source": "naukri.com", "type": "", "link": "https://jooble.org/desc/1",
        "updated": None,
    }
    result = _normalise(raw)
    assert "<" not in result["description"]
    assert "Hello" in result["description"]


def test_parse_dt_jooble_format():
    dt = _parse_dt("2026-06-19T10:30:00.0000000")
    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 6


def test_parse_dt_none_returns_none():
    assert _parse_dt(None) is None
