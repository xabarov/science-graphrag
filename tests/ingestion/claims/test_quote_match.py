"""Unit tests for ``quote_match`` normalization and fuzzy substring finder."""

from science_graphrag.ingestion.claims.quote_match import (
    find_fuzzy_substring,
    normalize_text_for_llm,
    normalize_text_for_match,
)


def test_normalize_handles_nbsp_and_collapsed_spaces() -> None:
    """NBSP and runs of whitespace collapse to single ASCII spaces."""
    raw = "foo\u00a0bar   baz\n\nqux"
    assert normalize_text_for_llm(raw) == "foo bar baz qux"


def test_normalize_unicode_dashes_to_ascii() -> None:
    """Unicode hyphen/minus characters map to ASCII ``-``."""
    raw = "a\u2013b\u2014c\u2212d"
    assert normalize_text_for_llm(raw) == "a-b-c-d"


def test_normalize_idempotent() -> None:
    """Second normalization pass is a no-op."""
    x = "  For300\u00d7 300  in-\nput  "
    once = normalize_text_for_llm(x)
    twice = normalize_text_for_llm(once)
    assert once == twice


def test_normalize_text_for_match_is_lower() -> None:
    """Match-normalization lowercases output."""
    assert normalize_text_for_match("SSD Achieves") == "ssd achieves"


def test_find_fuzzy_substring_real_pdf_artifact_for300() -> None:
    """Fuzzy block ≥85% of quote; model spacing vs PDF ``For300×`` glue after normalization."""
    chunk = normalize_text_for_match("For300× 300 input, SSD achieves 74.3%")
    quote = normalize_text_for_match("For 300x300 input, SSD achieves 74.3%")
    span = find_fuzzy_substring(quote, chunk, min_ratio=0.85)
    assert span is not None
    assert len(span) >= int(0.85 * len(quote))


def test_find_fuzzy_substring_returns_none_below_threshold() -> None:
    """Disjoint strings yield no long enough common block."""
    quote = normalize_text_for_match("x" * 80)
    chunk = normalize_text_for_match("y" * 80)
    assert find_fuzzy_substring(quote, chunk, min_ratio=0.85) is None
