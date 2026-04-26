from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import select

from science_graphrag.api.deps import StoreRegistry
from science_graphrag.config import Settings
from science_graphrag.ingestion.artifact_layout import (
    has_extracted_body_file,
    resolve_extracted_body_file,
    strip_ingest_artifact_header,
)
from science_graphrag.storage.db import get_engine, init_db, session_factory
from science_graphrag.storage.models_orm import DocumentRecord

# Hard cap for JSON extracted-body responses (chars after optional header strip).
_MAX_EXTRACTED_BODY_RESPONSE_CHARS = 1_500_000


def _has_semantic_layer_cypher() -> str:
    return (
        "(EXISTS { MATCH (w)-[:USES_METHOD]->(:Method) }) OR "
        "(EXISTS { MATCH (w)-[:EVALUATED_ON]->(:Dataset) })"
    )


def _sql_session_factory(settings: Settings):
    engine = get_engine(settings.database_url)
    init_db(engine)
    return session_factory(engine)


def resolve_document_for_work(
    settings: Settings, stores: StoreRegistry, work_id: str
) -> DocumentRecord | None:
    factory = _sql_session_factory(settings)
    with factory() as session:
        row = session.execute(
            select(DocumentRecord).where(DocumentRecord.work_id == work_id).limit(1),
        ).scalar_one_or_none()
        if row is not None:
            return row
    try:
        batch, _ = stores.qdrant_chunks.scroll_chunks_for_work(
            work_id=work_id, limit=1, offset=None
        )
    except Exception:  # noqa: BLE001
        return None
    if not batch:
        return None
    doc_id = batch[0].get("document_id")
    if not doc_id:
        return None
    with factory() as session:
        return session.get(DocumentRecord, str(doc_id))


def work_pdf_blob_path(settings: Settings, stores: StoreRegistry, work_id: str) -> Path | None:
    doc = resolve_document_for_work(settings, stores, work_id)
    if doc is None:
        return None
    mime = (doc.mime_type or "").lower()
    src = (doc.source_path or "").lower()
    if "pdf" not in mime and not src.endswith(".pdf"):
        return None
    path = stores.blob.path_for_sha(doc.sha256)
    if not path.is_file():
        return None
    return path


def list_works(
    stores: StoreRegistry,
    *,
    q: str | None,
    limit: int,
    offset: int,
    year_min: int | None = None,
    year_max: int | None = None,
    has_semantic: bool | None = None,
) -> tuple[list[dict[str, Any]], int]:
    sem = _has_semantic_layer_cypher()
    sem_filter = ""
    if has_semantic is True:
        sem_filter = f"AND ({sem})"
    elif has_semantic is False:
        sem_filter = f"AND NOT ({sem})"
    with stores.neo4j.session() as session:
        filt = (q or "").strip()
        count_q = (
            """
        MATCH (w:Work)
        WHERE ($needle = '' OR toLower(coalesce(w.title, '')) CONTAINS $needle)
          AND ($y0 IS NULL OR (w.publication_year IS NOT NULL AND w.publication_year >= $y0))
          AND ($y1 IS NULL OR (w.publication_year IS NOT NULL AND w.publication_year <= $y1))
        """
            + sem_filter
            + """
        RETURN count(w) AS total
        """
        )
        total = session.run(count_q, needle=filt.lower(), y0=year_min, y1=year_max).single()[
            "total"
        ]
        rows_q = (
            """
        MATCH (w:Work)
        WHERE ($needle = '' OR toLower(coalesce(w.title, '')) CONTAINS $needle)
          AND ($y0 IS NULL OR (w.publication_year IS NOT NULL AND w.publication_year >= $y0))
          AND ($y1 IS NULL OR (w.publication_year IS NOT NULL AND w.publication_year <= $y1))
        """
            + sem_filter
            + """
        RETURN w.id AS work_id,
               coalesce(w.title, '') AS title,
               w.publication_year AS year,
               w.doi AS doi,
               w.arxiv_id AS arxiv_id,
               w.venue_name AS venue,
               """
            + sem
            + """ AS has_semantic_layer
        ORDER BY title
        SKIP $skip LIMIT $lim
        """
        )
        recs = session.run(
            rows_q, needle=filt.lower(), y0=year_min, y1=year_max, skip=offset, lim=limit
        )
        items = [
            {
                "work_id": rec["work_id"],
                "title": rec["title"] or "",
                "year": rec["year"],
                "doi": rec["doi"],
                "arxiv_id": rec["arxiv_id"],
                "venue": rec["venue"],
                "authors_preview": [],
                "has_semantic_layer": bool(rec["has_semantic_layer"]),
            }
            for rec in recs
        ]
        return items, int(total)


