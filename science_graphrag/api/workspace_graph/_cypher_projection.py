from __future__ import annotations

from typing import Any

from science_graphrag.api.graph_display import parse_priority_csv
from science_graphrag.api.workspace_graph.projection import (
    edge_dict_from_rel,
    edge_key,
    node_dict_from_neo,
)


def run_projection_rows(
    session: Any,
    query: str,
    params_base: dict[str, Any],
    cap: int,
    prioritize: str | None,
    extract_taken: str,
) -> list[Any]:
    priority_types = parse_priority_csv(prioritize)
    params_primary = {
        **params_base,
        "preferPriority": True,
        "priorityTypes": list(priority_types),
        "excludeEmpty": True,
        "excludeIds": [],
        "lim": cap,
    }
    primary_rows = list(session.run(query, **params_primary))
    primary_take = min(len(primary_rows), max(cap // 2, cap - 50))
    selected_rows = primary_rows[:primary_take]
    taken_ids: set[str] = set()
    for rec in selected_rows:
        node = rec.get(extract_taken)
        if node is not None:
            node_id = str(dict(node).get("id") or node.element_id)
            if node_id:
                taken_ids.add(node_id)
    rest_lim = max(0, cap - len(selected_rows))
    if rest_lim > 0:
        selected_rows.extend(
            list(
                session.run(
                    query,
                    **{
                        **params_base,
                        "preferPriority": False,
                        "priorityTypes": list(priority_types),
                        "excludeEmpty": not bool(taken_ids),
                        "excludeIds": list(taken_ids),
                        "lim": rest_lim,
                    },
                )
            )
        )
    return selected_rows


def build_from_depth1_rows(
    session: Any,
    *,
    workspace_id: str,
    include_external: bool,
    node_types: list[str] | None,
    semantic_only: bool,
    cap: int,
    prioritize: str | None,
    ignore_node_type_filter: bool,
    semantic_rel_types: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
    sem_clause = ""
    if semantic_only:
        sem_clause = (
            "AND (type(r) IN $semTypes OR any(l IN labels(b) WHERE l IN ['Method','Dataset'])) "
        )
    query = (
        "MATCH (ws:Workspace {id: $wid})-[:CONTAINS]->(iw:Work) WITH collect(DISTINCT iw.id) AS internalIds "
        "MATCH (a:Work)-[r]-(b) WHERE a.id IN internalIds "
        "AND ($includeExternal OR NOT b:Work OR b.id IN internalIds) "
        "AND ($typesEmpty OR any(l IN labels(b) WHERE l IN $nodeTypes)) "
        "AND (($preferPriority AND any(l IN labels(b) WHERE l IN $priorityTypes)) "
        "OR ((NOT $preferPriority) AND NOT any(l IN labels(b) WHERE l IN $priorityTypes))) "
        "AND ($excludeEmpty OR NOT coalesce(b.id, toString(elementId(b))) IN $excludeIds) "
        f"{sem_clause}RETURN DISTINCT a, r, b LIMIT $lim"
    )
    rows = run_projection_rows(
        session,
        query,
        {
            "wid": workspace_id,
            "includeExternal": include_external,
            "typesEmpty": bool(ignore_node_type_filter) or (not node_types),
            "nodeTypes": node_types or [],
            "semTypes": semantic_rel_types,
        },
        cap,
        prioritize,
        "b",
    )
    nodes_by_id: dict[str, dict[str, Any]] = {}
    edges_by_key: dict[str, dict[str, Any]] = {}
    for rec in rows:
        a, rel, b = rec["a"], rec["r"], rec["b"]
        na = node_dict_from_neo(a)
        nb = node_dict_from_neo(b)
        if na:
            nodes_by_id[na["id"]] = na
        if nb:
            nodes_by_id[nb["id"]] = nb
        if na and nb and rel is not None:
            edge = edge_dict_from_rel(a, b, rel, len(edges_by_key))
            edges_by_key[edge_key(edge["source"], edge["type"], edge["target"])] = edge
    return list(nodes_by_id.values()), list(edges_by_key.values()), len(rows) >= cap


def build_from_depth2_rows(
    session: Any,
    *,
    workspace_id: str,
    include_external: bool,
    node_types: list[str] | None,
    semantic_only: bool,
    cap: int,
    prioritize: str | None,
    ignore_node_type_filter: bool,
    semantic_rel_types: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
    sem_clause = ""
    if semantic_only:
        sem_clause = (
            "AND (type(r1) IN $semTypes OR type(r2) IN $semTypes OR any(l IN labels(m) WHERE l IN ['Method','Dataset']) "
            "OR any(l IN labels(b) WHERE l IN ['Method','Dataset'])) "
        )
    query = (
        "MATCH (ws:Workspace {id: $wid})-[:CONTAINS]->(iw:Work) WITH collect(DISTINCT iw.id) AS I "
        "MATCH (a:Work)-[r1]-(m)-[r2]-(b) WHERE a.id IN I "
        "AND (NOT m:Work OR m.id IN I OR $includeExternal) AND (NOT b:Work OR b.id IN I OR $includeExternal) "
        "AND ($typesEmpty OR any(l IN labels(b) WHERE l IN $nodeTypes)) "
        "AND (($preferPriority AND any(l IN labels(b) WHERE l IN $priorityTypes)) "
        "OR ((NOT $preferPriority) AND NOT any(l IN labels(b) WHERE l IN $priorityTypes))) "
        "AND ($excludeEmpty OR NOT coalesce(b.id, toString(elementId(b))) IN $excludeIds) "
        f"{sem_clause}RETURN DISTINCT a, r1, m, r2, b LIMIT $lim"
    )
    lim = max(1, cap // 2)
    rows = run_projection_rows(
        session,
        query,
        {
            "wid": workspace_id,
            "includeExternal": include_external,
            "typesEmpty": bool(ignore_node_type_filter) or (not node_types),
            "nodeTypes": node_types or [],
            "semTypes": semantic_rel_types,
        },
        lim,
        prioritize,
        "b",
    )
    nodes_by_id: dict[str, dict[str, Any]] = {}
    edges_by_key: dict[str, dict[str, Any]] = {}
    for rec in rows:
        a, r1, m, r2, b = rec["a"], rec["r1"], rec["m"], rec["r2"], rec["b"]
        for node in (a, m, b):
            nd = node_dict_from_neo(node)
            if nd:
                nodes_by_id[nd["id"]] = nd
        if a is not None and m is not None and r1 is not None:
            e1 = edge_dict_from_rel(a, m, r1, len(edges_by_key))
            edges_by_key[edge_key(e1["source"], e1["type"], e1["target"])] = e1
        if m is not None and b is not None and r2 is not None:
            e2 = edge_dict_from_rel(m, b, r2, len(edges_by_key))
            edges_by_key[edge_key(e2["source"], e2["type"], e2["target"])] = e2
    return list(nodes_by_id.values()), list(edges_by_key.values()), len(rows) >= lim
