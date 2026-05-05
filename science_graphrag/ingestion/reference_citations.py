"""Neo4j reference citation persistence + small OpenAlex/dedup helpers for ingestion."""

from __future__ import annotations

import json
import re
import unicodedata
import uuid
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from science_graphrag.config import Settings
from science_graphrag.domain.models import ReferenceDraft, WorkDraft
from science_graphrag.ingestion.arxiv_ids import normalize_arxiv_id
from science_graphrag.ingestion.dedup import normalize_doi, title_fingerprint
from science_graphrag.ingestion.enrichment.openalex import (
    arxiv_id_from_openalex_ids,
    fetch_work_by_doi,
)
from science_graphrag.ingestion.normalize import normalize_text
from science_graphrag.utils.project_logging import get_logger

log = get_logger("ingestion.reference_citations")


@retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3), reraise=True)
def openalex_lookup_with_retry(doi: str, mailto: str) -> dict[str, Any] | None:
    """Fetch OpenAlex work JSON for a DOI with retries."""
    return fetch_work_by_doi(doi, mailto)


def normalized_title_for_fingerprint(title: str | None) -> str | None:
    """Normalize titles for deterministic fingerprinting."""
    if not title:
        return None
    t = normalize_text(title)
    t = unicodedata.normalize("NFKC", t).casefold()
    # Keep letters/digits across scripts and spaces; drop punctuation/symbols.
    t = "".join(ch for ch in t if ch.isalnum() or ch.isspace())
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) < 6:
        return None
    return t


def venue_id(venue_name: str | None) -> str:
    """Stable Venue.id derived from normalized venue_name."""
    name = normalize_text(venue_name or "").strip()
    if not name:
        return ""
    slug = re.sub(r"\s+", " ", name.lower()).strip()
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"venue:{slug}"))


def resolve_work_id(neo, draft: WorkDraft) -> str:
    """Allocate a stable-ish :Work id for the ingested document's WorkDraft."""
    doi = normalize_doi(draft.doi)
    if doi:
        existing = neo.find_work_id_by_doi(doi)
        if existing:
            return existing
        wid = str(uuid.uuid4())
        neo.upsert_minimal_work(
            wid,
            title=draft.title,
            publication_year=draft.publication_year,
            doi=doi,
            arxiv_id=normalize_arxiv_id(draft.arxiv_id),
            fingerprint=draft.fingerprint,
            openalex_id=draft.openalex_id,
            ingestion_confidence=float(draft.ingestion_confidence),
        )
        return wid

    arxiv = normalize_arxiv_id(draft.arxiv_id)
    if arxiv:
        existing = neo.find_work_id_by_arxiv(arxiv)
        if existing:
            return existing
        wid = str(uuid.uuid4())
        fp = draft.fingerprint
        if fp is None and draft.title and draft.publication_year is not None:
            nt = normalized_title_for_fingerprint(draft.title)
            if nt:
                fp = title_fingerprint(nt, draft.publication_year)
        neo.upsert_minimal_work(
            wid,
            title=draft.title,
            publication_year=draft.publication_year,
            doi=None,
            arxiv_id=arxiv,
            fingerprint=fp,
            openalex_id=draft.openalex_id,
            ingestion_confidence=float(draft.ingestion_confidence),
        )
        return wid

    fp = draft.fingerprint
    if fp:
        existing = neo.find_work_id_by_fingerprint(fp)
        if existing:
            return existing

    nt = normalized_title_for_fingerprint(draft.title) if draft.title else None
    if nt and draft.publication_year is not None:
        fp2 = title_fingerprint(nt, draft.publication_year)
        existing = neo.find_work_id_by_fingerprint(fp2)
        if existing:
            return existing
        wid = str(uuid.uuid4())
        neo.upsert_minimal_work(
            wid,
            title=draft.title,
            publication_year=draft.publication_year,
            doi=None,
            arxiv_id=None,
            fingerprint=fp2,
            openalex_id=draft.openalex_id,
            ingestion_confidence=float(draft.ingestion_confidence),
        )
        return wid

    wid = str(uuid.uuid4())
    neo.upsert_minimal_work(
        wid,
        title=draft.title,
        publication_year=draft.publication_year,
        doi=None,
        arxiv_id=None,
        fingerprint=fp,
        openalex_id=draft.openalex_id,
        ingestion_confidence=float(draft.ingestion_confidence),
    )
    return wid


