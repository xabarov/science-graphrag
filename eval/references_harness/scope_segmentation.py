"""Fair segmentation of bibliography excerpts for benchmark ``scope_llm`` (plan A1)."""

from __future__ import annotations

import re

from eval.references_harness.validate import SplitStyle, split_reference_entries
from science_graphrag.ingestion.llm.reference_tool_router import (
    extract_references_from_bibliography_excerpt,
)

_REF_HEAD_LINE = re.compile(r"^#{1,3}\s*(references|bibliography)\s*$", re.IGNORECASE)
_BRACKET_ENTRY_SPLIT = re.compile(r"\n(?=\s*\[\d+\])")


def normalize_excerpt_body_lines(excerpt: str) -> list[str]:
    """Drop leading blank lines and optional ``## References`` heading line."""
    lines = excerpt.splitlines()
    while lines and not lines[0].strip():
        lines = lines[1:]
    if lines and _REF_HEAD_LINE.match(lines[0].strip()):
        lines = lines[1:]
    while lines and not lines[0].strip():
        lines = lines[1:]
    return lines


def detect_reference_split_style(bibliography_lines: list[str]) -> SplitStyle:
    """Infer ``bracket_numbered`` vs ``numeric_dot`` from the first substantive line."""
    for ln in bibliography_lines:
        s = ln.strip()
        if not s:
            continue
        if re.match(r"^\[\d+\]", s):
            return "bracket_numbered"
        if re.match(r"^\d+\.\s", s):
            return "numeric_dot"
    return "bracket_numbered"


def _split_style_for_hint(
    lines: list[str],
    bibliography_style_hint: str | None,
) -> SplitStyle:
    hint = (bibliography_style_hint or "auto").strip().lower()
    style: SplitStyle
    if hint == "author_year":
        style = detect_reference_split_style(lines)
    elif hint in ("bracket_numbered", "bracket", "[n]"):
        style = "bracket_numbered"
    elif hint in ("numeric_dot", "n_dot", "1_dot"):
        style = "numeric_dot"
    elif hint in ("numbered", "numeric", "auto", ""):
        b = split_reference_entries(lines, "bracket_numbered")
        n = split_reference_entries(lines, "numeric_dot")
        if len(b) >= 2 and len(n) >= 2:
            style = "bracket_numbered" if len(b) >= len(n) else "numeric_dot"
        elif len(b) >= 2:
            style = "bracket_numbered"
        elif len(n) >= 2:
            style = "numeric_dot"
        else:
            style = detect_reference_split_style(lines)
    else:
        style = detect_reference_split_style(lines)
    return style


def _post_split_collapsed_bracket_blob(entries: list[str]) -> list[str]:
    """
    When line-based split or the LLM returns one blob with many ``[n]`` entries, split on
    ``[n]`` boundaries (scope_llm collapse regression).
    """
    if len(entries) != 1:
        return entries
    blob = entries[0].strip()
    if len(re.findall(r"\[\d+\]", blob)) < 2:
        return entries
    parts = [p.strip() for p in _BRACKET_ENTRY_SPLIT.split(blob) if p.strip()]
    return parts if len(parts) >= 2 else entries


def pred_raw_entries_from_bibliography_excerpt(
    excerpt: str,
    bibliography_style_hint: str | None,
) -> list[str]:
    """
    Split excerpt like gold ``raw_entries`` when possible; else LLM-assisted parse.

    For ``author_year`` hint, skip line-based split and use extract path only.
    """
    excerpt = excerpt.strip()
    if not excerpt:
        return []
    hint = (bibliography_style_hint or "auto").strip().lower()
    lines = normalize_excerpt_body_lines(excerpt)

    if hint == "author_year":
        merged_ay = [
            r.raw_reference.strip()
            for r in extract_references_from_bibliography_excerpt(excerpt)
            if r.raw_reference
        ]
        return _post_split_collapsed_bracket_blob(merged_ay)

    style = _split_style_for_hint(lines, bibliography_style_hint)
    split_entries = split_reference_entries(lines, style) if lines else []
    split_entries = _post_split_collapsed_bracket_blob(split_entries)
    if len(split_entries) >= 2:
        return split_entries

    merged = [
        r.raw_reference.strip()
        for r in extract_references_from_bibliography_excerpt(excerpt)
        if r.raw_reference
    ]
    merged = _post_split_collapsed_bracket_blob(merged)
    if merged:
        return merged
    return split_entries
