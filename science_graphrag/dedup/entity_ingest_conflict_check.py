"""Enqueue entity-level near-duplicate review rows during ingest (after graph write)."""

from __future__ import annotations

from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from science_graphrag.dedup.dataset_pipeline import embed_text as embed_dataset
from science_graphrag.dedup.entity_pipeline_common import SIM_QUEUE_MIN, _cosine
from science_graphrag.dedup.fingerprints import make_entity_pair_fingerprint
from science_graphrag.dedup.institution_pipeline import embed_text as embed_institution
from science_graphrag.dedup.method_pipeline import embed_text as embed_method
from science_graphrag.dedup.venue_pipeline import embed_text as embed_venue
from science_graphrag.ingestion.embeddings import HashEmbeddingProvider
from science_graphrag.storage.models_orm import EntityDedupConflict
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.utils.project_logging import get_logger

log = get_logger("dedup.entity_ingest")

_ENTITY_SPECS: list[tuple[str, str, str, Callable[[dict[str, Any]], str]]] = [
    ("institution", "list_work_institutions", "list_workspace_institutions", embed_institution),
    ("venue", "list_work_venues", "list_workspace_venues", embed_venue),
    ("method", "list_work_methods", "list_workspace_methods", embed_method),
    ("dataset", "list_work_datasets", "list_workspace_datasets", embed_dataset),
]


def enqueue_entity_near_duplicate_conflicts_on_ingest(
    *,
    session: Session,
    neo: Neo4jGraphStore,
    workspace_id: str | None,
    new_work_id: str,
    workspace_entity_limit: int = 500,
) -> dict[str, int]:
    """
    Compare entities attached to ``new_work_id`` against other entities in the workspace using
    the same hash-embedding similarity as scan dedup. Always queues human review (no auto-merge).
    Inserts ``EntityDedupConflict`` rows with ``origin='ingest'``. Does not commit the session.
    """

    ws_id = str(workspace_id or "").strip()
    wid = str(new_work_id or "").strip()
    out: dict[str, int] = {"institution": 0, "venue": 0, "method": 0, "dataset": 0}
    if not ws_id or not wid or not session:
        return out

    if not neo.workspace_get(ws_id):
        return out

    embedder = HashEmbeddingProvider()

    for entity_type, work_method, ws_method, embed_text in _ENTITY_SPECS:
        work_rows = getattr(neo, work_method)(wid)
        if not work_rows:
            continue
        new_ids = {
            str(r.get("id") or "").strip() for r in work_rows if str(r.get("id") or "").strip()
        }
        if not new_ids:
            continue

        ws_rows = getattr(neo, ws_method)(ws_id)[: max(2, int(workspace_entity_limit))]
        if len(ws_rows) < 2:
            continue

        existing_fp = set(
            str(x)
            for x in session.scalars(
                select(EntityDedupConflict.fingerprint).where(
                    EntityDedupConflict.entity_type == entity_type
                ),
            ).all()
            if x
        )

        vectors: dict[str, list[float]] = {}
        for row in ws_rows:
            eid = str(row.get("id") or "").strip()
            if not eid:
                continue
            try:
                vectors[eid] = embedder.embed([embed_text(row)])[0]
            except Exception as exc:  # noqa: BLE001
                log.warning("entity_ingest_embed_skip type=%s id=%s: %s", entity_type, eid, exc)
                continue

        ws_entity_ids = list(vectors.keys())
        inserted_here = 0
        pair_seen: set[tuple[str, str]] = set()

        for neid in new_ids:
            if neid not in vectors:
                wr = next((r for r in work_rows if str(r.get("id") or "").strip() == neid), None)
                if not wr:
                    continue
                try:
                    vectors[neid] = embedder.embed([embed_text(wr)])[0]
                except Exception as exc:  # noqa: BLE001
                    log.warning(
                        "entity_ingest_embed_new_skip type=%s id=%s: %s", entity_type, neid, exc
                    )
                    continue

            for oid in ws_entity_ids:
                if oid == neid:
                    continue
                va = vectors.get(neid)
                vb = vectors.get(oid)
                if va is None or vb is None:
                    continue
                sim = _cosine(va, vb)
                if sim < SIM_QUEUE_MIN:
                    continue
                a, b = sorted((neid, oid))
                key = (a, b)
                if key in pair_seen:
                    continue
                pair_seen.add(key)
                fp = make_entity_pair_fingerprint(ws_id, entity_type, a, b)
                if fp in existing_fp:
                    continue
                session.add(
                    EntityDedupConflict(
                        entity_type=entity_type,
                        entity_id_a=a,
                        entity_id_b=b,
                        similarity_score=sim,
                        status="pending",
                        check_mode="embedding",
                        fingerprint=fp,
                        workspace_id=ws_id,
                        origin="ingest",
                    ),
                )
                existing_fp.add(fp)
                inserted_here += 1

        out[entity_type] = inserted_here

    if any(out.values()):
        session.flush()
    return out
