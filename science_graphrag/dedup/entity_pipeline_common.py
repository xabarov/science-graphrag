from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from science_graphrag.dedup.fingerprints import make_entity_pair_fingerprint
from science_graphrag.ingestion.embeddings import HashEmbeddingProvider
from science_graphrag.storage.models_orm import EntityDedupConflict

SIM_AUTO_MERGE = 0.95
SIM_QUEUE_MIN = 0.80


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def run_entity_scan(
    *,
    entity_type: str,
    entities: list[dict[str, Any]],
    embed_text: Callable[[dict[str, Any]], str],
    db_session: Session,
    merge_pair: Callable[[str, str], bool],
    workspace_id: str | None = None,
    limit: int = 500,
    conflict_origin: str = "scan",
) -> dict[str, int]:
    """Generic pairwise dedup pass for one entity type."""
    if len(entities) < 2:
        return {"queued": 0, "auto_merged": 0, "skipped": 0}

    embedder = HashEmbeddingProvider()
    rows = entities[: max(2, int(limit))]
    vectors: dict[str, list[float]] = {}
    for row in rows:
        eid = str(row.get("id") or "").strip()
        if not eid:
            continue
        text = embed_text(row)
        vectors[eid] = embedder.embed([text])[0]

    ids = list(vectors.keys())
    if len(ids) < 2:
        return {"queued": 0, "auto_merged": 0, "skipped": 0}

    existing = db_session.scalars(
        select(EntityDedupConflict.fingerprint).where(
            EntityDedupConflict.entity_type == entity_type
        ),
    ).all()
    existing_fp = {str(x) for x in existing if x}

    queued = 0
    auto_merged = 0
    skipped = 0
    for i, a in enumerate(ids):
        for b in ids[i + 1 :]:
            sim = _cosine(vectors[a], vectors[b])
            if sim < SIM_QUEUE_MIN:
                skipped += 1
                continue
            if sim >= SIM_AUTO_MERGE:
                auto_merged += 1 if merge_pair(a, b) else 0
                continue

            fp = make_entity_pair_fingerprint(workspace_id, entity_type, a, b)
            if fp in existing_fp:
                continue
            db_session.add(
                EntityDedupConflict(
                    entity_type=entity_type,
                    entity_id_a=a,
                    entity_id_b=b,
                    similarity_score=sim,
                    status="pending",
                    check_mode="embedding",
                    fingerprint=fp,
                    workspace_id=workspace_id,
                    origin=str(conflict_origin or "scan").strip() or "scan",
                ),
            )
            existing_fp.add(fp)
            queued += 1

    db_session.commit()
    return {"queued": queued, "auto_merged": auto_merged, "skipped": skipped}
