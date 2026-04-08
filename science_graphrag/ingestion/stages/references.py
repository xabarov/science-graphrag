from __future__ import annotations

import re

from science_graphrag.domain.models import ReferenceDraft
from science_graphrag.ingestion.arxiv_ids import extract_arxiv_id_from_text, normalize_arxiv_id
from science_graphrag.ingestion.dedup import normalize_doi

_REF_HEAD_RE = re.compile(
    r"^#{0,3}\s*(references|bibliography)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_NUMBERED_REF_RE = re.compile(r"^(?:\[\d+\]|\d+\.)\s+")
_AUTHOR_YEAR_REF_RE = re.compile(
    r"^[A-Z][A-Za-z'`\-]+(?:,\s+[A-Z]\.)?(?:\s+(?:and|&)\s+[A-Z][A-Za-z'`\-]+(?:,\s+[A-Z]\.)?)?.*?\(\d{4}\)",
)
_AUTHOR_LINE_START_RE = re.compile(
    r"^[A-Z][A-Za-z'`\-]+,\s+[A-Z](?:\.[A-Z])?\.?(?:,|\s)",
)
_SENTENCE_START_RE = re.compile(r"^[A-Z][^:]{10,}$")
_YEAR_RE = re.compile(r"\((?:19|20)\d{2}\)")


def _looks_like_new_reference(line: str) -> bool:
    if _NUMBERED_REF_RE.match(line):
        return True
    if _AUTHOR_YEAR_REF_RE.match(line):
        return True
    if _AUTHOR_LINE_START_RE.match(line):
        return True
    return False


def _reference_lines(text: str) -> list[str]:
    m = _REF_HEAD_RE.search(text)
    if not m:
        return []
    tail = text[m.end() :]
    return [ln.strip() for ln in tail.split("\n") if ln.strip()]


def split_reference_entries(text: str) -> list[str]:
    lines = _reference_lines(text)
    if not lines:
        return []

    entries: list[list[str]] = []
    current: list[str] = []

    def flush() -> None:
        nonlocal current
        if current:
            entries.append(current)
            current = []

    for ln in lines:
        starts_new = _looks_like_new_reference(ln)
        if starts_new:
            flush()
            s = re.sub(r"^\[\d+\]\s*", "", ln)
            s = re.sub(r"^\d+\.\s+", "", s)
            current.append(s)
            continue

        if current:
            current.append(ln)
            continue

        if _SENTENCE_START_RE.match(ln) and _YEAR_RE.search(ln):
            current.append(ln)

    flush()
    return [" ".join(part for part in entry if part).strip() for entry in entries if entry]


def extract_references(text: str) -> list[ReferenceDraft]:
    refs: list[ReferenceDraft] = []
    doi_re = re.compile(r"\b(10\.\d{4,9}/\S+)\b", re.IGNORECASE)
    year_re = re.compile(r"\b(19|20)\d{2}\b")
    for raw in split_reference_entries(text):
        dm = doi_re.search(raw)
        doi = normalize_doi(dm.group(1)) if dm else None
        ym = year_re.search(raw)
        year = int(ym.group(0)) if ym else None
        arxiv_id = extract_arxiv_id_from_text(raw)
        if not arxiv_id:
            arxiv_id = normalize_arxiv_id(raw)
        title = None
        if doi:
            title = raw.split(doi)[0].strip(" .-")[:400] or None
        refs.append(
            ReferenceDraft(
                raw_reference=raw[:4000],
                doi=doi,
                title=title,
                year=year,
                arxiv_id=arxiv_id,
            )
        )
    return refs[:500]
