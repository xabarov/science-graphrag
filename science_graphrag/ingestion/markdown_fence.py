"""Strip whole-document markdown code fences from extractor output.

VL models often wrap the full document in `` ```markdown ... ``` ``. That must not
reach ``normalized.md`` or chunking unchanged. Logic mirrors the frontend
``unwrapOuterMarkdownCodeFence`` contract: only unwrap when the first non-empty
line is an opening fence and the last non-empty line is exactly `` ``` ``.
"""

from __future__ import annotations

import re

_OPENING_FENCE_RE = re.compile(r"^```[\w+-]*\s*$")


def strip_whole_document_markdown_fence(source: str) -> str:
    """If ``source`` is one fenced markdown document, return inner body; else unchanged.

    Conservative: does not strip partial fences or inner code blocks.
    """
    if source is None or not isinstance(source, str):
        return ""
    normalized = source.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    start = 0
    end = len(lines) - 1
    while start < len(lines) and lines[start].strip() == "":
        start += 1
    while end >= start and lines[end].strip() == "":
        end -= 1
    if end <= start:
        return source
    first = lines[start].strip().replace("\ufeff", "")
    last = lines[end].strip()
    if not _OPENING_FENCE_RE.match(first) or last != "```":
        return source
    inner = "\n".join(lines[start + 1 : end])
    return inner if inner else source
