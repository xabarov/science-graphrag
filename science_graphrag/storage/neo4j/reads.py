"""Read-only Neo4j queries (no writes)."""

from __future__ import annotations

from typing import Any

from science_graphrag.storage.neo4j.client import _Neo4jClient


def find_work_id_by_doi(client: _Neo4jClient, doi: str) -> str | None:
    q = "MATCH (w:Work {doi: $doi}) RETURN w.id AS id LIMIT 1"
    with client.session() as session:
        rec = session.run(q, doi=doi).single()
        return rec["id"] if rec else None


def find_work_id_by_fingerprint(client: _Neo4jClient, fingerprint: str) -> str | None:
    q = "MATCH (w:Work {fingerprint: $fp}) RETURN w.id AS id LIMIT 1"
    with client.session() as session:
        rec = session.run(q, fp=fingerprint).single()
        return rec["id"] if rec else None


def find_work_id_by_arxiv(client: _Neo4jClient, arxiv_id: str) -> str | None:
    q = "MATCH (w:Work {arxiv_id: $arxiv_id}) RETURN w.id AS id LIMIT 1"
    with client.session() as session:
        rec = session.run(q, arxiv_id=arxiv_id).single()
        return rec["id"] if rec else None


def get_work_external_keys(client: _Neo4jClient, work_id: str) -> dict[str, str] | None:
    """Return doi / arxiv_id / fingerprint for canonical-key checks."""
    q = """
    MATCH (w:Work {id: $id})
    RETURN coalesce(w.doi, '') AS doi,
           coalesce(w.arxiv_id, '') AS arxiv_id,
           coalesce(w.fingerprint, '') AS fingerprint
    LIMIT 1
    """
    with client.session() as session:
        rec = session.run(q, id=work_id).single()
        if not rec:
            return None
        return {
            "doi": str(rec["doi"] or ""),
            "arxiv_id": str(rec["arxiv_id"] or ""),
            "fingerprint": str(rec["fingerprint"] or ""),
        }


def work_exists(client: _Neo4jClient, work_id: str) -> bool:
    q = "MATCH (w:Work {id: $id}) RETURN 1 AS ok LIMIT 1"
    with client.session() as session:
        rec = session.run(q, id=work_id).single()
        return bool(rec)


def work_has_incoming_cites(client: _Neo4jClient, work_id: str) -> bool:
    q = """
    MATCH (:Work)-[:CITES]->(w:Work {id: $id})
    RETURN count(*) AS n
    """
    with client.session() as session:
        rec = session.run(q, id=work_id).single()
        return bool(rec and int(rec["n"]) > 0)


def find_work_dedup_violations(client: _Neo4jClient) -> list[dict[str, Any]]:
    """Return clusters where multiple :Work nodes share the same dedup key."""
    queries: list[tuple[str, str]] = [
        (
            "doi",
            """
            MATCH (w:Work)
            WHERE w.doi IS NOT NULL AND trim(toString(w.doi)) <> ''
            WITH w.doi AS k, collect(DISTINCT w.id) AS ids
            WHERE size(ids) > 1
            RETURN k AS dedup_key, ids
            """,
        ),
        (
            "openalex_id",
            """
            MATCH (w:Work)
            WHERE w.openalex_id IS NOT NULL AND trim(toString(w.openalex_id)) <> ''
            WITH w.openalex_id AS k, collect(DISTINCT w.id) AS ids
            WHERE size(ids) > 1
            RETURN k AS dedup_key, ids
            """,
        ),
        (
            "fingerprint",
            """
            MATCH (w:Work)
            WHERE w.fingerprint IS NOT NULL AND trim(toString(w.fingerprint)) <> ''
            WITH w.fingerprint AS k, collect(DISTINCT w.id) AS ids
            WHERE size(ids) > 1
            RETURN k AS dedup_key, ids
            """,
        ),
        (
            "arxiv_id",
            """
            MATCH (w:Work)
            WHERE w.arxiv_id IS NOT NULL AND trim(toString(w.arxiv_id)) <> ''
            WITH w.arxiv_id AS k, collect(DISTINCT w.id) AS ids
            WHERE size(ids) > 1
            RETURN k AS dedup_key, ids
            """,
        ),
    ]
    out: list[dict[str, Any]] = []
    with client.session() as session:
        for kind, cypher in queries:
            for rec in session.run(cypher):
                out.append(
                    {"kind": kind, "dedup_key": rec["dedup_key"], "work_ids": list(rec["ids"])},
                )
    return out


