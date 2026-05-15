"""Neo4j row queries for work graph neighborhood assembly (split from payload module)."""

from __future__ import annotations

from typing import Any

from neo4j import Session as Neo4jSession


def load_work_graph_workspace_internal_ids(
    session: Neo4jSession,
    *,
    workspace_id: str,
    center_work_id: str,
) -> tuple[set[str] | None, str | None]:
    """Load internal ``Work`` ids for workspace membership annotation.

    Returns ``(internal_ids, None)`` on success. On failure returns
    ``(None, "workspace_not_found")`` or ``(None, "work_not_in_workspace")``.
    """
    row = session.run(
        """
        MATCH (ws:Workspace {id: $wid})
        OPTIONAL MATCH (ws)-[:CONTAINS]->(cw:Work {id: $work_id})
        OPTIONAL MATCH (ws)-[:CONTAINS]->(iw:Work)
        RETURN ws.id AS wid,
               cw.id AS center_member,
               collect(DISTINCT iw.id) AS internal_ids
        """,
        wid=str(workspace_id).strip(),
        work_id=str(center_work_id).strip(),
    ).single()
    if not row or not str(row.get("wid") or "").strip():
        return None, "workspace_not_found"
    if not str(row.get("center_member") or "").strip():
        return None, "work_not_in_workspace"
    raw = row.get("internal_ids") or []
    iws = {str(x) for x in raw if x}
    return iws, None


def _work_neighbors_rows(
    session: Neo4jSession,
    *,
    work_id: str,
    lim: int,
    priority_types: tuple[str, ...],
    prefer_priority: bool,
    exclude_ids: list[str] | None = None,
) -> list[Any]:
    q = """
        MATCH (w:Work {id: $id})-[r]-(n)
        WHERE ($prefer_priority AND any(l IN labels(n) WHERE l IN $priority_types))
           OR ((NOT $prefer_priority) AND NOT any(l IN labels(n) WHERE l IN $priority_types))
        """
    if exclude_ids:
        q += " AND NOT coalesce(n.id, toString(elementId(n))) IN $exclude_ids "
    q += """
        OPTIONAL MATCH (n)-[:OF_AUTHOR]->(auth:Author)
        OPTIONAL MATCH (n)-[:AFFILIATED_WITH]->(inst:Institution)
        RETURN coalesce(n.id, toString(elementId(n))) AS nid, labels(n) AS labs, type(r) AS rt,
               coalesce(n.title, n.name, n.full_name, '') AS nlabel,
               coalesce(startNode(r).id, toString(elementId(startNode(r)))) AS src_id,
               coalesce(endNode(r).id, toString(elementId(endNode(r)))) AS tgt_id,
               n.publication_year AS n_pub_year, coalesce(n.doi, '') AS n_doi, coalesce(n.arxiv_id, '') AS n_arxiv,
               coalesce(n.venue_name, '') AS n_venue, coalesce(n.country, '') AS n_country,
               coalesce(n.venue_type, '') AS n_venue_type, coalesce(n.issn, '') AS n_issn,
               n.author_position AS n_ash_pos, coalesce(n.raw_affiliation, '') AS n_ash_aff,
               n.is_corresponding AS n_ash_corr, coalesce(auth.full_name, '') AS n_ash_author,
               coalesce(inst.name, '') AS n_ash_inst,
               coalesce(auth.id, '') AS n_auth_id
        LIMIT $lim
    """
    params: dict[str, Any] = {
        "id": work_id,
        "lim": lim,
        "priority_types": list(priority_types),
        "prefer_priority": bool(prefer_priority),
    }
    if exclude_ids:
        params["exclude_ids"] = exclude_ids
    return list(session.run(q, **params))
