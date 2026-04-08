"""Consistency checks between ``references_benchmark`` gold and ``article.md``."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from eval.layer1.spec import ReferencesBenchmarkGold

SplitStyle = Literal["bracket_numbered", "numeric_dot"]


def normalize_ws(text: str) -> str:
    """Collapse whitespace for robust comparison of bibliography text."""
    return " ".join(text.split())


def assert_references_benchmark_consistent(
    article_path: Path,
    rb: ReferencesBenchmarkGold,
) -> None:
    """
    Verify bibliography line span and ``raw_entries``.

    For ``manual`` kind, joining entries with newlines matches the span (ws-normalized).
    For ``silver_heuristic``, only bounds and non-empty entries are required.
    """
    lines = article_path.read_text(encoding="utf-8").splitlines()
    start, end = rb.bibliography.start_line, rb.bibliography.end_line
    if end > len(lines):
        raise AssertionError(
            f"end_line {end} exceeds article line count {len(lines)} for {article_path}",
        )
    if start < 1:
        raise AssertionError(f"start_line must be >= 1 for {article_path}")
    if not rb.raw_entries:
        raise AssertionError(f"raw_entries empty for {article_path}")

    if rb.annotation_kind == "silver_heuristic":
        return

    block = "\n".join(lines[start - 1 : end])
    merged = "\n".join(rb.raw_entries)
    if normalize_ws(block) != normalize_ws(merged):
        raise AssertionError(
            f"references_benchmark text mismatch for {article_path}: "
            "normalized bibliography lines != normalized joined raw_entries",
        )


def split_reference_entries(
    bibliography_lines: list[str],
    style: SplitStyle,
) -> list[str]:
    """
    Split a bibliography block into raw entries.

    * ``bracket_numbered``: new entry at a line starting with ``[n]``.
    * ``numeric_dot``: new entry at a line starting with ``n.`` (digit + dot + space).
    """
    text = "\n".join(bibliography_lines)
    if style == "bracket_numbered":
        parts = re.split(r"\n(?=\s*\[\d+\])", text)
    else:
        parts = re.split(r"\n(?=\s*\d+\.\s)", text)
    return [p.strip() for p in parts if p.strip()]


def split_numbered_reference_entries(bibliography_lines: list[str]) -> list[str]:
    """Backward-compatible alias for ``bracket_numbered`` style."""
    return split_reference_entries(bibliography_lines, "bracket_numbered")