def fetch_work_bibliography_card(client: _Neo4jClient, work_id: str) -> dict[str, Any] | None:
    """Title/year/first author + abstract snippet for dedup prompts."""
    q = """
    MATCH (w:Work {id: $id})
    OPTIONAL MATCH (w)-[:HAS_AUTHORSHIP]->(ash:Authorship)
    WITH w, ash
    ORDER BY ash.author_position ASC
    WITH w, head(collect(ash)) AS a1
    OPTIONAL MATCH (a1)-[:OF_AUTHOR]->(auth:Author)
    RETURN coalesce(w.title, '') AS title,
           w.publication_year AS year,
           coalesce(w.abstract, '') AS abstract,
           coalesce(w.doi, '') AS doi,
           coalesce(w.arxiv_id, '') AS arxiv_id,
           coalesce(auth.full_name, '') AS first_author
    LIMIT 1
    """
    with client.session() as session:
        rec = session.run(q, id=work_id).single()
        if not rec:
            return None
        return {
            "work_id": work_id,
            "title": str(rec["title"] or ""),
            "year": rec["year"],
            "abstract": str(rec["abstract"] or ""),
            "doi": str(rec["doi"] or ""),
            "arxiv_id": str(rec["arxiv_id"] or ""),
            "first_author": str(rec["first_author"] or ""),
        }


def fulltext_search_work_ids(
    client: _Neo4jClient,
    query: str,
    *,
    limit: int = 20,
) -> list[tuple[str, float]]:
    """Full-text search on works index. Returns (work_id, score)."""
    q = (query or "").strip()
    if not q:
        return []
    cypher = """
    CALL db.index.fulltext.queryNodes('works_title_abstract', $search)
    YIELD node, score
    WHERE 'Work' IN labels(node)
    RETURN node.id AS wid, score
    LIMIT $lim
    """
    try:
        with client.session() as session:
            rows = session.run(cypher, search=q, lim=int(limit))
            out: list[tuple[str, float]] = []
            for r in rows:
                wid = str(r["wid"] or "").strip()
                if wid:
                    out.append((wid, float(r["score"] or 0.0)))
            return out
    except Exception:  # noqa: BLE001
        return []


def cites_neighbor_work_ids(
    client: _Neo4jClient,
    seed_work_ids: list[str],
    *,
    exclude_ids: set[str],
    limit: int = 80,
) -> list[str]:
    """Distinct :Work ids reachable by one CITES hop from any seed work."""
    seeds = [str(x).strip() for x in seed_work_ids if str(x).strip()]
    if not seeds:
        return []
    excl = [str(x).strip() for x in exclude_ids if str(x).strip()]
    cypher = """
    UNWIND $seeds AS sid
    MATCH (w:Work {id: sid})-[r:CITES]-(n:Work)
    WHERE NOT n.id IN $excl
    RETURN DISTINCT n.id AS nid
    LIMIT $lim
    """
    try:
        with client.session() as session:
            rows = session.run(cypher, seeds=seeds[:50], excl=excl[:500], lim=int(limit))
            return [str(r["nid"]) for r in rows if r.get("nid")]
    except Exception:  # noqa: BLE001
        return []


def list_workspace_authors(client: _Neo4jClient, workspace_id: str) -> list[dict[str, Any]]:
    """Distinct authors attached to works in a workspace (for L2 dedup scan)."""
    q = """
    MATCH (ws:Workspace {id: $ws})-[:CONTAINS]->(:Work)-[:HAS_AUTHORSHIP]->(:Authorship)-[:OF_AUTHOR]->(a:Author)
    RETURN DISTINCT a.id AS id, coalesce(a.full_name, '') AS full_name
    """
    with client.session() as session:
        rows = session.run(q, ws=workspace_id)
        return [{"id": str(r["id"]), "full_name": str(r["full_name"] or "")} for r in rows]


