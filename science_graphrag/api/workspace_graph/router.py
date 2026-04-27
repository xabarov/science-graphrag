from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from science_graphrag.api.deps import StoreRegistry, get_stores
from science_graphrag.api.workspace_graph.cypher import (
    project_workspace_graph,
    workspace_graph_neighbors,
    workspace_graph_stats,
)
from science_graphrag.config import Settings, get_settings

router = APIRouter(prefix="/v1/workspaces", tags=["workspace-graph"])


@router.get("/{workspace_id}/graph")
def get_workspace_graph(
    workspace_id: str,
    mode: str = Query(
        default="inner_only",
        description="inner_only | union_1hop | semantic_layer | full",
    ),
    depth: int = Query(default=1, ge=1, le=2),
    include_external: bool = Query(default=False),
    external_min_internal_citers: int = Query(default=0, ge=0, le=50),
    node_types: str | None = Query(
        default=None,
        description="Comma-separated: Work,Author,Method,Dataset,Venue,Institution,Authorship,Claim",
    ),
    prioritize: str | None = Query(default="Method,Dataset,Work"),
    view: str = Query(default="reader", description="reader | raw"),
    neighbor_limit: int = Query(default=200, ge=1, le=2000),
    include_claims: bool = Query(
        default=False,
        description="Attach capped Claim nodes + Work-[:HAS_CLAIM]->Claim (ignored in union_1hop mode).",
    ),
    claims_per_work: int = Query(default=12, ge=1, le=80),
    claims_max_total: int = Query(default=120, ge=1, le=500),
    settings: Settings = Depends(get_settings),
    stores: StoreRegistry = Depends(get_stores),
) -> dict[str, Any]:
    graph = project_workspace_graph(
        stores.neo4j,
        settings,
        workspace_id,
        mode=mode,
        depth=depth,
        include_external=include_external,
        node_types=node_types,
        neighbor_limit=neighbor_limit,
        external_min_internal_citers=external_min_internal_citers,
        prioritize=prioritize,
        view=view,
        include_claims=include_claims,
        claims_per_work=claims_per_work,
        claims_max_total=claims_max_total,
    )
    if graph is None:
        raise HTTPException(status_code=404, detail="workspace_not_found")
    return graph


@router.get("/{workspace_id}/graph/stats")
def get_workspace_graph_stats(
    workspace_id: str,
    stores: StoreRegistry = Depends(get_stores),
) -> dict[str, Any]:
    stats = workspace_graph_stats(stores.neo4j, workspace_id)
    if stats is None:
        raise HTTPException(status_code=404, detail="workspace_not_found")
    return stats


@router.get("/{workspace_id}/graph/neighbors")
def get_workspace_graph_neighbors(
    workspace_id: str,
    node_id: str = Query(..., min_length=1, description="Neo4j node id (e.g. Work.id)"),
    depth: int = Query(default=1, ge=1, le=2),
    limit: int = Query(default=80, ge=1, le=200),
    prioritize: str | None = Query(default="Method,Dataset,Work"),
    stores: StoreRegistry = Depends(get_stores),
) -> dict[str, Any]:
    graph = workspace_graph_neighbors(
        stores.neo4j,
        workspace_id,
        node_id,
        depth=depth,
        limit=limit,
        prioritize=prioritize,
    )
    if graph is None:
        raise HTTPException(status_code=404, detail="workspace_not_found")
    return graph


@router.get("/{workspace_id}/graph/expand")
def expand_workspace_aggregator(
    workspace_id: str,
    aggregator_id: str = Query(..., min_length=6),
    limit: int = Query(default=50, ge=1, le=300),
    stores: StoreRegistry = Depends(get_stores),
) -> dict[str, Any]:
    raw = str(aggregator_id or "").strip()
    if not raw.startswith("agg:"):
        raise HTTPException(status_code=400, detail="invalid_aggregator_id")
    try:
        _, owner_encoded, node_kind, edge_type = raw.split(":", 3)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid_aggregator_id") from exc
    owner_id = owner_encoded.replace("%3A", ":")
    payload = workspace_graph_neighbors(
        stores.neo4j,
        workspace_id,
        owner_id,
        depth=2,
        limit=max(80, int(limit) * 3),
        prioritize="Method,Dataset,Work,Author,Authorship,Institution,Venue",
    )
    if payload is None:
        raise HTTPException(status_code=404, detail="workspace_not_found")
    nodes = list(payload.get("nodes") or [])
    edges = list(payload.get("edges") or [])
    node_by_id = {str(n.get("id") or ""): n for n in nodes}
    picked_nodes = []
    picked_edges = []
    for edge in edges:
        src = str(edge.get("source") or "")
        tgt = str(edge.get("target") or "")
        rt = str(edge.get("type") or "").upper()
        if rt != edge_type.upper():
            continue
        other = tgt if src == owner_id else src if tgt == owner_id else ""
        if not other:
            continue
        node = node_by_id.get(other)
        if not node:
            continue
        kind = str(node.get("node_kind") or node.get("type") or "").lower()
        if kind != node_kind.lower():
            continue
        picked_edges.append(edge)
        picked_nodes.append(node)
        if len(picked_nodes) >= int(limit):
            break
    uniq_nodes = {owner_id: node_by_id.get(owner_id)}
    for node in picked_nodes:
        uniq_nodes[str(node.get("id") or "")] = node
    out_nodes = [n for n in uniq_nodes.values() if n]
    kept_ids = {str(n.get("id") or "") for n in out_nodes}
    out_edges = [
        e
        for e in picked_edges
        if str(e.get("source") or "") in kept_ids and str(e.get("target") or "") in kept_ids
    ]
    return {
        "nodes": out_nodes,
        "edges": out_edges,
        "meta": {"expanded_aggregator_id": aggregator_id},
    }
