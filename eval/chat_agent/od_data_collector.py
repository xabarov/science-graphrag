"""Shared Neo4j + Qdrant + Postgres snapshot for rich OD workspace manifest and gap audits."""

from __future__ import annotations

import os
from collections import defaultdict
from typing import Any

from sqlalchemy import select

from eval.chat_agent.workspace_audit import audit_workspace_readiness
from science_graphrag.ingestion.checkpoint import parse_checkpoint
from science_graphrag.storage.db import get_engine, session_factory
from science_graphrag.storage.models_orm import DocumentRecord

OD_MANIFEST_SCHEMA_VERSION = 1


def qdrant_chunks_collection_name(settings: Any) -> str:
    """
    Resolve Qdrant chunks collection name.

    Same rule as ``scripts/backfill_workspace_claims._resolve_qdrant_chunks_collection``.
    """
    name = getattr(settings, "qdrant_chunks_collection", None) or getattr(
        settings, "qdrant_collection", None
    )
    return str(name or "chunks").strip() or "chunks"


def _neo4j_count_claims(neo: Any, work_id: str) -> int:
    q = """
    MATCH (w:Work {id: $wid})<-[:ANCHORED_IN]-(:Evidence)<-[:SUPPORTED_BY]-(c:Claim)
    RETURN count(DISTINCT c) AS n
    """
    with neo.session() as session:
        rec = session.run(q, wid=work_id).single()
    return int(rec["n"]) if rec else 0


def _neo4j_count_methods(neo: Any, work_id: str) -> int:
    q = """
    MATCH (w:Work {id: $wid})-[:USES_METHOD]->(m:Method)
    RETURN count(DISTINCT m) AS n
    """
    with neo.session() as session:
        rec = session.run(q, wid=work_id).single()
    return int(rec["n"]) if rec else 0


def _neo4j_work_title(neo: Any, work_id: str) -> str | None:
    q = "MATCH (w:Work {id: $wid}) RETURN coalesce(w.title, '') AS t LIMIT 1"
    with neo.session() as session:
        rec = session.run(q, wid=work_id).single()
    if not rec:
        return None
    t = str(rec["t"] or "").strip()
    return t or None


def _normalize_path_key(path: str) -> str:
    return os.path.normpath(str(path or "").strip())


def fetch_documents_by_work_ids(
    *, database_url: str, work_ids: list[str]
) -> dict[str, list[dict[str, Any]]]:
    """Return ``work_id`` -> list of document rows (id, source_path, raw checkpoint JSON)."""
    if not work_ids:
        return {}
    engine = get_engine(database_url)
    fac = session_factory(engine)
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with fac() as session:
        stmt = select(DocumentRecord).where(DocumentRecord.work_id.in_(work_ids))
        for row in session.scalars(stmt):
            wid = str(row.work_id or "").strip()
            if not wid:
                continue
            raw_ck = row.ingest_checkpoint_json
            out[wid].append(
                {
                    "document_id": str(row.id),
                    "source_path": str(row.source_path or ""),
                    "ingest_checkpoint_json": raw_ck,
                    "checkpoint": parse_checkpoint(raw_ck),
                },
            )
    return dict(out)


def _enrich_single_work_report(
    base_row: dict[str, Any],
    *,
    neo: Any,
    claims_store: Any,
    docs_by_work: dict[str, list[dict[str, Any]]],
) -> dict[str, Any] | None:
    """Merge baseline readiness row with OD-specific Neo4j/Qdrant/Postgres fields."""
    wid = str(base_row.get("work_id") or "").strip()
    if not wid:
        return None
    exists = bool(base_row.get("neo4j_work_exists"))
    neo_claims = _neo4j_count_claims(neo, wid) if exists else 0
    neo_methods = _neo4j_count_methods(neo, wid) if exists else 0
    title = _neo4j_work_title(neo, wid) if exists else None
    q_claims = int(claims_store.count_points_for_work(work_id=wid)) if exists else 0

    doc_rows = docs_by_work.get(wid, [])
    document_ids = sorted({str(d["document_id"]) for d in doc_rows})
    source_paths = sorted(
        {str(d["source_path"]) for d in doc_rows if str(d.get("source_path") or "").strip()}
    )

    flags = list(base_row.get("flags") or [])
    if exists and neo_claims == 0:
        flags.append("no_neo4j_claims")
    if exists and q_claims == 0 and neo_claims > 0:
        flags.append("neo_claims_without_qdrant_vectors")
    if exists and neo_claims > 0 and q_claims > 0 and neo_claims != q_claims:
        flags.append("neo_qdrant_claim_count_mismatch")

    return {
        **base_row,
        "work_title": title,
        "document_ids": document_ids,
        "source_paths": source_paths,
        "documents": doc_rows,
        "neo4j_claim_count": neo_claims,
        "neo4j_method_count": neo_methods,
        "qdrant_claim_vector_count": q_claims,
        "flags": flags,
    }


def collect_od_workspace_work_reports(
    *,
    workspace_id: str,
    stores: Any,
    settings: Any,
) -> dict[str, Any]:
    """
    Build extended per-work rows for a materialized OD workspace.

    Combines ``audit_workspace_readiness`` with Neo4j claims/methods/title, Qdrant claim counts,
    and Postgres ``documents`` rows (including parsed ingest checkpoint).
    """
    base = audit_workspace_readiness(workspace_id=workspace_id, stores=stores)
    neo = stores.neo4j
    claims_store = stores.qdrant_claims

    work_ids = [str(x) for x in (base.get("work_ids") or []) if str(x).strip()]
    docs_by_work = fetch_documents_by_work_ids(
        database_url=settings.database_url, work_ids=work_ids
    )

    work_reports: list[dict[str, Any]] = []
    for row in base.get("work_reports") or []:
        if not isinstance(row, dict):
            continue
        extended = _enrich_single_work_report(
            row,
            neo=neo,
            claims_store=claims_store,
            docs_by_work=docs_by_work,
        )
        if extended:
            work_reports.append(extended)

    return {
        **base,
        "work_reports": work_reports,
        "qdrant_chunks_collection": qdrant_chunks_collection_name(settings),
        "qdrant_claims_collection": str(settings.qdrant_claims_collection),
        "claims_extraction_enabled": bool(getattr(settings, "claims_extraction_enabled", True)),
    }
