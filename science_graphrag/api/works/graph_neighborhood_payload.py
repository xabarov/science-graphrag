"""Work graph neighborhood payload assembly (Neo4j session → nodes/edges/meta)."""

from __future__ import annotations

from typing import Any

from neo4j import Session as Neo4jSession

from science_graphrag.api.graph_display import (
    compute_node_display,
    node_kind_priority,
    parse_priority_csv,
    resolve_node_kind,
)
from science_graphrag.api.graph_reader_meta import enrich_reader_graph_meta
from science_graphrag.api.graph_reader_projection.authorship_collapse import (
    build_authorship_to_reader_author_map,
    collapse_authorship_for_reader_view,
)
from science_graphrag.api.graph_reader_projection.authorship_enrich import enrich_authorship_nodes
from science_graphrag.api.graph_reader_projection.authorship_meta import (
    compute_authorship_projection_meta,
    strip_reader_only_authorship_properties,
)
from science_graphrag.api.works.graph_neighborhood_aggregation import (
    _append_neighbor_edge,
    _enrich_edges_with_display,
    _has_semantic_layer_cypher,
)
from science_graphrag.api.works.graph_neighborhood_institutions import (
    INSTITUTION_ATTACH_CAP,
    attach_institutions_raw,
    attach_institutions_reader,
    fetch_work_authorship_institutions,
)
from science_graphrag.api.workspace_graph.claims_projection import build_claim_graph_slice_for_work
from science_graphrag.api.workspace_graph.projection import (
    annotate_membership_and_cites,
    apply_workspace_node_kind,
    merge_nodes_edges_lists,
)

MAX_WORK_GRAPH_NEIGHBORS = 300


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


