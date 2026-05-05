"""Intra-document consolidation of extracted Method mentions (ADR 023)."""

from __future__ import annotations

import re

from science_graphrag.dedup.entity_pipeline_common import _cosine
from science_graphrag.dedup.method_pipeline import embed_text as _embed_method_text
from science_graphrag.domain.semantic_models import SemanticEvidenceV1, SemanticMethodV1
from science_graphrag.ingestion.embeddings import HashEmbeddingProvider

# Slightly below auto-merge (0.95) to merge acronym / near-duplicate mentions in one paper.
_INTRA_DOC_SIM = 0.92


def _norm_surface(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _surface_tokens(m: SemanticMethodV1) -> set[str]:
    names: set[str] = set()
    if (m.name or "").strip():
        names.add(_norm_surface(m.name))
    for a in m.aliases or []:
        t = _norm_surface(str(a))
        if t:
            names.add(t)
    names.discard("")
    return names


def _methods_surface_overlap(a: SemanticMethodV1, b: SemanticMethodV1) -> bool:
    """True when primary names or aliases share the same normalized surface."""
    return bool(_surface_tokens(a) & _surface_tokens(b))


def _method_row_dict(m: SemanticMethodV1) -> dict:
    plain = (m.description_plaintext or "").strip()
    md = (m.description_markdown or "").strip()
    return {
        "name": m.name,
        "normalized_name": (m.name or "").strip().lower(),
        "aliases": list(m.aliases or []),
        "description_short": (m.description_short or "").strip(),
        "description_markdown": md or plain,
    }


def _embed_method_row(embedder: HashEmbeddingProvider, m: SemanticMethodV1) -> list[float]:
    row = embedder.embed([_embed_method_text(_method_row_dict(m))])[0]
    return [float(x) for x in row]


def _merge_two_methods(a: SemanticMethodV1, b: SemanticMethodV1) -> SemanticMethodV1:
    """Pick canonical surface name and union evidence/aliases."""
    a_name = (a.name or "").strip()
    b_name = (b.name or "").strip()
    if len(b_name) > len(a_name) and b.confidence >= a.confidence - 1e-6:
        primary, secondary = b, a
    elif len(a_name) >= len(b_name):
        primary, secondary = a, b
    else:
        primary, secondary = a, b

    alias_set: set[str] = set()
    for x in (primary.aliases or []) + (secondary.aliases or []):
        t = str(x).strip()
        if t and t not in (primary.name, secondary.name):
            alias_set.add(t)
    for nm in (secondary.name,):
        t = str(nm).strip()
        if t and t != primary.name:
            alias_set.add(t)

    ev: list[SemanticEvidenceV1] = []
    seen: set[tuple[str | None, str | None, str | None]] = set()
    for item in (primary.evidence or []) + (secondary.evidence or []):
        key = (item.chunk_id, item.section_heading, (item.quote or "")[:80])
        if key in seen:
            continue
        seen.add(key)
        ev.append(item)
        if len(ev) >= 24:
            break

    def _pick_longer(x: str | None, y: str | None) -> str | None:
        xs = (x or "").strip()
        ys = (y or "").strip()
        if len(ys) > len(xs):
            return ys or None
        return xs or ys or None

    ds = _pick_longer(primary.description_short, secondary.description_short)
    dm = _pick_longer(primary.description_markdown, secondary.description_markdown)
    dp = _pick_longer(primary.description_plaintext, secondary.description_plaintext)
    mk = primary.method_kind or secondary.method_kind
    src = primary.description_source or secondary.description_source
    pc = primary.description_confidence
    sc = secondary.description_confidence
    if pc is not None or sc is not None:
        dconf: float | None = max(float(pc or 0.0), float(sc or 0.0))
    elif dm or ds:
        dconf = max(primary.confidence, secondary.confidence)
    else:
        dconf = None

    return SemanticMethodV1(
        name=primary.name,
        aliases=sorted(alias_set)[:40],
        description_short=ds,
        description_markdown=dm,
        description_plaintext=dp,
        method_kind=mk,
        description_source=src,
        description_confidence=dconf,
        confidence=max(primary.confidence, secondary.confidence),
        evidence=ev,
    )


def consolidate_document_methods(methods: list[SemanticMethodV1]) -> list[SemanticMethodV1]:
    """Cluster highly similar methods inside one extraction using hash embeddings."""
    if len(methods) <= 1:
        return methods
    embedder = HashEmbeddingProvider()
    vectors: list[list[float]] = []
    for m in methods:
        try:
            vectors.append(_embed_method_row(embedder, m))
        except (TypeError, ValueError, IndexError, AttributeError, RuntimeError):
            vectors.append([0.0] * 384)

    n = len(methods)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[rj] = ri

    for i in range(n):
        for j in range(i + 1, n):
            if _methods_surface_overlap(methods[i], methods[j]):
                union(i, j)

    for i in range(n):
        for j in range(i + 1, n):
            if _cosine(vectors[i], vectors[j]) >= _INTRA_DOC_SIM:
                union(i, j)

    clusters: dict[int, list[int]] = {}
    for i in range(n):
        r = find(i)
        clusters.setdefault(r, []).append(i)

    out: list[SemanticMethodV1] = []
    for _root, idxs in clusters.items():
        merged = methods[idxs[0]]
        for k in idxs[1:]:
            merged = _merge_two_methods(merged, methods[k])
        out.append(merged)
    return out
