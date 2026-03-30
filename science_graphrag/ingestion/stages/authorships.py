from __future__ import annotations

import re

from science_graphrag.domain.models import AuthorshipDraft


def extract_authorships(text: str) -> list[AuthorshipDraft]:
    """Heuristic: lines between title (first line) and Abstract contain authors."""
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    if not lines:
        return []
    abs_idx = next((i for i, ln in enumerate(lines) if ln.lower().startswith("abstract")), None)
    if abs_idx is None or abs_idx <= 1:
        return []
    block = lines[1:abs_idx]
    if not block:
        return []
    author_line = " ".join(block)
    # split by comma and ' and '
    parts = re.split(r",|\band\b", author_line)
    names = [p.strip() for p in parts if p.strip() and len(p.strip()) > 2]
    out: list[AuthorshipDraft] = []
    for i, name in enumerate(names, start=1):
        if "@" in name or "university" in name.lower() or "institute" in name.lower():
            continue
        if len(name) > 120:
            continue
        out.append(
            AuthorshipDraft(
                author_position=i,
                author_raw_name=name,
                raw_affiliations=[],
            )
        )
    return out[:40]