def list_work_authors(client: _Neo4jClient, work_id: str) -> list[dict[str, Any]]:
    """Authors linked to a single work (for ingest-time dedup)."""
    q = """
    MATCH (:Work {id: $wid})-[:HAS_AUTHORSHIP]->(:Authorship)-[:OF_AUTHOR]->(a:Author)
    RETURN DISTINCT a.id AS id, coalesce(a.full_name, '') AS full_name
    """
    with client.session() as session:
        rows = session.run(q, wid=str(work_id or "").strip())
        return [{"id": str(r["id"]), "full_name": str(r["full_name"] or "")} for r in rows]


def fetch_author_display_name(client: _Neo4jClient, author_id: str) -> str:
    q = """
    MATCH (a:Author {id: $id})
    RETURN coalesce(a.full_name, a.normalized_name, '') AS name
    """
    aid = str(author_id or "").strip()
    if not aid:
        return ""
    with client.session() as session:
        rec = session.run(q, id=aid).single()
        if not rec:
            return ""
        return str(rec["name"] or "").strip()


def fetch_author_affiliation_hint(client: _Neo4jClient, author_id: str) -> str:
    q = """
    MATCH (a:Author {id: $id})<-[:OF_AUTHOR]-(x:Authorship)
    RETURN coalesce(x.raw_affiliation, '') AS aff
    LIMIT 1
    """
    with client.session() as session:
        rec = session.run(q, id=author_id).single()
        if not rec:
            return ""
        return str(rec["aff"] or "")


def workspace_list(client: _Neo4jClient) -> list[dict[str, Any]]:
    q = """
    MATCH (ws:Workspace)
    OPTIONAL MATCH (ws)-[:CONTAINS]->(w:Work)
    WITH ws, collect(DISTINCT w.id) AS wids
    RETURN ws.id AS id, ws.name AS name, ws.created_at AS created_at, wids AS work_ids,
           coalesce(ws.unbounded, false) AS unbounded
    ORDER BY ws.created_at DESC
    """
    out: list[dict[str, Any]] = []
    with client.session() as session:
        for rec in session.run(q):
            wids = [str(x) for x in (rec["work_ids"] or []) if x]
            out.append(
                {
                    "id": str(rec["id"]),
                    "name": str(rec["name"] or ""),
                    "created_at": str(rec["created_at"] or ""),
                    "work_ids": wids,
                    "unbounded": bool(rec["unbounded"]),
                },
            )
    return out


def workspace_get(client: _Neo4jClient, workspace_id: str) -> dict[str, Any] | None:
    q = """
    MATCH (ws:Workspace {id: $id})
    OPTIONAL MATCH (ws)-[:CONTAINS]->(w:Work)
    WITH ws, collect(DISTINCT w.id) AS wids
    RETURN ws.id AS id, ws.name AS name, ws.created_at AS created_at, wids AS work_ids,
           coalesce(ws.unbounded, false) AS unbounded
    """
    with client.session() as session:
        rec = session.run(q, id=workspace_id).single()
        if not rec:
            return None
        wids = [str(x) for x in (rec["work_ids"] or []) if x]
        return {
            "id": str(rec["id"]),
            "name": str(rec["name"] or ""),
            "created_at": str(rec["created_at"] or ""),
            "work_ids": wids,
            "unbounded": bool(rec["unbounded"]),
        }


def list_work_institutions(client: _Neo4jClient, work_id: str) -> list[dict[str, Any]]:
    q = """
    MATCH (:Work {id: $wid})-[:HAS_AUTHORSHIP]->(:Authorship)-[:AFFILIATED_WITH]->(i:Institution)
    RETURN DISTINCT i.id AS id,
           coalesce(i.name, '') AS name,
           coalesce(i.normalized_name, i.name, '') AS normalized_name,
           coalesce(i.country, '') AS country,
           coalesce(i.city, '') AS city
    """
    with client.session() as session:
        return [dict(r) for r in session.run(q, wid=str(work_id or "").strip())]


def list_work_venues(client: _Neo4jClient, work_id: str) -> list[dict[str, Any]]:
    q = """
    MATCH (:Work {id: $wid})-[:PUBLISHED_IN]->(v:Venue)
    RETURN DISTINCT v.id AS id,
           coalesce(v.name, '') AS name,
           coalesce(v.normalized_name, v.name, '') AS normalized_name,
           coalesce(v.venue_type, '') AS venue_type
    """
    with client.session() as session:
        return [dict(r) for r in session.run(q, wid=str(work_id or "").strip())]


