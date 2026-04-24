"""UI-facing work listing and detail (Phase 5/6 bridge)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from neo4j import Session as Neo4jSession
from sqlalchemy import select

from science_graphrag.config import Settings
from science_graphrag.ingestion.embeddings import resolve_embedding_dim
from science_graphrag.storage.blobs import BlobStore
from science_graphrag.storage.db import get_engine, init_db, session_factory
from science_graphrag.storage.models_orm import DocumentRecord
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.storage.qdrant_store import QdrantChunkStore


def _store(settings: Settings) -> Neo4jGraphStore:
    return Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)


def _vector_dim(settings: Settings) -> int:
    return resolve_embedding_dim(embedding_model=settings.embedding_model)


def _has_semantic_layer_cypher() -> str:
    return (
        "(EXISTS { MATCH (w)-[:USES_METHOD]->(:Method) }) OR "
        "(EXISTS { MATCH (w)-[:EVALUATED_ON]->(:Dataset) })"
    )


def _neighborhood_edge_endpoints(
    center_id: str, neighbor_id: str, raw_src: str, raw_tgt: str
) -> tuple[str, str]:
    """Resolve directed edge ends; fallback to center→neighbor if data is inconsistent."""
    endpoints = {center_id, neighbor_id}
    if (
        raw_src
        and raw_tgt
        and raw_src != raw_tgt
        and {raw_src, raw_tgt} == endpoints
    ):
        return raw_src, raw_tgt
    return center_id, neighbor_id


def _stable_edge_id(source: str, rel_type: str, target: str, seq: int) -> str:
    """Deterministic edge id for UI selection and URL sync (not Neo4j internal id)."""
    payload = f"{source}\0{rel_type or ''}\0{target}\0{seq}".encode()
    return "e_" + hashlib.sha256(payload).hexdigest()[:22]


def _display_type(rel_type: str) -> str:
    t = (rel_type or "").strip()
    return t.replace("_", " ") if t else "related"


def _neighbor_subtitle_and_properties(ntype: str, rec: Any) -> tuple[str, dict[str, Any]]:
    """Human subtitle line + small property bag for inspector UI."""
    props: dict[str, Any] = {}
    pub = rec.get("n_pub_year")
    if pub is not None:
        props["publication_year"] = pub
    ndoi = rec.get("n_doi")
    if ndoi:
        s = str(ndoi).strip()
        if s:
            props["doi"] = s
    narx = rec.get("n_arxiv")
    if narx:
        s = str(narx).strip()
        if s:
            props["arxiv_id"] = s
    nvenue = rec.get("n_venue")
    if nvenue:
        s = str(nvenue).strip()
        if s:
            props["venue"] = s[:200]

    if ntype == "Work" and pub is not None:
        subtitle = f"Work · {int(pub)}"
    elif ntype == "Work":
        subtitle = "Work"
    elif ntype in ("Method", "Dataset", "Author", "Institution", "Authorship"):
        subtitle = ntype
    else:
        subtitle = str(ntype) if ntype else "Node"
    return subtitle, props


def _append_neighbor_edge(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    center_id: str,
    rec: Any,
) -> None:
    """Add neighbor node (if new) and one directed edge from a Neo4j neighborhood row."""
    labs = rec["labs"] or []
    ntype = str(labs[0]) if labs else "Node"
    nid = str(rec["nid"])
    raw_label = str(rec.get("nlabel") or "").strip()
    disp = (raw_label or nid)[:200]
    subtitle, props = _neighbor_subtitle_and_properties(ntype, rec)
    if not any(x["id"] == nid for x in nodes):
        nodes.append(
            {
                "id": nid,
                "type": ntype,
                "label": disp,
                "display_label": disp,
                "subtitle": subtitle,
                "node_kind": ntype,
                "properties": props,
            },
        )
    raw_src = str(rec.get("src_id") or "").strip()
    raw_tgt = str(rec.get("tgt_id") or "").strip()
    src_id, tgt_id = _neighborhood_edge_endpoints(center_id, nid, raw_src, raw_tgt)
    edges.append(
        {
            "source": src_id,
            "target": tgt_id,
            "type": rec["rt"] or "",
        },
    )


def _enrich_edges_with_display(
    center_id: str,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> None:
    by_id = {n["id"]: n for n in nodes}
    for seq, edge in enumerate(edges):
        src_id = str(edge.get("source") or "")
        tgt_id = str(edge.get("target") or "")
        src_n = by_id.get(src_id, {})
        tgt_n = by_id.get(tgt_id, {})
        sl = str(src_n.get("display_label") or src_n.get("label") or src_id)
        tl = str(tgt_n.get("display_label") or tgt_n.get("label") or tgt_id)
        rt = str(edge.get("type") or "")
        disp_t = _display_type(rt)
        edge["id"] = str(edge.get("id") or "").strip() or _stable_edge_id(src_id, rt, tgt_id, seq)
        edge["display_type"] = disp_t
        edge["source_label"] = sl
        edge["target_label"] = tl
        edge["summary"] = f"{sl} —[{disp_t}]→ {tl}"
        if src_id == center_id:
            edge["direction"] = "outgoing"
        elif tgt_id == center_id:
            edge["direction"] = "incoming"
        else:
            edge["direction"] = "lateral"


MAX_WORK_GRAPH_NEIGHBORS = 300


def _work_graph_neighborhood_payload(
    session: Neo4jSession,
    work_id: str,
    *,
    neighbor_limit: int = 200,
    depth: int = 1,
) -> dict[str, Any] | None:
    sem = _has_semantic_layer_cypher()
    row = session.run(
        """
        MATCH (w:Work {id: $id})
        RETURN w.id AS wid,
               coalesce(w.title, '') AS wtitle,
               w.publication_year AS wyear,
               coalesce(w.doi, '') AS wdoi,
               coalesce(w.arxiv_id, '') AS warxiv,
               coalesce(w.venue_name, '') AS wvenue,
               """
        + sem
        + """ AS has_semantic
        """,
        id=work_id,
    ).single()
    if not row:
        return None
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    center_id = str(row["wid"])
    raw_title = str(row.get("wtitle") or "").strip()
    center_label = raw_title[:200] if raw_title else center_id
    wyear = row.get("wyear")
    center_props: dict[str, Any] = {}
    if wyear is not None:
        center_props["publication_year"] = wyear
    wdoi = str(row.get("wdoi") or "").strip()
    if wdoi:
        center_props["doi"] = wdoi
    warxiv = str(row.get("warxiv") or "").strip()
    if warxiv:
        center_props["arxiv_id"] = warxiv
    wvenue = str(row.get("wvenue") or "").strip()
    if wvenue:
        center_props["venue"] = wvenue[:200]
    center_sub = "Work"
    if wyear is not None:
        center_sub = f"Work · {int(wyear)}"

    nodes.append(
        {
            "id": center_id,
            "type": "Work",
            "label": center_label,
            "display_label": center_label,
            "subtitle": center_sub,
            "node_kind": "Work",
            "properties": center_props,
            "distance": 0,
        },
    )

    total_neighbors = int(
        session.run(
            """
            MATCH (w:Work {id: $id})-[r]-(n)
            RETURN count(r) AS c
            """,
            id=work_id,
        ).single()["c"],
    )

    depth_req = max(1, min(int(depth), 3))
    cap = min(MAX_WORK_GRAPH_NEIGHBORS, max(1, min(int(neighbor_limit), 2000)))
    if depth_req <= 1:
        hop1_lim = cap
        hop2_lim = 0
        effective_depth = 1
    else:
        hop1_lim = max(1, (cap * 2) // 3)
        hop2_lim = max(1, cap - hop1_lim)
        effective_depth = 2

    for rec in session.run(
        """
        MATCH (w:Work {id: $id})-[r]-(n)
        RETURN coalesce(n.id, toString(elementId(n))) AS nid,
               labels(n) AS labs,
               type(r) AS rt,
               coalesce(n.name, n.full_name, n.title, '') AS nlabel,
               coalesce(startNode(r).id, toString(elementId(startNode(r)))) AS src_id,
               coalesce(endNode(r).id, toString(elementId(endNode(r)))) AS tgt_id,
               n.publication_year AS n_pub_year,
               coalesce(n.doi, '') AS n_doi,
               coalesce(n.arxiv_id, '') AS n_arxiv,
               coalesce(n.venue_name, '') AS n_venue
        LIMIT $lim
        """,
        id=work_id,
        lim=hop1_lim,
    ):
        _append_neighbor_edge(nodes, edges, center_id, rec)

    for n in nodes[1:]:
        if "distance" not in n:
            n["distance"] = 1

    if effective_depth >= 2 and hop2_lim > 0:
        hop1_work_ids = [
            str(n["id"])
            for n in nodes
            if str(n.get("type") or "") == "Work" and str(n.get("id") or "") != center_id
        ][:30]
        h1_ids = [str(n["id"]) for n in nodes]
        if hop1_work_ids:
            for rec in session.run(
                """
                UNWIND $h1 AS wid
                MATCH (w:Work {id: wid})-[r:CITES]-(n:Work)
                WHERE n.id <> $center AND NOT n.id IN $h1set
                RETURN coalesce(n.id, toString(elementId(n))) AS nid,
                       labels(n) AS labs,
                       type(r) AS rt,
                       coalesce(n.name, n.full_name, n.title, '') AS nlabel,
                       coalesce(startNode(r).id, toString(elementId(startNode(r)))) AS src_id,
                       coalesce(endNode(r).id, toString(elementId(endNode(r)))) AS tgt_id,
                       n.publication_year AS n_pub_year,
                       coalesce(n.doi, '') AS n_doi,
                       coalesce(n.arxiv_id, '') AS n_arxiv,
                       coalesce(n.venue_name, '') AS n_venue
                LIMIT $lim2
                """,
                h1=hop1_work_ids,
                center=center_id,
                h1set=h1_ids,
                lim2=hop2_lim,
            ):
                nid = str(rec["nid"] or "")
                if not nid or any(x["id"] == nid for x in nodes):
                    continue
                _append_neighbor_edge(nodes, edges, center_id, rec)
                for n in nodes:
                    if n.get("id") == nid:
                        n["distance"] = 2
                        break

    _enrich_edges_with_display(center_id, nodes, edges)

    truncated = total_neighbors > hop1_lim
    expansions: list[str] = []
    if truncated:
        expansions.append("increase_neighbor_limit")
    if depth_req > effective_depth:
        expansions.append("multi_hop_depth")

    graph_scope = "work_2hop" if effective_depth >= 2 else "work_1hop"

    return {
        "work_id": work_id,
        "nodes": nodes,
        "edges": edges,
        "meta": {
            "semantic_available": bool(row["has_semantic"]),
            "graph_scope": graph_scope,
            "graph_depth_requested": int(depth),
            "graph_depth_effective": effective_depth,
            "neighbor_match_count": total_neighbors,
            "neighbor_limit_applied": hop1_lim + (hop2_lim if effective_depth >= 2 else 0),
            "nodes_returned": len(nodes),
            "edges_returned": len(edges),
            "is_truncated": truncated,
            "available_expansions": expansions,
        },
    }


def list_works(
    settings: Settings,
    *,
    q: str | None,
    limit: int,
    offset: int,
    year_min: int | None = None,
    year_max: int | None = None,
    has_semantic: bool | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Return work rows and total count for GET /v1/works."""

    store = _store(settings)
    sem = _has_semantic_layer_cypher()
    sem_filter = ""
    if has_semantic is True:
        sem_filter = f"AND ({sem})"
    elif has_semantic is False:
        sem_filter = f"AND NOT ({sem})"
    try:
        with store.session() as session:
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
            total = session.run(
                count_q,
                needle=filt.lower(),
                y0=year_min,
                y1=year_max,
            ).single()["total"]

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
                rows_q,
                needle=filt.lower(),
                y0=year_min,
                y1=year_max,
                skip=offset,
                lim=limit,
            )
            items: list[dict[str, Any]] = []
            for rec in recs:
                items.append(
                    {
                        "work_id": rec["work_id"],
                        "title": rec["title"] or "",
                        "year": rec["year"],
                        "doi": rec["doi"],
                        "arxiv_id": rec["arxiv_id"],
                        "venue": rec["venue"],
                        "authors_preview": [],
                        "has_semantic_layer": bool(rec["has_semantic_layer"]),
                    },
                )
            return items, int(total)
    finally:
        store.close()


