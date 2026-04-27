"""Lazy fetch for article-grounded CONTRADICTS between two workspace works."""

from __future__ import annotations

from typing import Any

from science_graphrag.ontology.article_contradictions import extract_contradiction_rel_api_props
from science_graphrag.storage.neo4j_store import Neo4jGraphStore


def _jsonify_neo_value(val: Any) -> Any:
    if val is None or isinstance(val, (str, int, float, bool)):
        return val
    return str(val)


def _jsonify_mapping(m: dict[str, Any] | None) -> dict[str, Any]:
    if not m:
        return {}
    return {str(k): _jsonify_neo_value(v) for k, v in m.items()}


def fetch_workspace_contradiction_detail(
    neo: Neo4jGraphStore,
    workspace_id: str,
    work_id_a: str,
    work_id_b: str,
) -> dict[str, Any] | None:
    """Return relationship + optional ArticleContradiction node, or None if not found / not members."""
    wid = str(workspace_id or "").strip()
    wa = str(work_id_a or "").strip()
    wb = str(work_id_b or "").strip()
    if not wid or not wa or not wb or wa == wb:
        return None
    lo, hi = (wa, wb) if wa < wb else (wb, wa)
    q = """
    MATCH (ws:Workspace {id: $wid})
    OPTIONAL MATCH (ws)-[:CONTAINS]->(w:Work)
    WHERE w.id IN [$wa, $wb]
    WITH ws, collect(DISTINCT w.id) AS mem
    WHERE ws IS NOT NULL AND size(mem) >= 2 AND $wa IN mem AND $wb IN mem
    WITH $wa AS wa, $wb AS wb
    WITH wa, wb, CASE WHEN wa < wb THEN wa ELSE wb END AS lo, CASE WHEN wa < wb THEN wb ELSE wa END AS hi
    MATCH (x:Work {id: lo})-[r:CONTRADICTS]->(y:Work {id: hi})
    OPTIONAL MATCH (c:ArticleContradiction)
    WHERE r.article_contradiction_id IS NOT NULL AND c.id = r.article_contradiction_id
    RETURN lo AS work_id_lo, hi AS work_id_hi, properties(r) AS rel, properties(c) AS article
    LIMIT 1
    """
    with neo.session() as session:
        row = session.run(q, wid=wid, wa=wa, wb=wb).single()
    if not row:
        return None
    rel_raw = row.get("rel") or {}
    if not isinstance(rel_raw, dict):
        rel_raw = {}
    article_raw = row.get("article")
    if article_raw is not None and not isinstance(article_raw, dict):
        article_raw = {}

    rel_api = extract_contradiction_rel_api_props(rel_raw, for_graph_list=False)
    article_api = _jsonify_mapping(article_raw) if article_raw else None
    return {
        "workspace_id": wid,
        "work_id_lo": str(row.get("work_id_lo") or lo),
        "work_id_hi": str(row.get("work_id_hi") or hi),
        "relationship": rel_api,
        "article_contradiction": article_api,
    }
