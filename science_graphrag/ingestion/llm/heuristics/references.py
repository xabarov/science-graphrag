"""Heuristic and merge utilities for references extraction."""

from __future__ import annotations

import re

from science_graphrag.domain.models import ReferenceDraft
from science_graphrag.ingestion.arxiv_ids import extract_arxiv_id_from_text, normalize_arxiv_id
from science_graphrag.ingestion.dedup import normalize_doi
from science_graphrag.ingestion.llm.schemas import ReferenceIdOnlyItemLLM, ReferenceItemLLM
from science_graphrag.ingestion.stages.references import extract_references

_LEADING_REF_ENUM_RE = re.compile(r"^\s*\[\d{1,4}\]\s*\.?\s*", re.MULTILINE)


def normalize_raw_reference_key(raw: str) -> str:
    text = (raw or "").strip()
    text = _LEADING_REF_ENUM_RE.sub("", text, count=1)
    text = re.sub(r"\s+", " ", text).lower()
    text = re.sub(r"[^a-z0-9.\-:/ ]+", "", text)
    return text[:500]


def canonicalize_arxiv_id(raw: str | None) -> str | None:
    return normalize_arxiv_id(raw)


def extract_references_heuristic(text: str) -> list[ReferenceDraft]:
    """Compatibility fallback entrypoint for regex-based references extraction."""

    return extract_references(text)


def references_from_llm(
    items: list[ReferenceItemLLM | ReferenceIdOnlyItemLLM],
    *,
    include_titles: bool,
) -> list[ReferenceDraft]:
    out: list[ReferenceDraft] = []
    for item in items:
        raw = (item.raw_reference or "").strip()
        if not raw:
            continue
        doi = normalize_doi(item.doi) or normalize_doi(raw)
        arx = canonicalize_arxiv_id(item.arxiv_id) or extract_arxiv_id_from_text(raw)
        title = None
        year = None
        if include_titles and isinstance(item, ReferenceItemLLM):
            title = (item.title or "").strip()[:400] or None
            year = item.year
        out.append(
            ReferenceDraft(
                raw_reference=raw[:4000],
                doi=doi,
                arxiv_id=arx,
                title=title,
                year=year,
            )
        )
        if len(out) >= 500:
            break
    return out


def _reference_identity(reference: ReferenceDraft) -> tuple[str, str]:
    if reference.doi:
        return "doi", reference.doi
    if reference.arxiv_id:
        return "arxiv", reference.arxiv_id
    return "raw", normalize_raw_reference_key(reference.raw_reference)


def _merge_reference_sets_enrich_only(
    heuristic_refs: list[ReferenceDraft],
    llm_refs: list[ReferenceDraft],
) -> tuple[list[ReferenceDraft], dict[str, int]]:
    merged: list[ReferenceDraft] = []
    index_by_identity: dict[tuple[str, str], int] = {}
    raw_identity_to_index: dict[str, int] = {}
    stats = {
        "heuristic_total": len(heuristic_refs),
        "llm_total": len(llm_refs),
        "llm_new_entries": 0,
        "llm_enriched_entries": 0,
        "llm_skipped_bare": 0,
        "merge_cap_applied": 0,
        "mode": "enrich_only",
    }
    for ref in heuristic_refs:
        identity = _reference_identity(ref)
        raw_identity = _reference_identity(ReferenceDraft(raw_reference=ref.raw_reference))[1]
        if identity[1]:
            index_by_identity[identity] = len(merged)
        if raw_identity:
            raw_identity_to_index[raw_identity] = len(merged)
        merged.append(ref.model_copy(deep=True))
    for ref in llm_refs:
        identity = _reference_identity(ref)
        raw_identity = _reference_identity(ReferenceDraft(raw_reference=ref.raw_reference))[1]
        idx = index_by_identity.get(identity) if identity[1] else None
        if idx is None and raw_identity:
            idx = raw_identity_to_index.get(raw_identity)
        if idx is None:
            continue
        existing = merged[idx]
        enriched = False
        if not existing.doi and ref.doi:
            existing.doi = ref.doi
            enriched = True
        if not existing.arxiv_id and ref.arxiv_id:
            existing.arxiv_id = ref.arxiv_id
            enriched = True
        if not existing.title and ref.title:
            existing.title = ref.title
            enriched = True
        if existing.year is None and ref.year is not None:
            existing.year = ref.year
            enriched = True
        if enriched:
            stats["llm_enriched_entries"] += 1
    return merged[:500], stats


def merge_reference_sets(
    heuristic_refs: list[ReferenceDraft],
    llm_refs: list[ReferenceDraft],
    *,
    mode: str = "conservative",
    max_extra_beyond_heuristic: int = 2,
) -> tuple[list[ReferenceDraft], dict[str, int]]:
    merged: list[ReferenceDraft] = []
    index_by_identity: dict[tuple[str, str], int] = {}
    raw_identity_to_index: dict[str, int] = {}
    policy = (mode or "conservative").strip().lower()
    stats = {
        "heuristic_total": len(heuristic_refs),
        "llm_total": len(llm_refs),
        "llm_new_entries": 0,
        "llm_enriched_entries": 0,
        "llm_skipped_bare": 0,
        "merge_cap_applied": 0,
        "mode": policy,
    }
    for ref in heuristic_refs:
        identity = _reference_identity(ref)
        raw_identity = _reference_identity(ReferenceDraft(raw_reference=ref.raw_reference))[1]
        if identity[1]:
            index_by_identity[identity] = len(merged)
        if raw_identity:
            raw_identity_to_index[raw_identity] = len(merged)
        merged.append(ref.model_copy(deep=True))
    for ref in llm_refs:
        identity = _reference_identity(ref)
        raw_identity = _reference_identity(ReferenceDraft(raw_reference=ref.raw_reference))[1]
        idx = index_by_identity.get(identity) if identity[1] else None
        if idx is None and raw_identity:
            idx = raw_identity_to_index.get(raw_identity)
        if idx is None:
            if policy == "conservative" and heuristic_refs and not ref.doi and not ref.arxiv_id:
                stats["llm_skipped_bare"] += 1
                continue
            merged.append(ref.model_copy(deep=True))
            stats["llm_new_entries"] += 1
            continue
        existing = merged[idx]
        enriched = False
        if not existing.doi and ref.doi:
            existing.doi = ref.doi
            enriched = True
        if not existing.arxiv_id and ref.arxiv_id:
            existing.arxiv_id = ref.arxiv_id
            enriched = True
        if not existing.title and ref.title:
            existing.title = ref.title
            enriched = True
        if existing.year is None and ref.year is not None:
            existing.year = ref.year
            enriched = True
        if enriched:
            stats["llm_enriched_entries"] += 1
    out = merged[:500]
    if (
        policy == "conservative"
        and heuristic_refs
        and len(out) > len(heuristic_refs) + max(0, max_extra_beyond_heuristic)
    ):
        out, cap_stats = _merge_reference_sets_enrich_only(heuristic_refs, llm_refs)
        cap_stats["merge_cap_applied"] = 1
        cap_stats["mode"] = policy
        cap_stats["llm_skipped_bare"] = stats["llm_skipped_bare"]
        return out, cap_stats
    return out, stats
