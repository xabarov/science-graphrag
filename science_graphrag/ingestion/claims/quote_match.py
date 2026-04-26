"""Normalize PDF-ish text and fuzzy-match quotes to chunk bodies (claims evidence gate)."""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

# Hyphen / minus-like characters → ASCII hyphen (PDF extraction noise).
_DASH_RE = re.compile(r"[\u2010\u2011\u2012\u2013\u2014\u2212]")
# Non-breaking and narrow spaces → regular space.
_NBSP_RE = re.compile(r"[\u00a0\u202f\u2007]")
# Insert space between a letter and a following digit (e.g. ``For300`` → ``For 300``).
_LETTER_DIGIT_BOUNDARY = re.compile(r"(?<=[A-Za-z])(?=\d)")


def normalize_text_for_llm(text: str) -> str:
    """NFKC + nbsp→space + unicode dashes→ASCII + ×→x + letter/digit boundary + collapse whitespace.

    Case is preserved (suitable for LLM input and stored quotes).
    """

    s = unicodedata.normalize("NFKC", str(text or ""))
    s = _NBSP_RE.sub(" ", s)
    s = _DASH_RE.sub("-", s)
    s = s.replace("\u00d7", "x")  # multiplication sign → ASCII x (dimensions)
    s = _LETTER_DIGIT_BOUNDARY.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_text_for_match(text: str) -> str:
    """Lowercased :func:`normalize_text_for_llm` for substring / fuzzy quote checks."""

    return normalize_text_for_llm(text).lower()


def find_fuzzy_substring(
    quote_norm: str,
    chunk_norm: str,
    *,
    min_ratio: float = 0.85,
) -> str | None:
    """Return a substring of ``chunk_norm`` when difflib finds a long enough common block.

    Uses :meth:`difflib.SequenceMatcher.find_longest_match` with ``autojunk=False``.
    Accepts when ``block.size >= min_ratio * len(quote_norm)``.
    """

    if len(quote_norm) < 8:
        return None
    matcher = SequenceMatcher(None, quote_norm, chunk_norm, autojunk=False)
    block = matcher.find_longest_match(0, len(quote_norm), 0, len(chunk_norm))
    if block.size == 0:
        return None
    need = int(min_ratio * len(quote_norm) + 1e-9)
    if block.size < need:
        return None
    return chunk_norm[block.b : block.b + block.size]
