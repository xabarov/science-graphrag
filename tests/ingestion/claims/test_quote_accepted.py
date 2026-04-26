"""Tests for ``_quote_accepted`` multi-level quote gate."""

import random

from science_graphrag.ingestion.claims.extractor import _quote_accepted
from science_graphrag.ingestion.claims.quote_match import normalize_text_for_llm


def test_strict_passes_clean_quote() -> None:
    """Verbatim substring passes the legacy strict path."""
    chunk = "The cat sat on the mat."
    quote = "The cat sat"
    ok, mode = _quote_accepted(quote, chunk)
    assert ok is True
    assert mode == "strict"


def test_strict_normalized_handles_for300_artifact() -> None:
    """PDF-style ``For300×`` vs model ``For 300x300`` after shared normalization in chunk."""
    chunk = normalize_chunk_for_test("For300× 300 input, SSD achieves 74.3%")
    quote = "For 300x300 input, SSD achieves 74.3%"
    ok, mode = _quote_accepted(quote, chunk)
    assert ok is True
    assert mode == "strict_normalized"


def test_fuzzy_normalized_handles_minor_paraphrase() -> None:
    """Contiguous block ≥85% of quote length but quote not a substring of chunk."""
    quote = "a" * 90 + "bbbbbb"
    chunk = "a" * 90 + "cccccc"
    ok, mode = _quote_accepted(quote, chunk)
    assert ok is True
    assert mode == "fuzzy_normalized"


def test_jaccard_still_catches_word_level_paraphrase() -> None:
    """Same token multiset as chunk prefix, permuted so ``quote`` is not a contiguous substring."""
    words_w = [f"w{i}" for i in range(18)]
    chunk = " ".join(words_w) + " " + " ".join(f"g{i}" for i in range(7))
    shuffled = words_w[:]
    random.Random(0).shuffle(shuffled)
    quote = " ".join(shuffled)
    assert quote.lower() not in chunk.lower()
    ok, mode = _quote_accepted(quote, chunk)
    assert ok is True
    assert mode == "jaccard"


def test_too_short_quote_rejected() -> None:
    """Quotes shorter than 8 characters are rejected in all modes."""
    ok, mode = _quote_accepted("short", "some longer chunk text here")
    assert ok is False
    assert mode == "none"


def normalize_chunk_for_test(s: str) -> str:
    """Same normalization as ``extract_claims_llm`` applies to chunk bodies."""
    return normalize_text_for_llm(s)