def persist_reference_citation(
    neo, citing_work_id: str, ref: ReferenceDraft, settings: Settings
) -> None:
    """Upsert/link a cited :Work from a parsed reference line."""
    doi = normalize_doi(ref.doi)
    if doi:
        cited = neo.find_work_id_by_doi(doi)
        if cited:
            neo.merge_cites(citing_work_id, cited)
            return

        openalex_id = None
        try:
            oa = fetch_work_by_doi(doi, settings.openalex_mailto)
            if oa:
                openalex_id = oa.get("id") if isinstance(oa, dict) else None
        except (
            httpx.HTTPError,
            json.JSONDecodeError,
            ValueError,
            TypeError,
            KeyError,
            AttributeError,
            RuntimeError,
            TimeoutError,
            OSError,
        ) as exc:
            log.warning(
                "OpenAlex fetch_work_by_doi failed (continuing without openalex_id): doi=%s err=%s",
                doi,
                exc,
            )
            openalex_id = None

        cited = str(uuid.uuid4())
        neo.upsert_minimal_work(
            cited,
            title=ref.title,
            publication_year=ref.year,
            doi=doi,
            arxiv_id=None,
            fingerprint=None,
            openalex_id=str(openalex_id) if openalex_id else None,
            ingestion_confidence=0.55,
        )
        neo.merge_cites(citing_work_id, cited)
        return

    arxiv = normalize_arxiv_id(ref.arxiv_id)
    if arxiv:
        cited = neo.find_work_id_by_arxiv(arxiv)
        if cited:
            neo.merge_cites(citing_work_id, cited)
            return
        cited = str(uuid.uuid4())
        fp = None
        nt = normalized_title_for_fingerprint(ref.title)
        if nt and ref.year is not None:
            fp = title_fingerprint(nt, ref.year)
        neo.upsert_minimal_work(
            cited,
            title=ref.title,
            publication_year=ref.year,
            doi=None,
            arxiv_id=arxiv,
            fingerprint=fp,
            openalex_id=None,
            ingestion_confidence=0.55,
        )
        neo.merge_cites(citing_work_id, cited)
        return

    nt = normalized_title_for_fingerprint(ref.title)
    if nt is None or ref.year is None:
        return
    fp = title_fingerprint(nt, ref.year)
    cited = neo.find_work_id_by_fingerprint(fp)
    if cited:
        neo.merge_cites(citing_work_id, cited)
        return

    cited = str(uuid.uuid4())
    neo.upsert_minimal_work(
        cited,
        title=ref.title,
        publication_year=ref.year,
        doi=None,
        arxiv_id=None,
        fingerprint=fp,
        openalex_id=None,
        ingestion_confidence=0.45,
    )
    neo.merge_cites(citing_work_id, cited)


def maybe_link_openalex_arxiv_version(
    neo,
    _work_id: str,
    draft: WorkDraft | None,
    oa_raw: dict[str, Any] | None,
) -> None:
    """Cross-link arXiv preprint identifiers between extraction and OpenAlex hints."""
    if not draft or not oa_raw:
        return
    oa_arxiv = arxiv_id_from_openalex_ids(oa_raw)
    local_arxiv = normalize_arxiv_id(draft.arxiv_id)
    if not oa_arxiv or not local_arxiv or oa_arxiv == local_arxiv:
        return

    a = neo.find_work_id_by_arxiv(local_arxiv)
    b = neo.find_work_id_by_arxiv(oa_arxiv)
    if not a or not b or a == b:
        return
    neo.merge_related_version(a, b)
