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
    r"^[A-Z][A-Za-z'`\-]+(?:,\s+[A-Z]\.)?"
    r"(?:\s+(?:and|&)\s+[A-Z][A-Za-z'`\-]+(?:,\s+[A-Z]\.)?)?.*?\(\d{4}\)",
)
_AUTHOR_LINE_START_RE = re.compile(
    r"^[A-Z][A-Za-z'`\-]+,\s+[A-Z](?:\.[A-Z])?\.?(?:,|\s)",
)
_SENTENCE_START_RE = re.compile(r"^[A-Z][^:]{10,}$")
_YEAR_RE = re.compile(r"\((?:19|20)\d{2}\)")
# Plain bibliography lines: "First Last, First Last, ..." (no [n]. or n. prefix),
# common in ICLR/CV PDFs.
_PLAIN_AUTHOR_LIST_LINE_RE = re.compile(
    r"^[A-Z][^,\n]{0,120},\s+[A-Z]",
)


def _looks_like_plain_author_list_line(line: str) -> bool:
    """Detect author-year blocks without numeric prefixes (Deformable DETR-style)."""
    s = line.strip()
    if len(s) < 24:
        return False
    if s.startswith(
        (
            "In ",
            "Deep learning for generic",
            "Feature ",
            "Microsoft ",
            "Generating ",
            "Criss-cross",
            "End-to-end",
            "arXiv preprint",
            "http",
        ),
    ):
        return False
    if _NUMBERED_REF_RE.match(s):
        return False
    return bool(_PLAIN_AUTHOR_LIST_LINE_RE.match(s))


def _looks_like_new_reference(line: str) -> bool:
    if _NUMBERED_REF_RE.match(line):
        return True
    if _AUTHOR_YEAR_REF_RE.match(line):
        return True
    if _AUTHOR_LINE_START_RE.match(line):
        return True
    if _looks_like_plain_author_list_line(line):
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
