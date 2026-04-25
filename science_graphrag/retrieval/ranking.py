"""Pure-python ranking helpers for retrieval hits."""

from __future__ import annotations

from typing import Any

_BACK_MATTER_MARKERS: tuple[str, ...] = (
    "acknowledg",
    "reference",
    "references",
    "bibliograph",
    "appendix",
)


def _is_likely_back_matter_section(section_path: str | None) -> bool:
    if not section_path:
        return False
    s = section_path.lower()
    return any(marker in s for marker in _BACK_MATTER_MARKERS)


def _body_section_bonus(section_path: str | None) -> float:
    if not section_path:
        return 0.0
    s = section_path.lower()
    tiers: tuple[tuple[tuple[str, ...], float], ...] = (
        (("abstract", "summary"), 0.04),
        (("introduction", "intro", "overview"), 0.035),
        (("method", "approach", "architecture", "model", "network"), 0.03),
        (("experiment", "result", "evaluation", "implementation"), 0.02),
    )
    for keys, bonus in tiers:
        if any(k in s for k in keys):
            return bonus
    if "related work" in s:
        return 0.015
    return 0.0


def _rank_hits_for_answer(hits: list[dict[str, Any]], *, top_k: int) -> list[dict[str, Any]]:
    if not hits:
        return []

    def sort_key(hit: dict[str, Any]) -> tuple[bool, float]:
        section_path = hit.get("section_path")
        is_back_matter = _is_likely_back_matter_section(section_path)
        base_score = float(hit.get("score") or 0.0)
        boosted = base_score + _body_section_bonus(section_path)
        return (is_back_matter, -boosted)

    return sorted(hits, key=sort_key)[:top_k]


def _citations_and_snippets_from_hits(
    hits: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    citations: list[dict[str, Any]] = []
    snippets: list[str] = []
    for rank, hit in enumerate(hits, start=1):
        text = (hit.get("text") or "").strip()
        if not text:
            continue
        citation: dict[str, Any] = {
            "rank": rank,
            "score": hit.get("score"),
            "work_id": hit.get("work_id"),
            "document_id": hit.get("document_id"),
            "chunk_fingerprint": hit.get("chunk_fingerprint"),
            "section_path": hit.get("section_path"),
            "excerpt": text[:600],
        }
        if hit.get("chunk_kind") is not None:
            citation["chunk_kind"] = hit.get("chunk_kind")
        if hit.get("language") is not None:
            citation["language"] = hit.get("language")
        if hit.get("rrf_score") is not None:
            citation["rrf_score"] = hit.get("rrf_score")
        citations.append(citation)
        snippets.append(text[:400])
    return citations, snippets


def _hit_fingerprint_key(hit: dict[str, Any]) -> str:
    chunk_fingerprint = hit.get("chunk_fingerprint")
    if chunk_fingerprint:
        return str(chunk_fingerprint)
    return str(hit.get("id") or "")


def _reciprocal_rank_fusion(
    ranked_lists: list[list[dict[str, Any]]],
    *,
    k: int = 60,
    top_n: int = 12,
) -> list[dict[str, Any]]:
    scores: dict[str, float] = {}
    by_fp: dict[str, dict[str, Any]] = {}
    for ranked_list in ranked_lists:
        for rank, hit in enumerate(ranked_list, start=1):
            fingerprint = _hit_fingerprint_key(hit)
            if not fingerprint:
                continue
            scores[fingerprint] = scores.get(fingerprint, 0.0) + 1.0 / (k + rank)
            prev = by_fp.get(fingerprint)
            if prev is None or float(hit.get("score") or 0.0) > float(prev.get("score") or 0.0):
                by_fp[fingerprint] = hit
    ordered = sorted(by_fp.keys(), key=lambda key: scores[key], reverse=True)
    out: list[dict[str, Any]] = []
    for fingerprint in ordered[:top_n]:
        hit = dict(by_fp[fingerprint])
        hit["rrf_score"] = scores[fingerprint]
        out.append(hit)
    return out


def _effective_work_id(work_id: str | None, hits: list[dict[str, Any]]) -> str | None:
    return work_id or (hits[0].get("work_id") if hits else None)
