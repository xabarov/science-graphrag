"""
Heuristic detection of the main ``## References`` bibliography span for layer-1 fixtures.

Used to bootstrap ``references_benchmark`` gold (manual annotation_kind when checks pass).
Rules are documented in ``docs/benchmarks/references-benchmark-gold-sop.md``.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple

from eval.references_harness.validate import split_reference_entries

SplitStyle = str  # "bracket_numbered" | "numeric_dot"


class BibliographySpanResult(NamedTuple):
    """Detected span (1-based inclusive line numbers) and split entries."""

    start_line: int
    end_line: int
    raw_entries: list[str]
    style: SplitStyle


def _truncate_supplementary(lines: list[str]) -> list[str]:
    out: list[str] = []
    for ln in lines:
        if "– Supplementary" in ln or ln.strip() == "# Supplementary":
            break
        out.append(ln)
    return out


def _collect_monotonic_ref_starts(lines: list[str], heading_line: int) -> list[tuple[int, int]]:
    """
    Line numbers where a line starts with ``[n]``, stopping when numbering breaks
    (e.g. inline ``[2]. Does`` after ``[21]`` in YOLOv3 rebuttal).
    """
    ref_lines: list[tuple[int, int]] = []
    prev_n = 0
    for i, ln in enumerate(lines[heading_line:], start=heading_line + 1):
        mm = re.match(r"^\s*\[(\d+)\]", ln)
        if not mm:
            continue
        n = int(mm.group(1))
        if ref_lines:
            if n == 1 and prev_n > 3:
                break
            if n < prev_n:
                break
        ref_lines.append((i, n))
        prev_n = n
    return ref_lines


def _find_end_after_last_ref(
    lines: list[str],
    ref_lines: list[tuple[int, int]],
) -> tuple[int, int] | None:
    if not ref_lines:
        return None
    start_line = ref_lines[0][0]
    last_num = ref_lines[-1][1]
    last_start = ref_lines[-1][0]
    end_line = last_start
    i = last_start
    while i < len(lines):
        i += 1
        if i > len(lines):
            break
        ln = lines[i - 1]
        mm = re.match(r"^\s*\[(\d+)\]", ln)
        if mm:
            n = int(mm.group(1))
            if n == 1 and i > last_start + 2:
                break
            if n > last_num:
                last_num = n
                last_start = i
                end_line = i
                continue
            if n < last_num:
                break
        s = ln.strip()
        if not s:
            continue
        if s.startswith("Figure ") or s.startswith("Table ") or s.startswith("Fig. "):
            break
        if re.match(r"^A\s+[A-Z]", s):
            break
        if re.match(r"^\d{1,3}$", s) and len(s) <= 3:
            end_line = i - 2
            break
        if s.startswith("person ") or s.startswith("pool5 "):
            break
        end_line = i
    return start_line, end_line


def detect_bracket_bibliography_span(article_lines: list[str]) -> BibliographySpanResult | None:
    """
    Find the primary ``## References`` block and split bracket-numbered entries.

    Returns ``None`` if no ``## References`` heading exists.
    """
    lines = _truncate_supplementary(article_lines)
    text = "\n".join(lines)
    m = re.search(r"(?m)^##\s+References\s*$", text)
    if not m:
        return None
    heading_line = text[: m.start()].count("\n") + 1
    ref_starts = _collect_monotonic_ref_starts(lines, heading_line)
    span = _find_end_after_last_ref(lines, ref_starts)
    if span is None:
        return None
    start_line, end_line = span
    chunk = lines[start_line - 1 : end_line]
    entries = split_reference_entries(chunk, "bracket_numbered")
    return BibliographySpanResult(
        start_line=start_line,
        end_line=end_line,
        raw_entries=entries,
        style="bracket_numbered",
    )


def span_result_from_article_path(article_path: Path) -> BibliographySpanResult | None:
    """Load ``article.md`` from disk and run :func:`detect_bracket_bibliography_span`."""
    lines = article_path.read_text(encoding="utf-8").splitlines()
    return detect_bracket_bibliography_span(lines)
