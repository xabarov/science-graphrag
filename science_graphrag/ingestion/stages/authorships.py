from __future__ import annotations

import re

from science_graphrag.domain.models import AuthorshipDraft

_AFFILIATION_HINTS = (
    "university",
    "institute",
    "research",
    "laboratory",
    "lab",
    "department",
    "school",
    "college",
    "facebook ai",
    "allen institute",
)
_MARKER_RE = re.compile(r"(?P<base>.*?)(?P<markers>[*∗†‡¶]+)$")


def _lines(text: str) -> list[str]:
    return [ln.strip() for ln in text.split("\n") if ln.strip()]


def _abstract_index(lines: list[str]) -> int | None:
    return next((i for i, ln in enumerate(lines) if ln.lower().startswith("abstract")), None)


def _looks_like_author_line(line: str) -> bool:
    lower = line.lower()
    if "http://" in lower or "https://" in lower or "@" in line:
        return False
    if any(hint in lower for hint in _AFFILIATION_HINTS):
        return False
    if "," not in line:
        return False
    candidates = [part.strip() for part in line.split(",") if part.strip()]
    if len(candidates) < 2:
        return False
    valid = 0
    for part in candidates:
        cleaned = _strip_markers(part)
        words = [w for w in cleaned.split() if w]
        if 2 <= len(words) <= 5 and all(w[:1].isupper() for w in words if w[0].isalpha()):
            valid += 1
    return valid >= 2


def _strip_markers(value: str) -> str:
    value = re.sub(r"[*∗†‡¶]+", "", value)
    value = re.sub(r"\s+", " ", value).strip(" ,;")
    return value


def split_front_matter(text: str) -> tuple[list[str], str | None, list[str]]:
    lines = _lines(text)
    if not lines:
        return [], None, []
    abs_idx = _abstract_index(lines)
    head = lines[:abs_idx] if abs_idx is not None else lines[:8]
    author_idx = next(
        (i for i, ln in enumerate(head[1:], start=1) if _looks_like_author_line(ln)),
        None,
    )
    if author_idx is None:
        return head[:1], None, []
    title_lines = head[:author_idx]
    author_line = head[author_idx]
    affiliation_lines = head[author_idx + 1 :]
    return title_lines, author_line, affiliation_lines


def _affiliation_map(affiliation_lines: list[str]) -> tuple[dict[str, str], list[str]]:
    joined = " ".join(
        line
        for line in affiliation_lines
        if "http://" not in line and "https://" not in line
    )
    segments = [seg.strip() for seg in joined.split(",") if seg.strip()]
    marker_map: dict[str, str] = {}
    clean_all: list[str] = []
    for seg in segments:
        match = _MARKER_RE.match(seg)
        clean = _strip_markers(seg)
        if not clean:
            continue
        clean_all.append(clean)
        if match:
            for marker in match.group("markers"):
                marker_map[marker] = clean
    return marker_map, clean_all


def extract_authorships(text: str) -> list[AuthorshipDraft]:
    """Parse author line and map author markers to affiliation markers when possible."""
    _, author_line, affiliation_lines = split_front_matter(text)
    if not author_line:
        return []

    marker_map, all_affiliations = _affiliation_map(affiliation_lines)
    parts = [part.strip() for part in re.split(r",|\band\b", author_line) if part.strip()]
    out: list[AuthorshipDraft] = []
    for part in parts:
        lower = part.lower()
        if "http://" in lower or "https://" in lower:
            continue
        match = _MARKER_RE.match(part)
        markers = match.group("markers") if match else ""
        name = _strip_markers(match.group("base") if match else part)
        words = [w for w in name.split() if w]
        if not (2 <= len(words) <= 5):
            continue
        if any(hint in lower for hint in _AFFILIATION_HINTS):
            continue
        affiliations = [marker_map[m] for m in markers if m in marker_map]
        if not affiliations and all_affiliations:
            affiliations = all_affiliations
        out.append(
            AuthorshipDraft(
                author_position=len(out) + 1,
                author_raw_name=name,
                raw_affiliations=list(dict.fromkeys(affiliations)),
            )
        )
    return out[:40]
