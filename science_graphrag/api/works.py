"""UI-facing work listing and detail (Phase 5/6 bridge)."""

from __future__ import annotations

from typing import Any

from neo4j import GraphDatabase, NotificationClassification

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


def list_works(
    settings: Settings,
    *,
    q: str | None,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    """Return work rows and total count for GET /v1/works."""

    driver = _neo4j_driver(settings)
    sem = _has_semantic_layer_cypher()
    try:
        with driver.session() as session:
            filt = (q or "").strip()
            count_q = """
            MATCH (w:Work)
            WHERE $needle = '' OR toLower(coalesce(w.title, '')) CONTAINS $needle
            RETURN count(w) AS total
            """
            total = session.run(
                count_q,
                needle=filt.lower(),
            ).single()["total"]

            rows_q = (
                """
            MATCH (w:Work)
            WHERE $needle = '' OR toLower(coalesce(w.title, '')) CONTAINS $needle
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
            recs = session.run(rows_q, needle=filt.lower(), skip=offset, lim=limit)
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


def work_graph_neighborhood(settings: Settings, work_id: str) -> dict[str, Any] | None:
    """1-hop neighborhood for GET /v1/works/{id}/graph."""

    driver = _neo4j_driver(settings)
    sem = _has_semantic_layer_cypher()
    try:
        with driver.session() as session:
            row = session.run(
                """
                MATCH (w:Work {id: $id})
                RETURN w.id AS wid,
                       coalesce(w.title, '') AS wtitle,
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
            nodes.append(
                {
                    "id": center_id,
                    "type": "Work",
                    "label": center_label,
                },
            )
            for rec in session.run(
                """
                MATCH (w:Work {id: $id})-[r]-(n)
                RETURN coalesce(n.id, toString(elementId(n))) AS nid,
                       labels(n) AS labs,
                       type(r) AS rt,
                       coalesce(n.name, n.full_name, n.title, '') AS nlabel
                LIMIT 200
                """,
                id=work_id,
            ):
                labs = rec["labs"] or []
                ntype = str(labs[0]) if labs else "Node"
                nid = str(rec["nid"])
                if not any(x["id"] == nid for x in nodes):
                    nodes.append(
                        {
                            "id": nid,
                            "type": ntype,
                            "label": (rec["nlabel"] or nid)[:200],
                        },
                    )
                edges.append(
                    {
                        "source": center_id,
                        "target": nid,
                        "type": rec["rt"] or "",
                    },
                )
            return {
                "work_id": work_id,
                "nodes": nodes,
                "edges": edges,
                "meta": {
                    "semantic_available": bool(row["has_semantic"]),
                },
            }
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
