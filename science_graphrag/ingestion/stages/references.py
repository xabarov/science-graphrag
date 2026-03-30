from __future__ import annotations

import re

from science_graphrag.domain.models import ReferenceDraft
from science_graphrag.ingestion.dedup import normalize_doi

_REF_HEAD_RE = re.compile(r"^\s*(references|bibliography)\s*$", re.IGNORECASE | re.MULTILINE)


def extract_references(text: str) -> list[ReferenceDraft]:
    m = _REF_HEAD_RE.search(text)
    if not m:
        return []
    tail = text[m.end() :]
    lines = [ln.strip() for ln in tail.split("\n") if ln.strip()]
    refs: list[ReferenceDraft] = []
    buf: list[str] = []
    doi_re = re.compile(r"\b(10\.\d{4,9}/\S+)\b", re.IGNORECASE)
    year_re = re.compile(r"\b(19|20)\d{2}\b")

    def flush() -> None:
        nonlocal buf
        if not buf:
            return
        raw = " ".join(buf)
        dm = doi_re.search(raw)
        doi = normalize_doi(dm.group(1)) if dm else None
        ym = year_re.search(raw)
        year = int(ym.group(0)) if ym else None
        title = None
        if doi:
            title = raw.split(doi)[0].strip(" .-")[:400] or None
        refs.append(
            ReferenceDraft(
                raw_reference=raw[:4000],
                doi=doi,
                title=title,
                year=year,
            )
        )
        buf = []

    for ln in lines:
        if re.match(r"^\[\d+\]\s+", ln) or re.match(r"^\d+\.\s+", ln):
            flush()
            s = re.sub(r"^\[\d+\]\s*", "", ln)
            s = re.sub(r"^\d+\.\s+", "", s)
            buf.append(s)
        else:
            if buf:
                buf.append(ln)
    flush()
    return refs[:500]