def _sql_session_factory(settings: Settings):
    engine = get_engine(settings.database_url)
    init_db(engine)
    return session_factory(engine)


def resolve_document_for_work(settings: Settings, work_id: str) -> DocumentRecord | None:
    """Postgres ``documents`` row for a work (``work_id`` column or Qdrant ``document_id`` fallback)."""

    factory = _sql_session_factory(settings)
    with factory() as session:
        row = session.execute(
            select(DocumentRecord).where(DocumentRecord.work_id == work_id).limit(1),
        ).scalar_one_or_none()
        if row is not None:
            return row
    dim = _vector_dim(settings)
    qstore = QdrantChunkStore(settings.qdrant_url, settings.qdrant_collection, vector_dim=dim)
    try:
        batch, _ = qstore.scroll_chunks_for_work(work_id=work_id, limit=1, offset=None)
    except Exception:  # noqa: BLE001
        return None
    if not batch:
        return None
    doc_id = batch[0].get("document_id")
    if not doc_id:
        return None
    with factory() as session:
        return session.get(DocumentRecord, str(doc_id))


def work_pdf_blob_path(settings: Settings, work_id: str) -> Path | None:
    """Path to raw PDF in ``BlobStore`` if this work was ingested from a PDF and blob exists."""

    doc = resolve_document_for_work(settings, work_id)
    if doc is None:
        return None
    mime = (doc.mime_type or "").lower()
    src = (doc.source_path or "").lower()
    if "pdf" not in mime and not src.endswith(".pdf"):
        return None
    blob = BlobStore(settings.blob_root)
    path = blob.path_for_sha(doc.sha256)
    if not path.is_file():
        return None
    return path