def get_work_detail(
    settings: Settings,
    stores: StoreRegistry,
    work_id: str,
) -> dict[str, Any] | None:
    sem = _has_semantic_layer_cypher()
    with stores.neo4j.session() as session:
        wrec = session.run(
            """
            MATCH (w:Work {id: $id})
            RETURN w,
                   """
            + sem
            + """ AS has_semantic_layer
            """,
            id=work_id,
        ).single()
        if not wrec:
            return None
        node = wrec["w"]
        semantic_ok = bool(wrec["has_semantic_layer"])
        authors = []
        for arec in session.run(
            """
            MATCH (w:Work {id: $id})-[:HAS_AUTHORSHIP]->(ash:Authorship)
            -[:OF_AUTHOR]->(auth:Author)
            OPTIONAL MATCH (ash)-[:AFFILIATED_WITH]->(i:Institution)
            WITH ash, auth, collect(DISTINCT coalesce(i.name, '')) AS insts
            RETURN ash.author_position AS pos,
                   auth.id AS author_id,
                   coalesce(auth.full_name, '') AS name,
                   [x IN insts WHERE x <> ''] AS institutions
            ORDER BY pos
            """,
            id=work_id,
        ):
            authors.append(
                {
                    "author_id": arec["author_id"],
                    "name": arec["name"],
                    "institutions": arec["institutions"] or [],
                }
            )
    out: dict[str, Any] = {
        "work_id": work_id,
        "title": node.get("title") or "",
        "abstract": node.get("abstract"),
        "year": node.get("publication_year"),
        "doi": node.get("doi"),
        "arxiv_id": node.get("arxiv_id"),
        "venue": node.get("venue_name"),
        "authors": authors,
        "ingestion": {
            "document_id": None,
            "has_chunks": False,
            "has_semantic_layer": semantic_ok,
            "has_extracted_body": False,
            "extracted_body_bytes": None,
            "work_provenance": "graph_stub",
        },
    }
    doc_row = resolve_document_for_work(settings, stores, work_id)
    if doc_row is not None:
        out["ingestion"]["document_id"] = doc_row.id
        out["ingestion"]["work_provenance"] = "ingested_document"
        art_root = Path(settings.artifact_root)
        if has_extracted_body_file(art_root, doc_row.id):
            resolved = resolve_extracted_body_file(art_root, doc_row.id)
            out["ingestion"]["has_extracted_body"] = True
            out["ingestion"]["extracted_body_bytes"] = (
                int(resolved[0].stat().st_size) if resolved else None
            )
    return out


def list_work_claims(stores: StoreRegistry, work_id: str) -> list[dict[str, Any]]:
    q = """
    MATCH (w:Work {id: $wid})<-[:ANCHORED_IN]-(e:Evidence)<-[:SUPPORTED_BY]-(c:Claim)
    RETURN c.id AS claim_id,
           coalesce(c.normalized_text, c.text, '') AS normalized_text,
           coalesce(c.claim_type, '') AS claim_type,
           coalesce(c.polarity, '') AS polarity,
           coalesce(c.confidence, 0.0) AS confidence,
           e.chunk_fingerprint AS chunk_fingerprint,
           coalesce(e.quote, '') AS quote,
           e.section_path AS section_path
    ORDER BY claim_id, chunk_fingerprint
    """
    with stores.neo4j.session() as session:
        rows = list(session.run(q, wid=work_id))
    by_claim: dict[str, dict[str, Any]] = {}
    for rec in rows:
        cid = str(rec["claim_id"] or "")
        if not cid:
            continue
        by_claim.setdefault(
            cid,
            {
                "claim_id": cid,
                "normalized_text": str(rec["normalized_text"] or ""),
                "claim_type": str(rec["claim_type"] or ""),
                "polarity": str(rec["polarity"] or ""),
                "confidence": float(rec["confidence"] or 0.0),
                "evidence": [],
            },
        )
        quote = str(rec["quote"] or "").strip()
        if quote:
            by_claim[cid]["evidence"].append(
                {
                    "chunk_fingerprint": str(rec["chunk_fingerprint"] or ""),
                    "quote": quote,
                    "section_path": rec["section_path"],
                }
            )
    return list(by_claim.values())


