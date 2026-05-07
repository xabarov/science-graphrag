from __future__ import annotations

import re
from typing import Any

import httpx

from science_graphrag.domain.models import WorkDraft, WorkType
from science_graphrag.ingestion.dedup import normalize_doi, title_fingerprint

# Polite-pool contact when callers pass empty mailto; must match ``Settings.openalex_mailto`` default.
OPENALEX_MAILTO_FALLBACK = "dev@localhost"

_ARXIV_IN_URL_RE = re.compile(
    r"arxiv\.org/abs/(?P<id>\d{4}\.\d{4,5})(?:v\d+)?",
    re.IGNORECASE,
)


def _map_oa_type(raw: str | None) -> WorkType | None:
    if not raw:
        return None
    mapping = {
        "article": WorkType.JOURNAL_ARTICLE,
        "review": WorkType.REVIEW,
        "preprint": WorkType.PREPRINT,
        "book-chapter": WorkType.BOOK_CHAPTER,
        "dissertation": WorkType.THESIS,
        "report": WorkType.REPORT,
    }
    return mapping.get(raw.lower(), WorkType.UNKNOWN)


def fetch_work_by_doi(doi: str, mailto: str) -> dict[str, Any] | None:
    """OpenAlex API: https://docs.openalex.org/api-entities/works"""
    doi_clean = doi
    url = f"https://api.openalex.org/works/doi:{doi_clean}"
    headers = {"User-Agent": f"science-graphrag/0.1 (mailto:{mailto})"}
    with httpx.Client(timeout=30.0, headers=headers) as client:
        r = client.get(url)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()


def arxiv_id_from_openalex_ids(data: dict[str, Any]) -> str | None:
    """Best-effort arXiv id from OpenAlex `ids.arxiv` URL, if present."""

    ids = data.get("ids")
    if not isinstance(ids, dict):
        return None
    raw = ids.get("arxiv")
    if not raw or not isinstance(raw, str):
        return None
    match = _ARXIV_IN_URL_RE.search(raw)
    if match:
        return match.group("id")
    return None


def draft_from_openalex(data: dict[str, Any]) -> WorkDraft:
    title = data.get("title") or data.get("display_name")
    year = data.get("publication_year")
    abstract = None
    ia = data.get("abstract_inverted_index")
    if isinstance(ia, dict) and ia:
        # Reconstruct abstract from inverted index (OpenAlex format)
        positions: list[tuple[int, str]] = []
        for word, idxs in ia.items():
            for i in idxs:
                positions.append((i, word))
        positions.sort(key=lambda x: x[0])
        abstract = " ".join(w for _, w in positions)
    venue_name = None
    primary = data.get("primary_location") or {}
    src = primary.get("source") or {}
    venue_name = src.get("display_name")
    wt = _map_oa_type(data.get("type"))
    norm_title = re.sub(r"\s+", " ", title).strip() if title else None
    fp = title_fingerprint(norm_title or "", year) if norm_title else None
    return WorkDraft(
        title=title,
        normalized_title=norm_title,
        abstract=abstract,
        publication_year=year,
        doi=normalize_doi(data.get("doi")),
        openalex_id=data.get("id"),
        venue_name=venue_name,
        fingerprint=fp,
        work_type=wt or WorkType.UNKNOWN,
        ingestion_confidence=0.9,
        source_metadata={"openalex": data.get("id")},
    )
