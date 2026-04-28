from __future__ import annotations

from typing import Any

from science_graphrag.api import works as works_api
from science_graphrag.api.graph_reader_meta import enrich_reader_graph_meta
from science_graphrag.api.graph_reader_projection.authorship_enrich import enrich_authorship_nodes
from science_graphrag.api.workspace_graph._cypher_gds import (
    gds_runtime_available,
    semantic_any,
)
from science_graphrag.api.workspace_graph._cypher_projection import (
    build_from_depth1_rows,
    run_projection_rows,
)
from science_graphrag.api.workspace_graph.claims_projection import (
    build_claim_graph_slice_for_workspace,
)
from science_graphrag.api.workspace_graph.projection import (
    annotate_membership_and_cites,
    apply_workspace_aggregators,
    apply_workspace_node_kind,
    edge_dict_from_rel,
    edge_key,
    enrich_edges_workspace,
    filter_external_works_by_min_citers,
    merge_graph_payloads,
    merge_nodes_edges_lists,
    node_dict_from_neo,
    parse_node_types_csv,
)
from science_graphrag.config import Settings
from science_graphrag.storage.neo4j_store import Neo4jGraphStore

SEMANTIC_REL_TYPES_LIST = sorted(
    {"USES_METHOD", "EVALUATED_ON", "HAS_AUTHORSHIP", "OF_AUTHOR", "AFFILIATED_WITH"}
)


def legacy_workspace_graph_union(
    neo4j_store: Neo4jGraphStore,
    settings: Settings,
    workspace_id: str,
    *,
    neighbor_limit: int | None = None,
    prioritize: str | None = None,
    view: str = "reader",
) -> dict[str, Any] | None:
    with neo4j_store.session() as session:
        row = session.run(
            "MATCH (ws:Workspace {id: $wid}) OPTIONAL MATCH (ws)-[:CONTAINS]->(w:Work) "
            "RETURN ws.id AS wid, collect(DISTINCT w.id) AS wids",
            wid=workspace_id,
        ).single()
    if not row or not row["wid"]:
        return None
    work_ids = [str(x) for x in (row["wids"] or []) if x]
    if not work_ids:
        empty_meta: dict[str, Any] = {
            "semantic_available": False,
            "graph_scope": "workspace_union_1hop",
            "graph_depth_effective": 1,
            "workspace_node_count": 0,
            "workspace_edge_count": 0,
            "is_truncated": False,
            "available_expansions": [],
            "workspace_id": workspace_id,
            "source_work_ids": [],
        }
        enrich_reader_graph_meta(
            empty_meta,
            neighbor_limit=None,
            prioritize=prioritize,
            view=view,
            workspace_id=workspace_id,
        )
        return {
            "work_id": "",
            "nodes": [],
            "edges": [],
            "meta": empty_meta,
        }
    if neighbor_limit is None:
        per_lim = 500_000
    else:
        per_lim = max(1, int(neighbor_limit))
    payloads: list[dict[str, Any]] = []
    for wid in work_ids:
        graph = works_api.work_graph_neighborhood(settings, wid, neighbor_limit=per_lim, depth=1)
        if graph:
            payloads.append(graph)
    merged = merge_graph_payloads(payloads)
    merged["meta"]["workspace_id"] = workspace_id
    merged["meta"]["source_work_ids"] = work_ids
    enrich_reader_graph_meta(
        merged["meta"],
        neighbor_limit=None,
        prioritize=prioritize,
        view=view,
        workspace_id=workspace_id,
    )
    return merged