def work_sources_payload(
    settings: Settings,
    stores: StoreRegistry,
    work_id: str,
) -> dict[str, Any] | None:
    if get_work_detail(settings, stores, work_id) is None:
        return None
    try:
        chunk_total = stores.qdrant_chunks.count_chunks_for_work(work_id=work_id)
    except Exception:  # noqa: BLE001
        chunk_total = 0
    doc = resolve_document_for_work(settings, stores, work_id)
    art_root = Path(settings.artifact_root)
    has_body_file = bool(doc and has_extracted_body_file(art_root, doc.id))
    md_size: int | None = None
    if has_body_file and doc is not None:
        hit = resolve_extracted_body_file(art_root, doc.id)
        if hit:
            md_size = int(hit[0].stat().st_size)
    sources: list[dict[str, Any]] = []
    if doc is not None:
        mime = (doc.mime_type or "").lower()
        src = (doc.source_path or "").lower()
        if "pdf" in mime or src.endswith(".pdf"):
            pdf_path = stores.blob.path_for_sha(doc.sha256)
            sz = int(pdf_path.stat().st_size) if pdf_path.is_file() else 0
            sources.append(
                {
                    "repr": "pdf",
                    "sha256": doc.sha256,
                    "mime_type": doc.mime_type or "application/pdf",
                    "size_bytes": sz,
                    "available": pdf_path.is_file(),
                }
            )
    sources.append(
        {
            "repr": "markdown",
            "sha256": None,
            "mime_type": "text/markdown",
            "size_bytes": md_size,
            "available": has_body_file,
            "indexed_chunks": int(chunk_total),
        },
    )
    return {"work_id": work_id, "sources": sources}


def get_work_extracted_body_payload(
    settings: Settings,
    stores: StoreRegistry,
    work_id: str,
) -> dict[str, Any] | None:
    """JSON body for ``GET /v1/works/{work_id}/extracted-body``; ``None`` if work is unknown."""

    if get_work_detail(settings, stores, work_id) is None:
        return None
    doc = resolve_document_for_work(settings, stores, work_id)
    if doc is None:
        return {
            "available": False,
            "reason": "no_ingested_document",
            "work_id": work_id,
        }
    return read_work_extracted_body_dict(
        settings,
        work_id=work_id,
        document_id=str(doc.id),
        max_chars=_MAX_EXTRACTED_BODY_RESPONSE_CHARS,
    )


def read_work_extracted_body_dict(
    settings: Settings,
    *,
    work_id: str,
    document_id: str,
    max_chars: int,
) -> dict[str, Any]:
    """Load canonical / legacy ingest markdown for API responses."""

    root = Path(settings.artifact_root)
    resolved = resolve_extracted_body_file(root, document_id)
    if not resolved:
        return {
            "available": False,
            "reason": "no_extracted_body",
            "work_id": work_id,
            "document_id": document_id,
        }
    path, source_label = resolved
    raw = path.read_text(encoding="utf-8", errors="replace")
    if source_label in ("article", "article_legacy"):
        text = strip_ingest_artifact_header(raw)
    else:
        text = raw
    truncated = len(text) > max_chars
    if truncated:
        text = text[:max_chars]
    return {
        "available": True,
        "work_id": work_id,
        "document_id": document_id,
        "source": source_label,
        "text": text,
        "truncated": truncated,
        "file_bytes": int(path.stat().st_size),
    }
