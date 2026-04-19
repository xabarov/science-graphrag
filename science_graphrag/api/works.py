"""UI-facing work listing and detail (Phase 5/6 bridge)."""

from __future__ import annotations

import hashlib
from typing import Any

from neo4j import GraphDatabase, NotificationClassification, Session as Neo4jSession

from science_graphrag.config import Settings
from science_graphrag.ingestion.embeddings import resolve_embedding_dim
from science_graphrag.storage.qdrant_store import QdrantChunkStore


def _neo4j_driver(settings: Settings):
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
        notifications_disabled_classifications=[NotificationClassification.UNRECOGNIZED],
    )


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

    lim = max(1, min(int(neighbor_limit), 2000))
    effective_depth = 1
    if depth != effective_depth:
        pass  # reserved for future multi-hop; still 1-hop today

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
        lim=lim,
    ):
        _append_neighbor_edge(nodes, edges, center_id, rec)

    _enrich_edges_with_display(center_id, nodes, edges)

    truncated = total_neighbors > lim
    expansions: list[str] = []
    if truncated:
        expansions.append("increase_neighbor_limit")
    if effective_depth == 1 and depth > 1:
        expansions.append("multi_hop_depth")

    return {
        "work_id": work_id,
        "nodes": nodes,
        "edges": edges,
        "meta": {
            "semantic_available": bool(row["has_semantic"]),
            "graph_scope": "work_1hop",
            "graph_depth_requested": int(depth),
            "graph_depth_effective": effective_depth,
            "neighbor_match_count": total_neighbors,
            "neighbor_limit_applied": lim,
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

    driver = _neo4j_driver(settings)
    sem = _has_semantic_layer_cypher()
    sem_filter = ""
    if has_semantic is True:
        sem_filter = f"AND ({sem})"
    elif has_semantic is False:
        sem_filter = f"AND NOT ({sem})"
    try:
        with driver.session() as session:
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
        driver.close()


def get_work_detail(settings: Settings, work_id: str) -> dict[str, Any] | None:
    """Single work + authors for GET /v1/works/{work_id}."""

    driver = _neo4j_driver(settings)
    sem = _has_semantic_layer_cypher()
    try:
        with driver.session() as session:
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
            return {
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
    finally:
        driver.close()


def work_graph_neighborhood(
    settings: Settings,
    work_id: str,
    *,
    neighbor_limit: int = 200,
    depth: int = 1,
) -> dict[str, Any] | None:
    """1-hop neighborhood for GET /v1/works/{id}/graph."""

    driver = _neo4j_driver(settings)
    try:
        with driver.session() as session:
            return _work_graph_neighborhood_payload(
                session,
                work_id,
                neighbor_limit=neighbor_limit,
                depth=depth,
            )
    finally:
        driver.close()


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
