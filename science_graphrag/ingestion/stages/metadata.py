from __future__ import annotations

import re

from science_graphrag.domain.models import WorkDraft, WorkType
from science_graphrag.ingestion.dedup import find_doi_in_text, title_fingerprint
from science_graphrag.ingestion.stages.authorships import split_front_matter

_ARXIV_RE = re.compile(r"\b(?:arXiv:\s*)?(\d{4}\.\d{4,5})\b", re.IGNORECASE)
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def extract_metadata(text: str) -> WorkDraft:
    doi = find_doi_in_text(text)
    arxiv_m = _ARXIV_RE.search(text)
    arxiv_id = arxiv_m.group(1) if arxiv_m else None
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    title_lines, _, _ = split_front_matter(text)
    if title_lines:
        title = " ".join(title_lines)[:500]
    else:
        title = lines[0][:500] if lines else None
    norm = re.sub(r"\s+", " ", title).strip() if title else None
    year = None
    ym = _YEAR_RE.search(text[:3000])
    if ym:
        try:
            year = int(ym.group(0))
        except ValueError:
            year = None
    abs_start = None
    for i, ln in enumerate(lines):
        if ln.lower().startswith("abstract"):
            abs_start = i
            break
    abstract = None
    if abs_start is not None:
        ab_lines: list[str] = []
        for ln in lines[abs_start + 1 : abs_start + 40]:
            if ln.lower().startswith(("introduction", "keywords", "1.", "i.")):
                break
            ab_lines.append(ln)
        abstract = " ".join(ab_lines).strip() or None

    fp = title_fingerprint(norm or "", year) if norm else None
    return WorkDraft(
        title=title,
        normalized_title=norm,
        abstract=abstract,
        publication_year=year,
        doi=doi,
        arxiv_id=arxiv_id,
        fingerprint=fp,
        work_type=WorkType.UNKNOWN,
        ingestion_confidence=0.4,
    )


def merge_draft_prefer_enriched(base: WorkDraft, enriched: WorkDraft) -> WorkDraft:
    """Prefer registry-enriched non-null fields."""
    data = base.model_dump()
    for k, v in enriched.model_dump().items():
        if v is not None and v != "" and v != WorkType.UNKNOWN:
            data[k] = v
    unk = WorkType.UNKNOWN
    if enriched.work_type == unk and base.work_type and base.work_type != unk:
        data["work_type"] = base.work_type
    return WorkDraft.model_validate(data)
