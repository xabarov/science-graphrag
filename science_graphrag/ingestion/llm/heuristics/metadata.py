"""Helpers and fallback rules for metadata stage."""

from __future__ import annotations

import re

from science_graphrag.domain.models import WorkDraft, WorkType
from science_graphrag.ingestion.arxiv_ids import normalize_arxiv_id
from science_graphrag.ingestion.dedup import normalize_doi, title_fingerprint
from science_graphrag.ingestion.llm.schemas import WorkMetadataLLM


def truncate_text(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + "\n\n[... truncated for context limit ...]"


def map_work_type(raw: str | None) -> WorkType | None:
    if not raw or not raw.strip():
        return WorkType.UNKNOWN
    key = raw.strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "journal": WorkType.JOURNAL_ARTICLE,
        "article": WorkType.JOURNAL_ARTICLE,
        "conference": WorkType.CONFERENCE_PAPER,
        "proceedings": WorkType.CONFERENCE_PAPER,
        "arxiv": WorkType.PREPRINT,
        "preprint": WorkType.PREPRINT,
        "review": WorkType.REVIEW,
        "chapter": WorkType.BOOK_CHAPTER,
        "thesis": WorkType.THESIS,
        "phd": WorkType.THESIS,
        "report": WorkType.REPORT,
        "unknown": WorkType.UNKNOWN,
    }
    if key in aliases:
        return aliases[key]
    try:
        return WorkType(key)
    except ValueError:
        for work_type in WorkType:
            if work_type.value in key or key in work_type.value:
                return work_type
    return WorkType.UNKNOWN


def canonicalize_arxiv_id(raw: str | None) -> str | None:
    return normalize_arxiv_id(raw)


def work_from_llm(metadata: WorkMetadataLLM) -> WorkDraft:
    title = (metadata.title or "").strip() or None
    normalized_title = re.sub(r"\s+", " ", title).strip() if title else None
    year = metadata.publication_year
    fp = title_fingerprint(normalized_title or "", year) if normalized_title else None
    doi = normalize_doi(metadata.doi)
    arxiv_id = canonicalize_arxiv_id(metadata.arxiv_id)
    return WorkDraft(
        title=title[:500] if title else None,
        normalized_title=normalized_title,
        abstract=(metadata.abstract or "").strip() or None,
        publication_year=year,
        doi=doi,
        arxiv_id=arxiv_id,
        language=(metadata.language or "").strip() or None,
        venue_name=(metadata.venue_name or "").strip() or None,
        work_type=map_work_type(metadata.work_type),
        fingerprint=fp,
        ingestion_confidence=0.72,
        source_metadata={"extraction_stage": "llm"},
    )


def work_acceptable(draft: WorkDraft) -> bool:
    return bool(draft.title and draft.title.strip()) or bool(draft.doi)
