"""Tests for exact-key query cache helpers."""
from app.services.job_search import _cache_key


def test_cache_key_normalises_case():
    k1 = _cache_key("Java", "India", False, None)
    k2 = _cache_key("java", "india", False, None)
    assert k1 == k2


def test_cache_key_differentiates_remote():
    k1 = _cache_key("Java", "India", False, None)
    k2 = _cache_key("Java", "India", True, None)
    assert k1 != k2


def test_cache_key_differentiates_experience():
    k1 = _cache_key("Java", None, False, "senior")
    k2 = _cache_key("Java", None, False, "entry")
    assert k1 != k2


def test_cache_key_none_location_matches_empty():
    k1 = _cache_key("Java", None, False, None)
    k2 = _cache_key("Java", "", False, None)
    assert k1 == k2
