"""
High-level deterministic tools for reference agent spikes (ref_gpt5.4_thoughts.md).

Not used in production ingestion.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from eval.references_harness.metrics import line_span_from_char_range
from eval.references_harness.scope_segmentation import (
    detect_reference_split_style,
    pred_raw_entries_from_bibliography_excerpt,
)
from eval.references_harness.validate import split_reference_entries
from science_graphrag.ingestion.document_slices import find_reference_section_spans
from science_graphrag.ingestion.stages.references import extract_references

BracketOrDot = Literal["bracket_numbered", "numeric_dot", "author_year", "unknown"]


def _line_signals(lines: list[str]) -> dict[str, Any]:
    n = max(len(lines), 1)
    bracket = sum(1 for ln in lines if re.match(r"^\s*\[\d+\]", ln.strip()))
    numeric_dot = sum(1 for ln in lines if re.match(r"^\s*\d+\.\s", ln.strip()))
    dois = sum(1 for ln in lines if re.search(r"\b10\.\d{4,}/", ln, re.I))
    arxiv = sum(1 for ln in lines if re.search(r"arxiv\s*:", ln, re.I) or "/abs/" in ln.lower())
    years = sum(1 for ln in lines if re.search(r"\b(19|20)\d{2}\b", ln))
    return {
        "lines_total": len(lines),
        "lines_starting_bracket_numbered": bracket,
        "lines_starting_numeric_dot": numeric_dot,
        "lines_with_doi_pattern": dois,
        "lines_with_arxiv_hint": arxiv,
        "lines_with_year_token": years,
        "bracket_density": round(bracket / n, 4),
        "numeric_dot_density": round(numeric_dot / n, 4),
        "doi_density": round(dois / n, 4),
    }


def bibliography_candidates(text: str) -> list[dict[str, Any]]:
    """
    Heuristic bibliography zones from ``find_reference_section_spans`` as 1-based line ranges
    plus marker densities (ref_gpt5.4_thoughts: find_bibliography_candidates).
    """
    lines = text.splitlines()
    n_doc = len(lines)
    candidates: list[dict[str, Any]] = []
    for start_c, end_c in find_reference_section_spans(text):
        a, b = line_span_from_char_range(text, start_c, end_c)
        if b < a:
            continue
        block = lines[a - 1 : b]
        sig = _line_signals(block)
        sig["start_line"] = a
        sig["end_line"] = b
        sig["near_document_end"] = b >= max(1, n_doc - 5)
        candidates.append(sig)
    if not candidates and n_doc:
        tail = lines[max(0, n_doc - 200) :]
        sig = _line_signals(tail)
        sig["start_line"] = max(1, n_doc - len(tail) + 1)
        sig["end_line"] = n_doc
        sig["near_document_end"] = True
        sig["note"] = "fallback_tail_no_heading"
        candidates.append(sig)
    return candidates


def count_reference_markers(lines: list[str], start_line: int, end_line: int) -> dict[str, Any]:
    """1-based inclusive line slice (ref_gpt5.4_thoughts: count_reference_markers)."""
    if start_line < 1 or end_line < start_line:
        return {"error": "invalid_range", "lines_total": 0}
    sl = lines[start_line - 1 : end_line]
    out = _line_signals(sl)
    out["start_line"] = start_line
    out["end_line"] = end_line
    return out


def infer_segmentation_style(lines: list[str]) -> BracketOrDot:
    if not lines:
        return "unknown"
    st = detect_reference_split_style(lines)
    if st == "bracket_numbered":
        return "bracket_numbered"
    if st == "numeric_dot":
        return "numeric_dot"
    head = [ln for ln in lines[:40] if ln.strip()]
    if any(re.search(r"^\s*\[\d+\]", ln.strip()) for ln in head):
        return "bracket_numbered"
    if any(re.match(r"^\s*\d+\.\s", ln.strip()) for ln in head):
        return "numeric_dot"
    return "author_year"


def segment_reference_block_lines(
    lines: list[str],
    start_line: int,
    end_line: int,
    style_hint: str | None = None,
) -> dict[str, Any]:
    """
    Deterministic segmentation (ref_gpt5.4_thoughts: segment_reference_block).

    Uses line splits for numbered styles; otherwise bench-aligned excerpt segmentation.
    """
    if start_line < 1 or end_line < start_line:
        return {
            "error": "invalid_range",
            "count": 0,
            "entries_preview": [],
            "raw_entries": [],
        }
    block_lines = lines[start_line - 1 : end_line]
    block_text = "\n".join(block_lines)
    inferred = infer_segmentation_style(block_lines)

    if style_hint in (None, "", "auto"):
        if inferred == "bracket_numbered":
            entries = split_reference_entries(block_lines, "bracket_numbered")
        elif inferred == "numeric_dot":
            entries = split_reference_entries(block_lines, "numeric_dot")
        else:
            entries = pred_raw_entries_from_bibliography_excerpt(block_text, "author_year")
    elif style_hint == "bracket_numbered":
        entries = split_reference_entries(block_lines, "bracket_numbered")
    elif style_hint == "numeric_dot":
        entries = split_reference_entries(block_lines, "numeric_dot")
    elif style_hint == "author_year":
        entries = pred_raw_entries_from_bibliography_excerpt(block_text, "author_year")
    else:
        entries = pred_raw_entries_from_bibliography_excerpt(block_text, style_hint)

    return {
        "inferred_style": inferred,
        "style_hint_used": style_hint or "auto",
        "count": len(entries),
        "entries_preview": [e[:120] for e in entries[:3]],
        "raw_entries": entries,
    }


def heuristic_full_count(text: str) -> int:
    return len(extract_references(text))
