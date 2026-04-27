"""Enqueue entity-level near-duplicate review rows during ingest (after graph write)."""

from __future__ import annotations

from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from science_graphrag.config import Settings
from science_graphrag.dedup.dataset_pipeline import embed_text as embed_dataset
from science_graphrag.dedup.entity_pipeline_common import SIM_AUTO_MERGE, SIM_QUEUE_MIN, _cosine
from science_graphrag.dedup.fingerprints import make_entity_pair_fingerprint
from science_graphrag.dedup.institution_pipeline import embed_text as embed_institution
from science_graphrag.dedup.method_ingest_adjudicate import adjudicate_method_pair_llm
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


def _as_float_list(vec: Any) -> list[float]:
    if hasattr(vec, "tolist"):
        return [float(x) for x in vec.tolist()]
    return [float(x) for x in vec]


def _pick_method_keep_drop(neid: str, oid: str, new_ids: set[str]) -> tuple[str, str]:
    """Return (keep_id, drop_id); prefer keeping an existing workspace anchor over the new work."""
    if neid in new_ids and oid not in new_ids:
        return oid, neid
    if oid in new_ids and neid not in new_ids:
        return neid, oid
    return (neid, oid) if neid < oid else (oid, neid)


def _process_method_pairs_on_ingest(
    *,
    session: Session,
    neo: Neo4jGraphStore,
    ws_id: str,
    work_rows: list[dict[str, Any]],
    ws_rows: list[dict[str, Any]],
    workspace_entity_limit: int,
    existing_fp: set[str],
    settings: Settings | None,
) -> tuple[int, int, int]:
    """Returns (conflicts_queued, auto_merged, llm_merged)."""
    embedder = HashEmbeddingProvider()
    new_ids = {str(r.get("id") or "").strip() for r in work_rows if str(r.get("id") or "").strip()}
    if not new_ids:
        return 0, 0, 0

    ws_trim = ws_rows[: max(2, int(workspace_entity_limit))]
    if len(ws_trim) < 2:
        return 0, 0, 0

    vectors: dict[str, list[float]] = {}
    by_id: dict[str, dict[str, Any]] = {}
    for row in ws_trim:
        eid = str(row.get("id") or "").strip()
        if not eid:
            continue
        by_id[eid] = row
        try:
            vectors[eid] = _as_float_list(embedder.embed([embed_method(row)])[0])
        except Exception as exc:  # noqa: BLE001
            log.warning("entity_ingest_embed_skip type=method id=%s: %s", eid, exc)

    for neid in list(new_ids):
        if neid not in vectors:
            wr = next((r for r in work_rows if str(r.get("id") or "").strip() == neid), None)
            if not wr:
                continue
            try:
                vectors[neid] = _as_float_list(embedder.embed([embed_method(wr)])[0])
            except Exception as exc:  # noqa: BLE001
                log.warning("entity_ingest_embed_new_skip type=method id=%s: %s", neid, exc)

    ws_entity_ids = [eid for eid in vectors if eid]
    queued = 0
    auto_merged = 0
    llm_merged = 0
    pair_seen: set[tuple[str, str]] = set()

    for neid in list(new_ids):
        if neid not in vectors:
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
            fp = make_entity_pair_fingerprint(ws_id, "method", a, b)
            if fp in existing_fp:
                continue

            if sim >= SIM_AUTO_MERGE:
                keep, drop = _pick_method_keep_drop(neid, oid, new_ids)
                if neo.merge_method_into_canonical(keep, drop):
                    auto_merged += 1
                    vectors.pop(drop, None)
                    by_id.pop(drop, None)
                    new_ids.discard(drop)
                    if drop in ws_entity_ids:
                        ws_entity_ids = [x for x in ws_entity_ids if x != drop]
                    existing_fp.add(fp)
                continue

            if settings is not None and settings.method_ingest_llm_adjudicate:
                row_a = by_id.get(neid) or next(
                    (r for r in work_rows if str(r.get("id") or "").strip() == neid), {}
                )
                row_b = by_id.get(oid) or {}
                judgment = adjudicate_method_pair_llm(settings, row_a, row_b, sim)
                if judgment is None:
                    session.add(
                        EntityDedupConflict(
                            entity_type="method",
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
                    queued += 1
                    continue
                if judgment.verdict == "same_method":
                    keep, drop = _pick_method_keep_drop(neid, oid, new_ids)
                    if neo.merge_method_into_canonical(keep, drop):
                        llm_merged += 1
                        vectors.pop(drop, None)
                        by_id.pop(drop, None)
                        new_ids.discard(drop)
                        if drop in ws_entity_ids:
                            ws_entity_ids = [x for x in ws_entity_ids if x != drop]
                        existing_fp.add(fp)
                    continue
                if judgment.verdict == "uncertain":
                    session.add(
                        EntityDedupConflict(
                            entity_type="method",
                            entity_id_a=a,
                            entity_id_b=b,
                            similarity_score=sim,
                            status="pending",
                            check_mode="llm_uncertain",
                            fingerprint=fp,
                            workspace_id=ws_id,
                            origin="ingest",
                            llm_same_entity=None,
                            llm_reason=(judgment.reason or "")[:2000],
                        ),
                    )
                    existing_fp.add(fp)
                    queued += 1
                continue

            session.add(
                EntityDedupConflict(
                    entity_type="method",
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
            queued += 1

    return queued, auto_merged, llm_merged


def enqueue_entity_near_duplicate_conflicts_on_ingest(
    *,
    session: Session,
    neo: Neo4jGraphStore,
    workspace_id: str | None,
    new_work_id: str,
    workspace_entity_limit: int = 500,
    settings: Settings | None = None,
) -> dict[str, int]:
    """
    Compare entities attached to ``new_work_id`` against other entities in the workspace.

    For **method**, ``sim >= SIM_AUTO_MERGE`` triggers ``merge_method_into_canonical`` when safe.
    For ``0.80 <= sim < 0.95``, optional LLM adjudication (``method_ingest_llm_adjudicate``) may merge
    or queue with ``check_mode=llm_uncertain``. Other entity types: queue-only (legacy).

    Returns counts under keys ``institution``, ``venue``, ``method``, ``dataset`` (conflicts queued),
    plus ``method_ingest_auto_merged`` and ``method_ingest_llm_merged`` when non-zero merges occur.
    """

    ws_id = str(workspace_id or "").strip()
    wid = str(new_work_id or "").strip()
    out: dict[str, int] = {
        "institution": 0,
        "venue": 0,
        "method": 0,
        "dataset": 0,
        "method_ingest_auto_merged": 0,
        "method_ingest_llm_merged": 0,
    }
    if not ws_id or not wid or not session:
        return out

    if not neo.workspace_get(ws_id):
        return out

    embedder = HashEmbeddingProvider()

    existing_fp = set(
        str(x)
        for x in session.scalars(select(EntityDedupConflict.fingerprint)).all()
        if x
    )

    for entity_type, work_method, ws_method, embed_text in _ENTITY_SPECS:
        work_rows = getattr(neo, work_method)(wid)
        if not work_rows:
            continue
        ws_rows = getattr(neo, ws_method)(ws_id)[: max(2, int(workspace_entity_limit))]
        if len(ws_rows) < 2:
            continue

        if entity_type == "method":
            q, am, lm = _process_method_pairs_on_ingest(
                session=session,
                neo=neo,
                ws_id=ws_id,
                work_rows=work_rows,
                ws_rows=ws_rows,
                workspace_entity_limit=workspace_entity_limit,
                existing_fp=existing_fp,
                settings=settings,
            )
            out["method"] += q
            out["method_ingest_auto_merged"] += am
            out["method_ingest_llm_merged"] += lm
            continue

        new_ids = {
            str(r.get("id") or "").strip() for r in work_rows if str(r.get("id") or "").strip()
        }
        if not new_ids:
            continue

        vectors: dict[str, list[float]] = {}
        for row in ws_rows:
            eid = str(row.get("id") or "").strip()
            if not eid:
                continue
            try:
                vectors[eid] = _as_float_list(embedder.embed([embed_text(row)])[0])
            except Exception as exc:  # noqa: BLE001
                log.warning("entity_ingest_embed_skip type=%s id=%s: %s", entity_type, eid, exc)

        ws_entity_ids = list(vectors.keys())
        inserted_here = 0
        pair_seen: set[tuple[str, str]] = set()

        for neid in new_ids:
            if neid not in vectors:
                wr = next((r for r in work_rows if str(r.get("id") or "").strip() == neid), None)
                if not wr:
                    continue
                try:
                    vectors[neid] = _as_float_list(embedder.embed([embed_text(wr)])[0])
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

    if any(out[k] for k in ("institution", "venue", "method", "dataset")):
        session.flush()
    return out
