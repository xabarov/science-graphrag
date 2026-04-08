"""Task-aware text slices for scholarly Markdown after PDF→MD normalization."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

SliceType = Literal["front_matter", "references_scope", "full_document"]

# Introduction / body start markers (first occurrence wins if after min_chars)
_INTRO_MARKERS = (
    "\n## Introduction",
    "\n# Introduction",
    "\n1. Introduction",
    "\n1 Introduction",
    "\n1. INTRODUCTION",
    "\nI. Introduction",
    "\nINTRODUCTION",
)

_REF_HEAD_RE = re.compile(r"^#{0,3}\s*(references|bibliography)\s*$", re.IGNORECASE | re.MULTILINE)

# When no following ``##`` heading exists, avoid swallowing appendix/code tail (plan B1).
_REF_SECTION_EOF_STOP_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^#{1,6}\s+A[\.\s]", re.IGNORECASE),  # # A. Appendix, ## A Appendix
    re.compile(r"^#{1,6}\s+Appendix\b", re.IGNORECASE),
    re.compile(r"^Appendix\b", re.IGNORECASE),
    re.compile(r"^A\s+Appendix\b", re.IGNORECASE),
    re.compile(r"^A\.\s+Appendix\b", re.IGNORECASE),
    re.compile(r"^A\s+A\s+PPENDIX", re.IGNORECASE),  # OCR: "A A PPENDIX"
    re.compile(r"^A\.\d+\s+", re.IGNORECASE),  # e.g. "A.1 ..." appendix subsection
    re.compile(r"^```\s*$"),
    re.compile(r"^Listing\s+\d+", re.IGNORECASE),
)


def _reference_section_end_without_next_heading(
    rest: str, *, min_content_lines: int = 2
) -> int | None:
    """
    Return length of prefix of ``rest`` to use as the reference block, or None to use EOF.

    Stops before appendix headings, fenced code blocks, or ``Listing N`` lines once enough
    bibliography-like content was seen (avoids false positives right under ``## References``).
    """
    pos = 0
    content_lines = 0
    for i, line in enumerate(rest.split("\n")):
        if i > 0:
            pos += 1
        stripped = line.strip()
        if stripped:
            content_lines += 1
        if content_lines >= min_content_lines:
            for pat in _REF_SECTION_EOF_STOP_PATTERNS:
                if pat.match(stripped):
                    return pos
        pos += len(line)
    return None


@dataclass(frozen=True, slots=True)
class DocumentSlice:
    """A contiguous span of normalized markdown with provenance hints."""

    slice_type: SliceType
    text: str
    start_offset: int
    end_offset: int
    section_path: str | None = None
    source_page_hint: str | None = None


def strip_repeated_boilerplate(text: str) -> str:
    """
    Light cleanup: drop consecutive duplicate short lines (e.g. repeated page numbers)
    and trim runs of blank lines. Does not remove non-consecutive duplicates.
    """
    lines = text.split("\n")
    out: list[str] = []
    prev_stripped: str | None = None
    for ln in lines:
        s = ln.strip()
        if s == prev_stripped and len(s) <= 6 and s.isdigit():
            continue
        prev_stripped = s if s else prev_stripped
        out.append(ln)
    collapsed: list[str] = []
    blank_run = 0
    for ln in out:
        if not ln.strip():
            blank_run += 1
            if blank_run <= 2:
                collapsed.append(ln)
        else:
            blank_run = 0
            collapsed.append(ln)
    return "\n".join(collapsed).strip()


def front_matter_slice(
    text: str,
    *,
    max_chars: int = 12_000,
    min_intro_pos: int = 40,
) -> DocumentSlice:
    """
    Slice for metadata and authorships: title block, authors, abstract start,
    capped before Introduction when detected.
    """
    if not text:
        return DocumentSlice("front_matter", "", 0, 0, section_path="(empty)")

    scan = text[: min(len(text), max(max_chars * 2, max_chars))]
    end = min(max_chars, len(text))
    for marker in _INTRO_MARKERS:
        pos = scan.find(marker)
        if pos >= min_intro_pos:
            end = min(end, pos)
            break

    sliced = text[:end].strip()
    return DocumentSlice(
        "front_matter",
        sliced,
        start_offset=0,
        end_offset=min(end, len(text)),
        section_path="Front matter",
    )


def _truncate(s: str, max_len: int) -> str:
    if len(s) <= max_len:
        return s
    return s[:max_len] + "\n\n[... truncated for context limit ...]"


def find_reference_section_spans(text: str) -> list[tuple[int, int]]:
    """
    Return list of (start, end) offsets for reference-like regions.
    Each region starts after a References/Bibliography heading and runs to the next
    same-level or higher heading, or end of document.
    """
    spans: list[tuple[int, int]] = []
    for m in _REF_HEAD_RE.finditer(text):
        start = m.end()
        rest = text[start:]
        next_heading = re.search(r"^#{1,6}\s+\S", rest, flags=re.MULTILINE)
        if next_heading and next_heading.start() > 0:
            end = start + next_heading.start()
        else:
            early = _reference_section_end_without_next_heading(rest)
            end = start + early if early is not None else len(text)
        if end > start:
            spans.append((start, end))
    return spans


def build_references_scope_text(
    text: str,
    *,
    max_chars: int = 90_000,
) -> str:
    """
    Full references scope for LLM / heuristics: all Reference sections concatenated,
    or tail fallback if no heading found.

    Sections are bounded by ``find_reference_section_spans`` (including EOF appendix/code
    trims). When a scope-LLM excerpt is available in the pipeline, it may further cap
    overlong tails before parsing (see ingestion stage ordering).
    """
    spans = find_reference_section_spans(text)
    if spans:
        parts: list[str] = []
        for start, end in spans:
            parts.append(text[start:end].strip())
        combined = "\n\n".join(parts)
        return _truncate(combined, max_chars)

    return _truncate(text[-max_chars:] if len(text) > max_chars else text, max_chars)


def references_scope_slice(
    text: str,
    *,
    max_chars: int = 90_000,
) -> DocumentSlice:
    """Structured slice metadata for references scope (same text as build_references_scope_text)."""
    scope_text = build_references_scope_text(text, max_chars=max_chars)
    if not scope_text.strip():
        return DocumentSlice(
            "references_scope",
            "",
            0,
            0,
            section_path="References",
        )
    # Best-effort offsets: locate first occurrence of scope prefix in original
    prefix = scope_text[: min(200, len(scope_text))]
    idx = text.find(prefix) if prefix else -1
    if idx < 0:
        return DocumentSlice(
            "references_scope",
            scope_text,
            max(0, len(text) - max_chars),
            len(text),
            section_path="References",
        )
    return DocumentSlice(
        "references_scope",
        scope_text,
        start_offset=idx,
        end_offset=min(idx + len(scope_text), len(text)),
        section_path="References",
    )
