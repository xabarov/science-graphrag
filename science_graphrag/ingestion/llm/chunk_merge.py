"""
Contracts and helpers for merging extractions across chunks (Phase 2–3+).

Chunk-level dedup for embeddings lives in ingestion.chunking; this module
targets entity/relationship reconciliation after per-chunk LLM extraction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ProvenanceRef:
    """Links an extracted fact to source chunks (fingerprints stable across re-ingest)."""

    chunk_fingerprints: list[str] = field(default_factory=list)
    document_id: str | None = None
    work_id: str | None = None


@dataclass(slots=True)
class MergedEvidence:
    """Placeholder for aggregated descriptions per entity (future summarization step)."""

    texts: list[str] = field(default_factory=list)
    provenance: ProvenanceRef = field(default_factory=ProvenanceRef)


def merge_provenance_lists(
    left: list[str],
    right: list[str],
) -> list[str]:
    """Stable union preserving order."""
    seen: set[str] = set()
    out: list[str] = []
    for x in left + right:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def relationship_dedup_key(
    subject_key: object,
    predicate: str,
    object_key: object,
) -> tuple[object, str, object]:
    """Normalized tuple key for an edge (after entity resolution)."""
    return (subject_key, predicate.strip().lower(), object_key)


def entity_merge_key_work(
    *,
    doi: str | None,
    arxiv_id: str | None,
    title_fingerprint: str | None,
) -> str:
    """
    Deterministic priority: DOI > arXiv > title fingerprint.
    Callers should normalize DOI before passing.
    """
    if doi:
        return f"work:doi:{doi.lower()}"
    if arxiv_id:
        return f"work:arxiv:{arxiv_id.strip().lower()}"
    if title_fingerprint:
        return f"work:fp:{title_fingerprint}"
    return "work:unknown"


def entity_merge_key_author(normalized_name: str, affiliation_hint: str | None = None) -> str:
    """Stable author cluster key from normalized name and optional affiliation."""
    base = normalized_name.strip().lower()
    aff = (affiliation_hint or "").strip().lower()[:120]
    return f"author:{base}|{aff}"


def aggregate_edge_provenance(
    existing: dict[str, Any] | None,
    new_chunk_fps: list[str],
) -> dict[str, Any]:
    """Merge provenance into a relationship payload (JSON-serializable)."""
    payload = dict(existing or {})
    prev = payload.get("source_chunk_fingerprints") or []
    if not isinstance(prev, list):
        prev = [str(prev)]
    payload["source_chunk_fingerprints"] = merge_provenance_lists(
        [str(x) for x in prev],
        new_chunk_fps,
    )
    return payload
