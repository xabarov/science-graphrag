from __future__ import annotations

import hashlib
from typing import Any

from neo4j import Session as Neo4jSession

from science_graphrag.api.deps import StoreRegistry
from science_graphrag.api.graph_display import (
    compute_node_display,
    edge_display_type,
    enrich_authorship_nodes,
    node_kind_priority,
    parse_priority_csv,
    resolve_node_kind,
)

MAX_WORK_GRAPH_NEIGHBORS = 300


def _has_semantic_layer_cypher() -> str:
    return (
        "(EXISTS { MATCH (w)-[:USES_METHOD]->(:Method) }) OR "
        "(EXISTS { MATCH (w)-[:EVALUATED_ON]->(:Dataset) })"
    )


def _neighborhood_edge_endpoints(
    center_id: str, neighbor_id: str, raw_src: str, raw_tgt: str
) -> tuple[str, str]:
    endpoints = {center_id, neighbor_id}
    if raw_src and raw_tgt and raw_src != raw_tgt and {raw_src, raw_tgt} == endpoints:
        return raw_src, raw_tgt
    return center_id, neighbor_id


def _stable_edge_id(source: str, rel_type: str, target: str, seq: int) -> str:
    payload = f"{source}\0{rel_type or ''}\0{target}\0{seq}".encode()
    return "e_" + hashlib.sha256(payload).hexdigest()[:22]


def _append_neighbor_edge(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    center_id: str,
    rec: Any,
) -> None:
    labs = rec["labs"] or []
    ntype = str(labs[0]) if labs else "Node"
    nid = str(rec["nid"])
    props: dict[str, Any] = {}
    for key, src, ln in (
        ("publication_year", "n_pub_year", None),
        ("doi", "n_doi", 256),
        ("arxiv_id", "n_arxiv", 256),
        ("venue", "n_venue", 200),
        ("workspace_membership", "n_workspace_membership", 32),
        ("country", "n_country", 120),
        ("venue_type", "n_venue_type", 120),
        ("issn", "n_issn", 64),
    ):
        val = rec.get(src)
        if val is None:
            continue
        sval = str(val).strip()
        if sval:
            props[key] = sval[:ln] if ln else val
    rendered = compute_node_display(
        ntype,
        str(rec.get("nlabel") or "").strip(),
        props,
        authorship_extra=(
            {
                "author_position": rec.get("n_ash_pos"),
                "author_name": rec.get("n_ash_author"),
                "raw_affiliation": rec.get("n_ash_aff"),
                "institution_name": rec.get("n_ash_inst"),
                "is_corresponding": rec.get("n_ash_corr"),
            }
            if ntype == "Authorship"
            else None
        ),
    )
    workspace_membership = str(
        props.get("workspace_membership") or rec.get("n_workspace_membership") or ""
    ).strip()
    if not any(x["id"] == nid for x in nodes):
        nodes.append(
            {
                "id": nid,
                "type": ntype,
                "label": str(rendered["display_label"]),
                "display_label": str(rendered["display_label"]),
                "subtitle": str(rendered["subtitle"]),
                "node_kind": resolve_node_kind(ntype, workspace_membership=workspace_membership),
                "properties": dict(rendered["properties"]),
            }
        )
    src_id, tgt_id = _neighborhood_edge_endpoints(
        center_id,
        nid,
        str(rec.get("src_id") or "").strip(),
        str(rec.get("tgt_id") or "").strip(),
    )
    edges.append({"source": src_id, "target": tgt_id, "type": rec["rt"] or ""})