def _work_graph_neighborhood_payload(  # pylint: disable=too-many-arguments,too-many-locals,too-many-branches,too-many-statements
    session: Neo4jSession,
    work_id: str,
    *,
    neighbor_limit: int = 200,
    depth: int = 1,
    prioritize: str | None = None,
    view: str = "reader",
    workspace_id: str | None = None,
    workspace_internal_work_ids: set[str] | None = None,
    aggregator_threshold: int | None = None,
    aggregator_disabled_kinds: str | None = None,
    include_claims: bool = False,
    claims_limit: int = 24,
    include_authorship_debug: bool = False,
    include_institutions: bool = False,
) -> dict[str, Any] | None:
    """Assemble work-neighborhood JSON (nodes/edges/meta) from a Neo4j session.

    Legacy / deprecated query parameters
    --------------------------------------
    ``aggregator_threshold`` and ``aggregator_disabled_kinds`` are accepted for API
    stability but **ignored** since GR8 neighbor aggregation was disabled (2026-04-28).
    The response always reports ``meta.neighbor_aggregation == "none"``; callers must
    not rely on these knobs to change node bucketing or payload shape.
    """
    # Query params kept for API stability; neighbor bucketing (GR8) is permanently off.
    _ = (aggregator_threshold, aggregator_disabled_kinds)
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
    counts_row = session.run(
        """
        MATCH (w:Work {id: $id})
        OPTIONAL MATCH (wi:Work)-[:CITES]->(w)
        OPTIONAL MATCH (w)-[:CITES]->(wo:Work)
        OPTIONAL MATCH (w)-[:HAS_AUTHORSHIP]->(:Authorship)-[:OF_AUTHOR]->(auth:Author)
        RETURN count(DISTINCT wi) AS cites_in_count,
               count(DISTINCT wo) AS cites_out_count,
               count(DISTINCT auth) AS authors_count
        """,
        id=work_id,
    ).single()
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    center_id = str(row["wid"])
    cprops: dict[str, Any] = {}
    for k, v in (
        ("publication_year", row.get("wyear")),
        ("doi", str(row.get("wdoi") or "").strip()),
        ("arxiv_id", str(row.get("warxiv") or "").strip()),
        ("venue", str(row.get("wvenue") or "").strip()[:200]),
    ):
        if v:
            cprops[k] = v
    if counts_row:
        cprops["cites_in_count"] = int(counts_row.get("cites_in_count") or 0)
        cprops["cites_out_count"] = int(counts_row.get("cites_out_count") or 0)
        cprops["authors_count"] = int(counts_row.get("authors_count") or 0)
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
                RETURN coalesce(n.id, toString(elementId(n))) AS nid,
                       labels(n) AS labs, type(r) AS rt,
                       coalesce(n.name, n.full_name, n.title, '') AS nlabel,
                       coalesce(startNode(r).id, toString(elementId(startNode(r)))) AS src_id,
                       coalesce(endNode(r).id, toString(elementId(endNode(r)))) AS tgt_id,
                       n.publication_year AS n_pub_year, coalesce(n.doi, '') AS n_doi,
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
    claims_meta: dict[str, Any] = {"include_claims": bool(include_claims), "claims_included": False}
    if include_claims:
        cn, ce, cm = build_claim_graph_slice_for_work(
            session,
            work_id,
            claims_limit=max(1, min(int(claims_limit), 120)),
        )
        nodes, edges = merge_nodes_edges_lists(nodes, edges, cn, ce)
        claims_meta = {"include_claims": True, "claims_included": True, **cm}
    enrich_authorship_nodes(session, nodes)
    vnorm = str(view or "reader").strip().lower()
    inst_rows: list[dict[str, Any]] = []
    if include_institutions:
        inst_rows = fetch_work_authorship_institutions(session, work_id, INSTITUTION_ATTACH_CAP)
    ash_author_map: dict[str, str] = {}
    if include_institutions and vnorm == "reader":
        ash_author_map = build_authorship_to_reader_author_map(nodes, edges, center_id)
    institutions_attached = 0
    if vnorm == "raw":
        strip_reader_only_authorship_properties(nodes)
    if include_institutions and vnorm == "raw":
        institutions_attached = attach_institutions_raw(nodes, edges, inst_rows)
    if vnorm == "reader":
        nodes, edges = collapse_authorship_for_reader_view(nodes, edges, center_id)
    if include_institutions and vnorm == "reader":
        institutions_attached = attach_institutions_reader(nodes, edges, inst_rows, ash_author_map)
    reader_authorship_projection = (
        compute_authorship_projection_meta(center_id, edges) if vnorm == "reader" else None
    )
    _enrich_edges_with_display(center_id, nodes, edges)
    # GR8 neighbor aggregation disabled (2026-04-28): concrete nodes within caps only.
    # ``aggregator_threshold`` / ``aggregator_disabled_kinds`` are accepted but ignored.
    if workspace_internal_work_ids is not None and str(workspace_id or "").strip():
        annotate_membership_and_cites(nodes, edges, workspace_internal_work_ids)
        apply_workspace_node_kind(nodes)
    truncated = bool(skipped_by_kind) or total_neighbors > hop1_lim
    expansions = ["increase_neighbor_limit"] if truncated else []
    if depth_req > effective_depth:
        expansions.append("multi_hop_depth")
    meta: dict[str, Any] = {
        "neighbor_aggregation": "none",
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
        "include_institutions": bool(include_institutions),
        **claims_meta,
    }
    if include_institutions:
        meta["reader_extra_hops"] = ["institution"]
        meta["institutions"] = {
            "cap": INSTITUTION_ATTACH_CAP,
            "returned": int(institutions_attached),
        }
    _ws_ctx = workspace_internal_work_ids is not None and bool(str(workspace_id or "").strip())
    enrich_reader_graph_meta(
        meta,
        neighbor_limit=int(neighbor_limit),
        prioritize=prioritize,
        view=view,
        workspace_id=workspace_id,
        graph_mode="work_workspace_context" if _ws_ctx else None,
    )
    if include_authorship_debug and reader_authorship_projection is not None:
        meta["authorship_projection"] = reader_authorship_projection
    return {
        "work_id": work_id,
        "nodes": nodes,
        "edges": edges,
        "meta": meta,
    }