def project_workspace_graph(
    neo4j_store: Neo4jGraphStore,
    settings: Settings,
    workspace_id: str,
    *,
    mode: str = "inner_only",
    depth: int = 1,
    include_external: bool = False,
    node_types: str | None = None,
    neighbor_limit: int | None = None,
    external_min_internal_citers: int = 0,
    prioritize: str | None = None,
    view: str = "reader",
    include_claims: bool = False,
    claims_per_work: int | None = None,
    claims_max_total: int | None = None,
) -> dict[str, Any] | None:
    mode_norm = (mode or "inner_only").strip().lower()
    # Full workspace graph: always uncapped 1-hop from internal works (see ADR-011 / graph-ui-plan).
    cap: int | None = None
    ignored_query_params: list[str] = []
    if int(depth) != 1:
        ignored_query_params.append("depth")
    if neighbor_limit is not None:
        ignored_query_params.append("neighbor_limit")
    if node_types is not None and str(node_types).strip():
        ignored_query_params.append("node_types")
    types_list = parse_node_types_csv(node_types)
    claims_slice_meta: dict[str, Any] = {
        "include_claims": bool(include_claims),
        "claims_included": False,
    }
    with neo4j_store.session() as session:
        row = session.run(
            "MATCH (ws:Workspace {id: $wid}) OPTIONAL MATCH (ws)-[:CONTAINS]->(w:Work) "
            "RETURN ws.id AS wid, collect(DISTINCT w.id) AS wids",
            wid=workspace_id,
        ).single()
        if not row or not row["wid"]:
            return None
        internal_ids = [str(x) for x in (row["wids"] or []) if x]
        iws = set(internal_ids)
        gds_avail = gds_runtime_available(session)
        if mode_norm == "union_1hop":
            out = legacy_workspace_graph_union(
                neo4j_store,
                settings,
                workspace_id,
                neighbor_limit=None,
                prioritize=prioritize,
                view=view,
            )
            if out is None:
                return None
            nodes = list(out.get("nodes") or [])
            edges = list(out.get("edges") or [])
            enrich_authorship_nodes(session, nodes)
            enrich_edges_workspace(nodes, edges)
            inc, exc = annotate_membership_and_cites(nodes, edges, iws)
            apply_workspace_node_kind(nodes)
            if include_claims:
                claims_slice_meta = {
                    "include_claims": True,
                    "claims_included": False,
                    "claims_disabled_reason": "union_1hop_mode",
                }
            out["meta"] = {
                **dict(out.get("meta") or {}),
                "graph_scope": "workspace_v2",
                "mode": mode_norm,
                "graph_depth_requested": int(depth),
                "graph_depth_effective": 1,
                "include_external": True,
                "node_types_filter": types_list,
                "internal_node_count": inc,
                "external_node_count": exc,
                "edge_count": len(edges),
                "cap_applied": None,
                "workspace_id": workspace_id,
                "source_work_ids": internal_ids,
                "gds_used": False,
                "gds_runtime_available": gds_avail,
                "deprecated_ignored_query_params": ignored_query_params or None,
                **claims_slice_meta,
            }
            enrich_reader_graph_meta(
                out["meta"],
                neighbor_limit=None,
                prioritize=prioritize,
                view=view,
                workspace_id=workspace_id,
            )
            return out
        if not internal_ids:
            empty_ws_meta: dict[str, Any] = {
                "semantic_available": False,
                "graph_scope": "workspace_v2",
                "mode": mode_norm,
                "graph_depth_requested": int(depth),
                "graph_depth_effective": 1,
                "include_external": include_external,
                "node_types_filter": types_list or [],
                "internal_node_count": 0,
                "external_node_count": 0,
                "edge_count": 0,
                "is_truncated": False,
                "cap_applied": None,
                "workspace_id": workspace_id,
                "source_work_ids": [],
                "available_expansions": ["add_works"],
                "gds_used": False,
                "gds_runtime_available": gds_avail,
                "deprecated_ignored_query_params": ignored_query_params or None,
                **claims_slice_meta,
            }
            enrich_reader_graph_meta(
                empty_ws_meta,
                neighbor_limit=None,
                prioritize=prioritize,
                view=view,
                workspace_id=workspace_id,
            )
            return {
                "work_id": "",
                "nodes": [],
                "edges": [],
                "meta": empty_ws_meta,
            }
        semantic_only = mode_norm == "semantic_layer"
        # Node-type filtering is a client concern; server returns full incident subgraph (mode
        # gates).
        ignore_node_type_filter = True
        nodes, edges, truncated = build_from_depth1_rows(
            session,
            workspace_id=workspace_id,
            include_external=include_external,
            node_types=types_list,
            semantic_only=semantic_only,
            cap=cap,
            prioritize=prioritize,
            ignore_node_type_filter=ignore_node_type_filter,
            semantic_rel_types=SEMANTIC_REL_TYPES_LIST,
        )
        gds_used = False
        sem = semantic_any(session, internal_ids)
        if external_min_internal_citers > 0 and include_external:
            nodes, edges = filter_external_works_by_min_citers(
                nodes, edges, iws, external_min_internal_citers
            )
        if include_claims:
            cn, ce, cmeta = build_claim_graph_slice_for_workspace(
                session,
                workspace_id,
                claims_per_work=None if claims_per_work is None else max(1, int(claims_per_work)),
                max_claims_total=(
                    None if claims_max_total is None else max(1, int(claims_max_total))
                ),
            )
            nodes, edges = merge_nodes_edges_lists(nodes, edges, cn, ce)
            claims_slice_meta = {
                "include_claims": True,
                "claims_included": True,
                **cmeta,
            }
        enrich_authorship_nodes(session, nodes)
    enrich_edges_workspace(nodes, edges)
    inc_n, exc_n = annotate_membership_and_cites(nodes, edges, iws)
    apply_workspace_node_kind(nodes)
    if str(view or "reader").strip().lower() != "raw":
        nodes, edges = apply_workspace_aggregators(
            workspace_id,
            nodes,
            edges,
        )
    expansions: list[str] = []
    if truncated:
        expansions.append("increase_neighbor_limit")
    expansions.extend(["include_external", "expand_node"])
    main_meta: dict[str, Any] = {
        "semantic_available": sem,
        "graph_scope": "workspace_v2",
        "mode": mode_norm,
        "graph_depth_requested": int(depth),
        "graph_depth_effective": 1,
        "include_external": include_external,
        "node_types_filter": types_list or [],
        "internal_node_count": inc_n,
        "external_node_count": exc_n,
        "edge_count": len(edges),
        "is_truncated": truncated,
        "cap_applied": cap,
        "workspace_id": workspace_id,
        "source_work_ids": internal_ids,
        "available_expansions": expansions,
        "gds_used": gds_used,
        "gds_runtime_available": gds_avail,
        "deprecated_ignored_query_params": ignored_query_params or None,
        **claims_slice_meta,
    }
    enrich_reader_graph_meta(
        main_meta,
        neighbor_limit=None,
        prioritize=prioritize,
        view=view,
        workspace_id=workspace_id,
    )
    return {
        "work_id": "",
        "nodes": nodes,
        "edges": edges,
        "meta": main_meta,
    }


