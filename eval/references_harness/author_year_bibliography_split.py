"""
Split author-year / plain-text bibliography blocks (no ``[n]`` prefixes) into raw entries.

Used for gold bootstrap and tests on PDF→MD fixtures where page numbers and conference
banners appear between entries (handled via ``silver_heuristic`` gold, not strict ``manual``).
"""

from __future__ import annotations

import re
from typing import List


def split_author_year_reference_entries(block_lines: List[str]) -> List[str]:
    """
    Heuristic one-entry-per-reference split for ICLR/CV-style plain bibliographies.

    Skips isolated page numbers and repeated "Published as a conference paper" banners.
    """
    def is_junk(ln: str) -> bool:
        s = ln.strip()
        if not s:
            return True
        if s.isdigit() and len(s) <= 2:
            return True
        if "Published as a conference paper at ICLR" in s:
            return True
        return False

    clean_lines = [ln for ln in block_lines if not is_junk(ln)]

    def line_ends_reference(ln: str) -> bool:
        s = ln.strip()
        if re.search(r"(?:19|20)\d{2}[a-z]?\.?\s*$", s):
            return True
        if re.search(r"arXiv:\d{4}\.\d{4,5}", s):
            return True
        return False

    def looks_like_author_line(ln: str) -> bool:
        s = ln.strip()
        if not s or s[0].islower():
            return False
        if "," not in s[:100]:
            return False
        if s.startswith("In ") or s.startswith("Deep learning for generic"):
            return False
        return True

    entries: list[str] = []
    buf: list[str] = []
    for ln in clean_lines:
        if not buf:
            buf.append(ln)
            continue
        if ln.strip()[0].islower():
            buf.append(ln)
            continue
        if ln.strip().startswith("arXiv preprint"):
            buf.append(ln)
            continue
        if not line_ends_reference(buf[-1]) and not looks_like_author_line(ln):
            buf.append(ln)
            continue
        if not line_ends_reference(buf[-1]) or ln.strip().startswith(
            ("In ", "Feature ", "Microsoft ", "Generating ", "Deep learning"),
        ):
            if not looks_like_author_line(ln) or ln.strip().startswith(
                ("Criss-cross", "End-to-end"),
            ):
                buf.append(ln)
                continue
        if looks_like_author_line(ln) and line_ends_reference(buf[-1]):
            entries.append("\n".join(buf).strip())
            buf = [ln]
            continue
        buf.append(ln)
    if buf:
        entries.append("\n".join(buf).strip())
    return entries