def work_sources_payload(settings: Settings, work_id: str) -> dict[str, Any] | None:
    """Inventory for ``GET /v1/works/{id}/sources`` (PDF blob + markdown chunks)."""

    if get_work_detail(settings, work_id) is None:
        return None
    dim = _vector_dim(settings)
    qstore = QdrantChunkStore(settings.qdrant_url, settings.qdrant_collection, vector_dim=dim)
    try:
        chunk_total = qstore.count_chunks_for_work(work_id=work_id)
    except Exception:  # noqa: BLE001
        chunk_total = 0
    doc = resolve_document_for_work(settings, work_id)
    sources: list[dict[str, Any]] = []
    pdf_path: Path | None = None
    if doc is not None:
        mime = (doc.mime_type or "").lower()
        src = (doc.source_path or "").lower()
        if "pdf" in mime or src.endswith(".pdf"):
            blob = BlobStore(settings.blob_root)
            pdf_path = blob.path_for_sha(doc.sha256)
            sz = int(pdf_path.stat().st_size) if pdf_path.is_file() else 0
            sources.append(
                {
                    "repr": "pdf",
                    "sha256": doc.sha256,
                    "mime_type": doc.mime_type or "application/pdf",
                    "size_bytes": sz,
                    "available": pdf_path.is_file(),
                },
            )
    sources.append(
        {
            "repr": "markdown",
            "sha256": None,
            "mime_type": "text/markdown",
            "size_bytes": None,
            "available": chunk_total > 0,
        },
    )
    return {"work_id": work_id, "sources": sources}