def workspace_graph_stats(neo4j_store: Neo4jGraphStore, workspace_id: str) -> dict[str, Any] | None:
    with neo4j_store.session() as session:
        row = session.run(
            "MATCH (ws:Workspace {id: $wid}) OPTIONAL MATCH (ws)-[:CONTAINS]->(w:Work) "
            "RETURN ws.id AS wid, count(DISTINCT w) AS works_n",
            wid=workspace_id,
        ).single()
        if not row or not row["wid"]:
            return None
        works_count = int(row["works_n"] or 0)
        if works_count == 0:
            return {
                "workspace_id": workspace_id,
                "works_count": 0,
                "authors_count": 0,
                "internal_citations": 0,
                "external_citations": 0,
                "external_works_count": 0,
            }
        authors_count = int(
            (
                session.run(
                    "MATCH (ws:Workspace {id: $wid})-[:CONTAINS]->(:Work)-[:HAS_AUTHORSHIP]->(:Authorship)-[:OF_AUTHOR]->(a:Author) RETURN count(DISTINCT a) AS c",
                    wid=workspace_id,
                ).single()
                or {"c": 0}
            )["c"]
        )
        internal_citations = int(
            (
                session.run(
                    "MATCH (ws:Workspace {id: $wid})-[:CONTAINS]->(iw:Work) WITH collect(DISTINCT iw.id) AS I "
                    "MATCH (a:Work)-[:CITES]->(b:Work) WHERE a.id IN I AND b.id IN I RETURN count(*) AS c",
                    wid=workspace_id,
                ).single()
                or {"c": 0}
            )["c"]
        )
        erow = session.run(
            "MATCH (ws:Workspace {id: $wid})-[:CONTAINS]->(iw:Work) WITH collect(DISTINCT iw.id) AS I "
            "MATCH (a:Work)-[:CITES]->(b:Work) WHERE a.id IN I AND NOT b.id IN I RETURN count(*) AS c, count(DISTINCT b) AS dw",
            wid=workspace_id,
        ).single()
    return {
        "workspace_id": workspace_id,
        "works_count": works_count,
        "authors_count": authors_count,
        "internal_citations": internal_citations,
        "external_citations": int(erow["c"]) if erow else 0,
        "external_works_count": int(erow["dw"]) if erow else 0,
    }


