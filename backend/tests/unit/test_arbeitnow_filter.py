from app.services.arbeitnow_client import _title_matches


def test_matching_keyword_passes():
    assert _title_matches("Java Backend Developer", "Java Spring Boot") is True


def test_unrelated_title_filtered():
    assert _title_matches("Office Assistant", "Java Spring Boot") is False


def test_short_query_passes_all():
    # query "Go" has only 2 chars — don't filter
    assert _title_matches("Office Assistant", "Go") is True


def test_partial_keyword_match():
    assert _title_matches("Spring Cloud Developer", "Java Spring Boot") is True