def get_work_detail(settings: Settings, work_id: str) -> dict[str, Any] | None:
    """Single work + authors for GET /v1/works/{work_id}."""

    store = _store(settings)
    sem = _has_semantic_layer_cypher()
    try:
        with store.session() as session:
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
            authors: list[dict[str, Any]] = []
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
                    },
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
                    "document_id": work_id,
                    "has_chunks": False,
                    "has_semantic_layer": semantic_ok,
                },
            }
            doc_row = resolve_document_for_work(settings, work_id)
            if doc_row is not None:
                out["ingestion"]["document_id"] = doc_row.id
            return out
    finally:
        store.close()


def work_graph_neighborhood(
    settings: Settings,
    work_id: str,
    *,
    neighbor_limit: int = 200,
    depth: int = 1,
) -> dict[str, Any] | None:
    """1-hop neighborhood for GET /v1/works/{id}/graph."""

    store = _store(settings)
    try:
        with store.session() as session:
            return _work_graph_neighborhood_payload(
                session,
                work_id,
                neighbor_limit=neighbor_limit,
                depth=depth,
            )
    finally:
        store.close()


def list_work_claims(settings: Settings, work_id: str) -> list[dict[str, Any]] | None:
    """Return claims + evidence for ``GET /v1/works/{id}/claims`` (Neo4j)."""

    if get_work_detail(settings, work_id) is None:
        return None
    store = _store(settings)
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
    try:
        with store.session() as session:
            rows = list(session.run(q, wid=work_id))
    finally:
        store.close()
    by_claim: dict[str, dict[str, Any]] = {}
    for rec in rows:
        cid = str(rec["claim_id"] or "")
        if not cid:
            continue
        if cid not in by_claim:
            by_claim[cid] = {
                "claim_id": cid,
                "normalized_text": str(rec["normalized_text"] or ""),
                "claim_type": str(rec["claim_type"] or ""),
                "polarity": str(rec["polarity"] or ""),
                "confidence": float(rec["confidence"] or 0.0),
                "evidence": [],
            }
        quote = str(rec["quote"] or "").strip()
        if not quote:
            continue
        by_claim[cid]["evidence"].append(
            {
                "chunk_fingerprint": str(rec["chunk_fingerprint"] or ""),
                "quote": quote,
                "section_path": rec["section_path"],
            },
        )
    return list(by_claim.values())