def workspace_graph_neighbors(
    neo4j_store: Neo4jGraphStore,
    workspace_id: str,
    node_id: str,
    *,
    depth: int = 1,
    limit: int | None = None,
    prioritize: str | None = None,
) -> dict[str, Any] | None:
    nid = (node_id or "").strip()
    if not nid:
        return None
    ignored: list[str] = []
    if int(depth) != 1:
        ignored.append("depth")
    if limit is not None:
        ignored.append("limit")
    cap: int | None = None
    with neo4j_store.session() as session:
        ws_row = session.run(
            "MATCH (ws:Workspace {id: $wid}) RETURN ws.id AS wid", wid=workspace_id
        ).single()
        if not ws_row or not ws_row["wid"]:
            return None
        nodes_by_id: dict[str, dict[str, Any]] = {}
        edges_by_key: dict[str, dict[str, Any]] = {}
        q_h1 = (
            "MATCH (n {id: $nid}) MATCH (n)-[r]-(m) "
            "WHERE (($preferPriority AND any(l IN labels(m) WHERE l IN $priorityTypes)) "
            "OR ((NOT $preferPriority) AND NOT any(l IN labels(m) WHERE l IN $priorityTypes))) "
            "AND ($excludeEmpty OR NOT coalesce(m.id, toString(elementId(m))) IN $excludeIds) "
            "RETURN n, r, m"
        )
        for rec in run_projection_rows(session, q_h1, {"nid": nid}, cap, prioritize, "m"):
            n, rel_obj, m = rec["n"], rec["r"], rec["m"]
            nn, nm = node_dict_from_neo(n), node_dict_from_neo(m)
            if nn:
                nodes_by_id[nn["id"]] = nn
            if nm:
                nodes_by_id[nm["id"]] = nm
            if n is not None and m is not None and rel_obj is not None:
                edge = edge_dict_from_rel(n, m, rel_obj, len(edges_by_key))
                edges_by_key[edge_key(edge["source"], edge["type"], edge["target"])] = edge
        nodes = list(nodes_by_id.values())
        edges = list(edges_by_key.values())
        enrich_authorship_nodes(session, nodes)
        row_ids = session.run(
            "MATCH (ws:Workspace {id: $wid})-[:CONTAINS]->(w:Work) RETURN collect(DISTINCT w.id) AS I",
            wid=workspace_id,
        ).single()
        iws = {str(x) for x in (row_ids["I"] or []) if x}
    enrich_edges_workspace(nodes, edges)
    annotate_membership_and_cites(nodes, edges, iws)
    apply_workspace_node_kind(nodes)
    neigh_meta: dict[str, Any] = {
        "graph_scope": "workspace_neighbors",
        "neighbor_limit_applied": None,
        "deprecated_ignored_query_params": ignored or None,
        "is_truncated": False,
    }
    enrich_reader_graph_meta(
        neigh_meta,
        neighbor_limit=None,
        prioritize=prioritize,
        view="reader",
        workspace_id=workspace_id,
    )
    return {
        "workspace_id": workspace_id,
        "center_id": nid,
        "depth_requested": int(depth),
        "depth_effective": 1,
        "nodes": nodes,
        "edges": edges,
        "meta": neigh_meta,
    }
