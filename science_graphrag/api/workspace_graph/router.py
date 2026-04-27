from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from science_graphrag.api.deps import StoreRegistry, get_stores
from science_graphrag.api.workspace_graph.contradiction_detail import (
    fetch_workspace_contradiction_detail,
)
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
    include_external: bool = Query(default=False),
    external_min_internal_citers: int = Query(default=0, ge=0, le=50),
    prioritize: str | None = Query(default="Method,Dataset,Work"),
    view: str = Query(default="reader", description="reader | raw"),
    include_claims: bool = Query(
        default=False,
        description=(
            "Attach capped Claim nodes + Work-[:HAS_CLAIM]->Claim " "(ignored in union_1hop mode)."
        ),
    ),
    claims_per_work: int | None = Query(
        default=None,
        ge=1,
        description="Optional per-work claims cap; omit for uncapped claim slices.",
    ),
    claims_max_total: int | None = Query(
        default=None,
        ge=1,
        description="Optional total claims cap; omit for uncapped claim slices.",
    ),
    settings: Settings = Depends(get_settings),
    stores: StoreRegistry = Depends(get_stores),
) -> dict[str, Any]:
    graph = project_workspace_graph(
        stores.neo4j,
        settings,
        workspace_id,
        mode=mode,
        depth=1,
        include_external=include_external,
        node_types=None,
        neighbor_limit=None,
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


@router.get("/{workspace_id}/graph/contradiction-detail")
def get_workspace_contradiction_detail(
    workspace_id: str,
    work_id_a: str = Query(..., min_length=1, description="Work.id (one endpoint of CONTRADICTS)"),
    work_id_b: str = Query(..., min_length=1, description="Work.id (other endpoint)"),
    stores: StoreRegistry = Depends(get_stores),
) -> dict[str, Any]:
    """Full article-grounded payload for a Work–Work CONTRADICTS edge inside a workspace."""
    wa = str(work_id_a or "").strip()
    wb = str(work_id_b or "").strip()
    if not wa or not wb or wa == wb:
        raise HTTPException(status_code=400, detail="invalid_work_pair")
    payload = fetch_workspace_contradiction_detail(stores.neo4j, workspace_id, wa, wb)
    if payload is None:
        raise HTTPException(status_code=404, detail="contradiction_not_found")
    return payload


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
    prioritize: str | None = Query(default="Method,Dataset,Work"),
    stores: StoreRegistry = Depends(get_stores),
) -> dict[str, Any]:
    graph = workspace_graph_neighbors(
        stores.neo4j,
        workspace_id,
        node_id,
        depth=1,
        limit=None,
        prioritize=prioritize,
    )
    if graph is None:
        raise HTTPException(status_code=404, detail="workspace_not_found")
    return graph


@router.get("/{workspace_id}/graph/expand")
def expand_workspace_aggregator(
    workspace_id: str,
    aggregator_id: str = Query(..., min_length=6),
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
        depth=1,
        limit=None,
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