def work_chunks(
    settings: Settings,
    work_id: str,
    *,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    """Chunks for GET /v1/works/{id}/chunks (Qdrant)."""

    dim = _vector_dim(settings)
    store = QdrantChunkStore(settings.qdrant_url, settings.qdrant_collection, vector_dim=dim)
    try:
        total = store.count_chunks_for_work(work_id=work_id)
    except Exception:  # noqa: BLE001
        return {
            "items": [],
            "total": 0,
            "error": "qdrant_unavailable",
        }

    accumulated: list[dict[str, Any]] = []
    scroll_offset: int | str | None = None
    cap = min(offset + limit + 100, 5000)
    while len(accumulated) < cap:
        batch, scroll_offset = store.scroll_chunks_for_work(
            work_id=work_id,
            limit=min(200, cap - len(accumulated)),
            offset=scroll_offset,
        )
        accumulated.extend(batch)
        if scroll_offset is None or not batch:
            break

    slice_rows = accumulated[offset : offset + limit]
    items = [
        {
            "document_id": row.get("document_id"),
            "chunk_fingerprint": row.get("chunk_fingerprint"),
            "section_path": row.get("section_path"),
            "text": (row.get("text") or "")[:8000],
            "order": offset + i,
        }
        for i, row in enumerate(slice_rows)
    ]
    doc_id = items[0]["document_id"] if items else None
    return {"items": items, "total": total, "document_id": doc_id}
