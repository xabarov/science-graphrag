"""Optional Claim nodes for workspace / work graph payloads (high cardinality — always capped)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from science_graphrag.api.workspace_graph.projection import edge_dict_from_ids, node_dict_from_neo


def _claim_rows_for_workspace(
    session: Any,
    workspace_id: str,
) -> list[dict[str, Any]]:
    """Return rows with work_id and neo4j claim node (distinct per work+claim)."""

    q = """
    MATCH (ws:Workspace {id: $wid})-[:CONTAINS]->(w:Work)
    MATCH (c:Claim)-[:SUPPORTED_BY]->(:Evidence)-[:ANCHORED_IN]->(w)
    RETURN DISTINCT w.id AS work_id, c AS claim
    """
    return list(session.run(q, wid=str(workspace_id).strip()))


def _claim_rows_for_work(session: Any, work_id: str) -> list[dict[str, Any]]:
    q = """
    MATCH (w:Work {id: $wid})
    MATCH (c:Claim)-[:SUPPORTED_BY]->(:Evidence)-[:ANCHORED_IN]->(w)
    RETURN DISTINCT c AS claim
    """
    return list(session.run(q, wid=str(work_id).strip()))


def build_claim_graph_slice_for_workspace(
    session: Any,
    workspace_id: str,
    *,
    claims_per_work: int | None,
    max_claims_total: int | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Build Claim nodes + synthetic Work-[:HAS_CLAIM]->Claim edges (capped)."""

    per_work = None if claims_per_work is None else max(1, int(claims_per_work))
    max_total = None if max_claims_total is None else max(1, int(max_claims_total))

    rows = _claim_rows_for_workspace(session, workspace_id)
    grouped: dict[str, list[Any]] = defaultdict(list)
    for rec in rows:
        wid = str(rec.get("work_id") or "").strip()
        claim = rec.get("claim")
        if not wid or claim is None:
            continue
        grouped[wid].append(claim)

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seq = 0
    total = 0
    truncated = False

    for work_id in sorted(grouped.keys()):
        if max_total is not None and total >= max_total:
            truncated = True
            break
        claims = grouped[work_id]
        claims_sorted = sorted(claims, key=lambda n: str(dict(n).get("id") or n.element_id))
        budget = len(claims_sorted)
        if per_work is not None:
            budget = min(budget, per_work)
        if max_total is not None:
            budget = min(budget, max_total - total)
        for claim in claims_sorted[:budget]:
            nd = node_dict_from_neo(claim)
            if not nd:
                continue
            cid = str(nd["id"])
            nodes.append(nd)
            edges.append(edge_dict_from_ids(work_id, cid, "HAS_CLAIM", seq))
            seq += 1
            total += 1
            if max_total is not None and total >= max_total:
                truncated = True
                break

    meta = {
        "claims_nodes": len(nodes),
        "claims_per_work_cap": per_work,
        "claims_max_total_cap": max_total,
        "claims_truncated": truncated,
    }
    return nodes, edges, meta


def build_claim_graph_slice_for_work(
    session: Any,
    work_id: str,
    *,
    claims_limit: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    lim = max(1, min(int(claims_limit), 120))
    rows = _claim_rows_for_work(session, work_id)
    claims = [rec.get("claim") for rec in rows if rec.get("claim") is not None]
    claims_sorted = sorted(claims, key=lambda n: str(dict(n).get("id") or n.element_id))

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seq = 0
    for claim in claims_sorted[:lim]:
        nd = node_dict_from_neo(claim)
        if not nd:
            continue
        cid = str(nd["id"])
        nodes.append(nd)
        edges.append(edge_dict_from_ids(work_id, cid, "HAS_CLAIM", seq))
        seq += 1

    meta = {
        "claims_nodes": len(nodes),
        "claims_limit_cap": lim,
        "claims_truncated": len(claims_sorted) > lim,
    }
    return nodes, edges, meta
