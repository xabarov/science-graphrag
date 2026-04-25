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
        description="Comma-separated: Work,Author,Method,Dataset,Venue,Institution,Authorship",
    ),
    prioritize: str | None = Query(default="Method,Dataset,Work"),
    neighbor_limit: int = Query(default=200, ge=1, le=2000),
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