def _enrich_edges_with_display(
    center_id: str, nodes: list[dict[str, Any]], edges: list[dict[str, Any]]
) -> None:
    by_id = {n["id"]: n for n in nodes}
    for seq, edge in enumerate(edges):
        src_id, tgt_id = str(edge.get("source") or ""), str(edge.get("target") or "")
        src_n, tgt_n = by_id.get(src_id, {}), by_id.get(tgt_id, {})
        sl = str(src_n.get("display_label") or src_n.get("label") or src_id)
        tl = str(tgt_n.get("display_label") or tgt_n.get("label") or tgt_id)
        rt = str(edge.get("type") or "")
        disp_t = edge_display_type(rt)
        edge["id"] = str(edge.get("id") or "").strip() or _stable_edge_id(src_id, rt, tgt_id, seq)
        edge["display_type"] = disp_t
        edge["source_label"] = sl
        edge["target_label"] = tl
        edge["summary"] = f"{sl} —[{disp_t}]→ {tl}"
        edge["direction"] = (
            "outgoing" if src_id == center_id else "incoming" if tgt_id == center_id else "lateral"
        )


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
               coalesce(inst.name, '') AS n_ash_inst
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


def _work_graph_neighborhood_payload(
    session: Neo4jSession,
    work_id: str,
    *,
    neighbor_limit: int = 200,
    depth: int = 1,
    prioritize: str | None = None,
) -> dict[str, Any] | None:
    row = session.run(
        """
        MATCH (w:Work {id: $id})
        RETURN w.id AS wid, coalesce(w.title, '') AS wtitle, w.publication_year AS wyear,
               coalesce(w.doi, '') AS wdoi, coalesce(w.arxiv_id, '') AS warxiv,
               coalesce(w.venue_name, '') AS wvenue,
        """
        + _has_semantic_layer_cypher()
        + """ AS has_semantic
        """,
        id=work_id,
    ).single()
    if not row:
        return None
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    center_id = str(row["wid"])
    cprops = {}
    for k, v in (
        ("publication_year", row.get("wyear")),
        ("doi", str(row.get("wdoi") or "").strip()),
        ("arxiv_id", str(row.get("warxiv") or "").strip()),
        ("venue", str(row.get("wvenue") or "").strip()[:200]),
    ):
        if v:
            cprops[k] = v
    cr = compute_node_display("Work", str(row.get("wtitle") or "").strip(), cprops)
    nodes.append(
        {
            "id": center_id,
            "type": "Work",
            "label": str(cr["display_label"]),
            "display_label": str(cr["display_label"]),
            "subtitle": str(cr["subtitle"]),
            "node_kind": resolve_node_kind("Work"),
            "properties": dict(cr["properties"]),
            "distance": 0,
        }
    )
    total_neighbors = int(
        session.run("MATCH (w:Work {id: $id})-[r]-(n) RETURN count(r) AS c", id=work_id).single()[
            "c"
        ]
    )
    kind_distribution: dict[str, int] = {
        str(rec["kind"] or "Unknown"): int(rec["c"])
        for rec in session.run(
            "MATCH (w:Work {id: $id})-[r]-(n) WITH labels(n) AS labs, count(r) AS c "
            "RETURN labs[0] AS kind, c",
            id=work_id,
        )
    }
    depth_req = max(1, min(int(depth), 3))
    cap = min(MAX_WORK_GRAPH_NEIGHBORS, max(1, min(int(neighbor_limit), 2000)))
    hop1_lim, hop2_lim, effective_depth = (
        (cap, 0, 1)
        if depth_req <= 1
        else (max(1, (cap * 2) // 3), max(1, cap - max(1, (cap * 2) // 3)), 2)
    )
    priority_types = parse_priority_csv(prioritize)
    primary_rows = _work_neighbors_rows(
        session, work_id=work_id, lim=hop1_lim, priority_types=priority_types, prefer_priority=True
    )
    primary_take = min(len(primary_rows), max(hop1_lim // 2, hop1_lim - 50))
    primary_used = primary_rows[:primary_take]
    taken_ids = [str(rec.get("nid") or "") for rec in primary_used if str(rec.get("nid") or "")]
    secondary_rows: list[Any] = []
    if hop1_lim - len(primary_used) > 0:
        secondary_rows = _work_neighbors_rows(
            session,
            work_id=work_id,
            lim=hop1_lim - len(primary_used),
            priority_types=priority_types,
            prefer_priority=False,
            exclude_ids=taken_ids,
        )
    for rec in [*primary_used, *secondary_rows]:
        _append_neighbor_edge(nodes, edges, center_id, rec)
    for n in nodes[1:]:
        n.setdefault("distance", 1)
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
                RETURN coalesce(n.id, toString(elementId(n))) AS nid, labels(n) AS labs, type(r) AS rt,
                       coalesce(n.name, n.full_name, n.title, '') AS nlabel,
                       coalesce(startNode(r).id, toString(elementId(startNode(r)))) AS src_id,
                       coalesce(endNode(r).id, toString(elementId(endNode(r)))) AS tgt_id,
                       n.publication_year AS n_pub_year, coalesce(n.doi, '') AS n_doi,
                       coalesce(n.arxiv_id, '') AS n_arxiv, coalesce(n.venue_name, '') AS n_venue
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
    center_node = next((n for n in nodes if str(n.get("id") or "") == center_id), None)
    neighbor_nodes = [n for n in nodes if str(n.get("id") or "") != center_id]
    neighbor_nodes.sort(
        key=lambda n: (node_kind_priority(str(n.get("node_kind") or "")), str(n.get("id") or ""))
    )
    skipped_by_kind: dict[str, int] = {}
    if len(neighbor_nodes) > cap:
        neighbor_nodes = neighbor_nodes[:cap]
    # Compute skipped counts from graph-level kind distribution vs what is returned.
    # This covers both cap-truncated and never-fetched nodes.
    if kind_distribution:
        fetched_by_type: dict[str, int] = {}
        for node in neighbor_nodes:
            t = str(node.get("type") or "Unknown")
            fetched_by_type[t] = fetched_by_type.get(t, 0) + 1
        for kind, available in kind_distribution.items():
            fetched = fetched_by_type.get(kind, 0)
            if available > fetched:
                skipped_by_kind[kind] = available - fetched
    kept_ids = {center_id, *[str(n.get("id") or "") for n in neighbor_nodes]}
    nodes = ([center_node] if center_node else []) + neighbor_nodes
    edges = [
        e
        for e in edges
        if str(e.get("source") or "") in kept_ids and str(e.get("target") or "") in kept_ids
    ]
    enrich_authorship_nodes(session, nodes)
    _enrich_edges_with_display(center_id, nodes, edges)
    truncated = bool(skipped_by_kind) or total_neighbors > hop1_lim
    expansions = ["increase_neighbor_limit"] if truncated else []
    if depth_req > effective_depth:
        expansions.append("multi_hop_depth")
    return {
        "work_id": work_id,
        "nodes": nodes,
        "edges": edges,
        "meta": {
            "semantic_available": bool(row["has_semantic"]),
            "graph_scope": "work_2hop" if effective_depth >= 2 else "work_1hop",
            "graph_depth_requested": int(depth),
            "graph_depth_effective": effective_depth,
            "neighbor_match_count": total_neighbors,
            "neighbor_limit_applied": hop1_lim + (hop2_lim if effective_depth >= 2 else 0),
            "nodes_returned": len(nodes),
            "edges_returned": len(edges),
            "is_truncated": truncated,
            "skipped_by_kind": skipped_by_kind if skipped_by_kind else {},
            "available_expansions": expansions,
        },
    }


def work_graph_neighborhood(
    stores: StoreRegistry | Any,
    work_id: str,
    *,
    neighbor_limit: int = 200,
    depth: int = 1,
    prioritize: str | None = None,
) -> dict[str, Any] | None:
    # Backward compatibility: older callers pass Settings instead of StoreRegistry.
    if not hasattr(stores, "neo4j"):
        from science_graphrag.storage.neo4j_store import Neo4jGraphStore

        temp = Neo4jGraphStore(stores.neo4j_uri, stores.neo4j_user, stores.neo4j_password)
        try:
            with temp.session() as session:
                return _work_graph_neighborhood_payload(
                    session,
                    work_id,
                    neighbor_limit=neighbor_limit,
                    depth=depth,
                    prioritize=prioritize,
                )
        finally:
            temp.close()
    with stores.neo4j.session() as session:
        return _work_graph_neighborhood_payload(
            session,
            work_id,
            neighbor_limit=neighbor_limit,
            depth=depth,
            prioritize=prioritize,
        )
