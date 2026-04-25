"""Neo4j-driven retrieval context and workspace scoping."""

from __future__ import annotations

from typing import Any, NamedTuple

from science_graphrag.retrieval.ranking import _effective_work_id
from science_graphrag.storage.neo4j_store import Neo4jGraphStore

_SEMANTIC_EXISTS = (
    "(EXISTS { MATCH (w)-[:USES_METHOD]->(:Method) }) OR "
    "(EXISTS { MATCH (w)-[:EVALUATED_ON]->(:Dataset) })"
)


class _GraphAndResolved(NamedTuple):
    graph_context: dict[str, Any]
    resolved_work_id: str | None


def _neo4j_graph_context_for_work(store: Neo4jGraphStore, work_id: str) -> dict[str, Any]:
    methods: list[str] = []
    datasets: list[str] = []
    try:
        with store.session() as session:
            row = session.run(
                f"""
                MATCH (w:Work {{id: $wid}})
                RETURN w.id AS wid,
                       {_SEMANTIC_EXISTS} AS semantic_available
                """,
                wid=work_id,
            ).single()
            if not row:
                return {
                    "methods": [],
                    "datasets": [],
                    "semantic_available": False,
                    "context_work_id": work_id,
                    "degraded": ["work_not_in_graph"],
                    "error": None,
                }
            semantic_available = bool(row["semantic_available"])
            for rec in session.run(
                """
                MATCH (:Work {id: $wid})-[:USES_METHOD]->(m:Method)
                RETURN DISTINCT coalesce(m.name, '') AS name
                """,
                wid=work_id,
            ):
                name = (rec["name"] or "").strip()
                if name:
                    methods.append(name)
            for rec in session.run(
                """
                MATCH (:Work {id: $wid})-[:EVALUATED_ON]->(d:Dataset)
                RETURN DISTINCT coalesce(d.name, '') AS name
                """,
                wid=work_id,
            ):
                name = (rec["name"] or "").strip()
                if name:
                    datasets.append(name)
            return {
                "methods": sorted(set(methods)),
                "datasets": sorted(set(datasets)),
                "semantic_available": semantic_available,
                "context_work_id": work_id,
                "degraded": [],
                "error": None,
            }
    except Exception:  # noqa: BLE001
        return {
            "methods": [],
            "datasets": [],
            "semantic_available": False,
            "context_work_id": work_id,
            "degraded": ["neo4j_unavailable"],
            "error": "neo4j_unavailable",
        }


def _graph_context_for_hits(
    neo4j: Neo4jGraphStore,
    work_id: str | None,
    hits: list[dict[str, Any]],
) -> _GraphAndResolved:
    effective = _effective_work_id(work_id, hits)
    if effective:
        return _GraphAndResolved(_neo4j_graph_context_for_work(neo4j, effective), effective)
    return _GraphAndResolved(
        {
            "methods": [],
            "datasets": [],
            "semantic_available": False,
            "context_work_id": None,
            "degraded": ["no_resolved_work"],
            "error": None,
        },
        None,
    )


def _workspace_scope_work_ids(
    neo4j: Neo4jGraphStore,
    workspace_id: str,
) -> tuple[list[str] | None, dict[str, Any]]:
    wid = (workspace_id or "").strip()
    if not wid:
        return None, {}
    row = neo4j.workspace_get(wid)
    if not row:
        return [], {
            "workspace_id": wid,
            "workspace_missing": True,
            "workspace_scope_work_count": 0,
        }
    work_ids = [str(x) for x in (row.get("work_ids") or []) if x]
    return work_ids, {"workspace_id": wid, "workspace_scope_work_count": len(work_ids)}
