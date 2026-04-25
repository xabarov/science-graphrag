"""Prompt contracts for semantic method/dataset extraction."""

from __future__ import annotations

import hashlib
import re

_SEM_REF_HEAD_RE = re.compile(
    r"^#{0,3}\s*(references|bibliography)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

MAX_SEMANTIC_BODY_CHARS = 12_000
MAX_SEMANTIC_BODY_CHARS_RETRY = 6_000
MAX_SEMANTIC_BODY_CHARS_MICRO = 4_000
MAX_SEMANTIC_BODY_CHARS_NANO = 2_500

SYSTEM_SEMANTIC = (
    "Extract methods and datasets for this paper only. Output must stay small enough to "
    "serialize as one JSON tool call (no repetition, no huge lists). "
    "Hard caps: **at most 4 methods** and **at most 5 datasets**. "
    "Prefer the paper's own method names. Do not add baseline methods unless the paper "
    "claims them as contributions. Evidence.quote should be <=120 chars."
)

SYSTEM_SEMANTIC_COMPACT = (
    "Extract methods and datasets for this paper only. "
    "At most 4 methods and 5 datasets. Keep JSON compact and omit long prose."
)


def semantic_prompt_fingerprint() -> str:
    """Stable hash of semantic prompt contract."""

    material = "|".join(
        (
            SYSTEM_SEMANTIC,
            SYSTEM_SEMANTIC_COMPACT,
            f"MAX_SEMANTIC_BODY_CHARS={MAX_SEMANTIC_BODY_CHARS}",
            f"MAX_SEMANTIC_BODY_CHARS_MICRO={MAX_SEMANTIC_BODY_CHARS_MICRO}",
            f"MAX_SEMANTIC_BODY_CHARS_NANO={MAX_SEMANTIC_BODY_CHARS_NANO}",
            "bundle_schema=v1",
        ),
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]
    return f"sha256-20:{digest}"


def truncate_text(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + "\n\n[... truncated ...]"


def semantic_body_slice(normalized_markdown: str, *, max_chars: int | None = None) -> str:
    """Main text without bibliography section when delimited."""

    cap = max_chars if max_chars is not None else MAX_SEMANTIC_BODY_CHARS
    match = _SEM_REF_HEAD_RE.search(normalized_markdown)
    body = normalized_markdown[: match.start()] if match else normalized_markdown
    return truncate_text(body.strip(), cap)
