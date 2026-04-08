from __future__ import annotations

import re

_CANONICAL_ARXIV_RE = re.compile(r"\b(\d{4})\.(\d{4,5})(?:v\d+)?\b", re.IGNORECASE)
_COMPACT_ARXIV_RE = re.compile(r"\b(\d{4})(\d{4,5})(?:v\d+)?\b", re.IGNORECASE)
_RAW_ARXIV_RE = re.compile(
    r"(?:arxiv:\s*|abs/|corr,\s*abs/)(\d{4})(?:[.\s]?)(\d{4,5})(?:v\d+)?\b",
    re.IGNORECASE,
)


def _is_valid_modern_arxiv(prefix: str, suffix: str) -> bool:
    try:
        yymm = int(prefix)
        month = int(prefix[2:])
    except ValueError:
        return False
    if month < 1 or month > 12:
        return False
    if yymm >= 1501:
        return len(suffix) == 5
    return len(suffix) in (4, 5)


def normalize_arxiv_id(raw: str | None) -> str | None:
    if not raw:
        return None
    text = str(raw).strip()
    if not text:
        return None

    match = _CANONICAL_ARXIV_RE.search(text)
    if match:
        prefix, suffix = match.groups()
        if _is_valid_modern_arxiv(prefix, suffix):
            return f"{prefix}.{suffix}"
        return None

    compact_match = _COMPACT_ARXIV_RE.search(text)
    if compact_match:
        prefix, suffix = compact_match.groups()
        if _is_valid_modern_arxiv(prefix, suffix):
            return f"{prefix}.{suffix}"

    return None


def extract_arxiv_id_from_text(raw: str) -> str | None:
    match = _RAW_ARXIV_RE.search(raw)
    if match:
        prefix, suffix = match.groups()
        if _is_valid_modern_arxiv(prefix, suffix):
            return f"{prefix}.{suffix}"
        return None
    return normalize_arxiv_id(raw)