def list_work_methods(client: _Neo4jClient, work_id: str) -> list[dict[str, Any]]:
    q = """
    MATCH (:Work {id: $wid})-[:USES_METHOD]->(m:Method)
    RETURN DISTINCT m.id AS id,
           coalesce(m.name, '') AS name,
           coalesce(m.normalized_name, m.name, '') AS normalized_name,
           coalesce(m.aliases, []) AS aliases,
           coalesce(m.description_short, '') AS description_short
    """
    with client.session() as session:
        return [dict(r) for r in session.run(q, wid=str(work_id or "").strip())]


def list_work_datasets(client: _Neo4jClient, work_id: str) -> list[dict[str, Any]]:
    q = """
    MATCH (:Work {id: $wid})-[:EVALUATED_ON]->(d:Dataset)
    RETURN DISTINCT d.id AS id,
           coalesce(d.name, '') AS name,
           coalesce(d.normalized_name, d.name, '') AS normalized_name,
           coalesce(d.aliases, []) AS aliases
    """
    with client.session() as session:
        return [dict(r) for r in session.run(q, wid=str(work_id or "").strip())]


def list_workspace_institutions(client: _Neo4jClient, workspace_id: str) -> list[dict[str, Any]]:
    q = """
    MATCH (:Workspace {id: $ws})-[:CONTAINS]->(:Work)-[:HAS_AUTHORSHIP]->(:Authorship)-[:AFFILIATED_WITH]->(i:Institution)
    RETURN DISTINCT i.id AS id,
           coalesce(i.name, '') AS name,
           coalesce(i.normalized_name, i.name, '') AS normalized_name,
           coalesce(i.country, '') AS country,
           coalesce(i.city, '') AS city
    """
    with client.session() as session:
        return [dict(r) for r in session.run(q, ws=workspace_id)]


def list_workspace_venues(client: _Neo4jClient, workspace_id: str) -> list[dict[str, Any]]:
    q = """
    MATCH (:Workspace {id: $ws})-[:CONTAINS]->(:Work)-[:PUBLISHED_IN]->(v:Venue)
    RETURN DISTINCT v.id AS id,
           coalesce(v.name, '') AS name,
           coalesce(v.normalized_name, v.name, '') AS normalized_name,
           coalesce(v.venue_type, '') AS venue_type
    """
    with client.session() as session:
        return [dict(r) for r in session.run(q, ws=workspace_id)]


def list_workspace_methods(client: _Neo4jClient, workspace_id: str) -> list[dict[str, Any]]:
    q = """
    MATCH (:Workspace {id: $ws})-[:CONTAINS]->(:Work)-[:USES_METHOD]->(m:Method)
    RETURN DISTINCT m.id AS id,
           coalesce(m.name, '') AS name,
           coalesce(m.normalized_name, m.name, '') AS normalized_name,
           coalesce(m.aliases, []) AS aliases,
           coalesce(m.description_short, '') AS description_short
    """
    with client.session() as session:
        return [dict(r) for r in session.run(q, ws=workspace_id)]


def list_workspace_datasets(client: _Neo4jClient, workspace_id: str) -> list[dict[str, Any]]:
    q = """
    MATCH (:Workspace {id: $ws})-[:CONTAINS]->(:Work)-[:EVALUATED_ON]->(d:Dataset)
    RETURN DISTINCT d.id AS id,
           coalesce(d.name, '') AS name,
           coalesce(d.normalized_name, d.name, '') AS normalized_name,
           coalesce(d.aliases, []) AS aliases
    """
    with client.session() as session:
        return [dict(r) for r in session.run(q, ws=workspace_id)]


_ENTITY_NODE_LABELS: dict[str, str] = {
    "institution": "Institution",
    "venue": "Venue",
    "method": "Method",
    "dataset": "Dataset",
}


def fetch_entity_display_label(client: _Neo4jClient, entity_type: str, entity_id: str) -> str:
    et = str(entity_type or "").strip().lower()
    label = _ENTITY_NODE_LABELS.get(et)
    eid = str(entity_id or "").strip()
    if not label or not eid:
        return eid
    q = f"MATCH (n:{label} {{id: $id}}) RETURN coalesce(n.name, n.normalized_name, '') AS name"
    with client.session() as session:
        rec = session.run(q, id=eid).single()
        if not rec:
            return eid
        name = str(rec["name"] or "").strip()
        return name or eid
