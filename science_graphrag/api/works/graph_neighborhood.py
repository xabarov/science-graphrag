"""Work graph neighborhood API (orchestration + expand); payload assembly is in ``graph_neighborhood_payload``."""

from __future__ import annotations

from typing import Any

from science_graphrag.api.graph_reader_meta import enrich_reader_graph_meta
from science_graphrag.api.works.graph_neighborhood_aggregation import (
    _aggregator_id,
    _append_neighbor_edge,
    parse_aggregator_id,
)
from science_graphrag.api.works.graph_neighborhood_payload import (
    MAX_WORK_GRAPH_NEIGHBORS,
    _work_graph_neighborhood_payload,
    _work_neighbors_rows,
    load_work_graph_workspace_internal_ids,
)
from science_graphrag.stores.registry import StoreRegistry

__all__ = [
    "MAX_WORK_GRAPH_NEIGHBORS",
    "_aggregator_id",
    "_append_neighbor_edge",
    "_work_graph_neighborhood_payload",
    "_work_neighbors_rows",
    "expand_work_aggregator",
    "load_work_graph_workspace_internal_ids",
    "work_graph_neighborhood",
]


def work_graph_neighborhood(
    stores: StoreRegistry | Any,
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
                    view=view,
                    workspace_id=workspace_id,
                    workspace_internal_work_ids=workspace_internal_work_ids,
                    aggregator_threshold=aggregator_threshold,
                    aggregator_disabled_kinds=aggregator_disabled_kinds,
                    include_claims=include_claims,
                    claims_limit=claims_limit,
                    include_authorship_debug=include_authorship_debug,
                    include_institutions=include_institutions,
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
            view=view,
            workspace_id=workspace_id,
            workspace_internal_work_ids=workspace_internal_work_ids,
            aggregator_threshold=aggregator_threshold,
            aggregator_disabled_kinds=aggregator_disabled_kinds,
            include_claims=include_claims,
            claims_limit=claims_limit,
            include_authorship_debug=include_authorship_debug,
            include_institutions=include_institutions,
        )


def expand_work_aggregator(
    stores: StoreRegistry | Any,
    work_id: str,
    aggregator_id: str,
    *,
    limit: int = 50,
    workspace_id: str | None = None,
    workspace_internal_work_ids: set[str] | None = None,
    include_institutions: bool = False,
) -> dict[str, Any] | None:
    owner_id, node_kind, edge_type = parse_aggregator_id(aggregator_id)
    # Reader collapse uses virtual Work—[AUTHORED]→Author edges; raw payload has
    # HAS_AUTHORSHIP→Authorship instead. Re-fetch reader with author aggregation disabled
    # so expand returns the same logical neighbors as the pre-aggregation graph.
    use_reader_authored = (
        str(edge_type or "").upper() == "AUTHORED"
        and str(node_kind or "").lower() == "author"
        and str(owner_id or "").strip() == str(work_id or "").strip()
    )
    payload = work_graph_neighborhood(
        stores,
        work_id,
        neighbor_limit=max(200, limit * 4),
        depth=1,
        prioritize="Method,Dataset,Work,Author,Authorship,Institution,Venue",
        view="reader" if use_reader_authored else "raw",
        workspace_id=workspace_id,
        workspace_internal_work_ids=workspace_internal_work_ids,
        aggregator_disabled_kinds="Author" if use_reader_authored else None,
        include_institutions=include_institutions,
    )
    if not payload:
        return None
    nodes = list(payload.get("nodes") or [])
    edges = list(payload.get("edges") or [])
    node_by_id = {str(n.get("id") or ""): n for n in nodes}
    picked_nodes: list[dict[str, Any]] = []
    picked_edges: list[dict[str, Any]] = []
    for edge in edges:
        src = str(edge.get("source") or "")
        tgt = str(edge.get("target") or "")
        rt = str(edge.get("type") or "").upper()
        if rt != edge_type.upper():
            continue
        if src == owner_id:
            other = tgt
        elif tgt == owner_id:
            other = src
        else:
            continue
        node = node_by_id.get(other)
        kind = str(node.get("node_kind") or node.get("type") or "").lower() if node else ""
        if kind != node_kind.lower():
            continue
        picked_edges.append(edge)
        if node:
            picked_nodes.append(node)
        if len(picked_nodes) >= max(1, int(limit)):
            break
    uniq_nodes = {owner_id: node_by_id.get(owner_id)}
    for node in picked_nodes:
        uniq_nodes[str(node.get("id") or "")] = node
    final_nodes = [n for n in uniq_nodes.values() if n]
    kept_ids = {str(n.get("id") or "") for n in final_nodes}
    final_edges = [
        e
        for e in picked_edges
        if str(e.get("source") or "") in kept_ids and str(e.get("target") or "") in kept_ids
    ]
    expand_meta: dict[str, Any] = {"expanded_aggregator_id": aggregator_id}
    _ws_norm = str(workspace_id or "").strip() or None
    enrich_reader_graph_meta(
        expand_meta,
        neighbor_limit=max(200, limit * 4),
        prioritize="Method,Dataset,Work,Author,Authorship,Institution,Venue",
        view="reader" if use_reader_authored else "raw",
        workspace_id=_ws_norm,
        graph_mode="work_expand_aggregator",
    )
    pm = payload.get("meta") or {}
    expand_meta["include_institutions"] = bool(include_institutions)
    if include_institutions:
        if pm.get("reader_extra_hops"):
            expand_meta["reader_extra_hops"] = list(pm["reader_extra_hops"])
        if pm.get("institutions"):
            expand_meta["institutions"] = dict(pm["institutions"])
    return {
        "nodes": final_nodes,
        "edges": final_edges,
        "meta": expand_meta,
    }
