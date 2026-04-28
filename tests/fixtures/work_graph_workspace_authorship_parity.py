"""Helpers for Phase 3 parity tests: work graph reader vs workspace graph payload.

Comparison rules are documented in ``docs/architecture/work-graph-reader-authorship.md``.
"""

from __future__ import annotations

from typing import Any


def surfaced_author_count_reader_work_graph(payload: dict[str, Any], center_id: str) -> int:
    """How many author targets the reader work graph represents (post-collapse, post-aggregate)."""
    for n in payload.get("nodes") or []:
        if str(n.get("node_kind") or "") != "Aggregator":
            continue
        hints = n.get("aggregation_hints") or {}
        if str(hints.get("aggregator_kind") or "") != "author_of_work":
            continue
        agg_owner = str(n.get("id") or "")
        if agg_owner.startswith("agg:") and center_id.replace(":", "%3A") in agg_owner:
            try:
                return max(1, int(hints.get("count") or 0))
            except (TypeError, ValueError):
                return 1
    author_nodes = sum(
        1
        for n in (payload.get("nodes") or [])
        if str(n.get("type") or "") == "Author" or str(n.get("node_kind") or "") == "Author"
    )
    authored_edges = sum(
        1
        for e in (payload.get("edges") or [])
        if str(e.get("type") or "").upper() == "AUTHORED"
        and str(e.get("source") or "") == center_id
    )
    return max(author_nodes, authored_edges)


def logical_author_slots_workspace_payload(center_work_id: str, edges: list[dict[str, Any]]) -> int:
    """Logical author slots from a workspace graph payload (pre UI author projection).

    Counts each ``Authorship`` via ``HAS_AUTHORSHIP`` from the work; merges ``OF_AUTHOR`` targets.
    Authorship rows without ``OF_AUTHOR`` each count as one slot (like ``va:`` on work graph).
    """
    ash_from_work: set[str] = set()
    for edge in edges or []:
        rt = str(edge.get("type") or "").upper()
        if rt != "HAS_AUTHORSHIP":
            continue
        src, tgt = str(edge.get("source") or ""), str(edge.get("target") or "")
        if src == center_work_id:
            ash_from_work.add(tgt)
        elif tgt == center_work_id:
            ash_from_work.add(src)
    if not ash_from_work:
        return 0
    of_pairs: list[tuple[str, str]] = []
    for edge in edges or []:
        if str(edge.get("type") or "").upper() != "OF_AUTHOR":
            continue
        src, tgt = str(edge.get("source") or ""), str(edge.get("target") or "")
        if src in ash_from_work:
            of_pairs.append((src, tgt))
        elif tgt in ash_from_work:
            of_pairs.append((tgt, src))
    author_by_ash: dict[str, str] = {}
    for ash_id, author_id in of_pairs:
        if ash_id in ash_from_work and author_id:
            author_by_ash[ash_id] = author_id
    merged_authors = set(author_by_ash.values())
    orphan_ashes = ash_from_work - set(author_by_ash.keys())
    return len(merged_authors) + len(orphan_ashes)


def workspace_one_hop_subgraph(
    center_work_id: str, nodes: list[dict[str, Any]], edges: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Induced subgraph: center ``Work`` and neighbors adjacent in ``edges``."""
    nids = {center_work_id}
    sub_edges: list[dict[str, Any]] = []
    for e in edges or []:
        src, tgt = str(e.get("source") or ""), str(e.get("target") or "")
        if src == center_work_id:
            nids.add(tgt)
        elif tgt == center_work_id:
            nids.add(src)
    sub_nodes = [n for n in (nodes or []) if str(n.get("id") or "") in nids]
    for e in edges or []:
        src, tgt = str(e.get("source") or ""), str(e.get("target") or "")
        if src in nids and tgt in nids:
            sub_edges.append(e)
    return sub_nodes, sub_edges


def work_graph_workspace_membership_by_work_id(payload: dict[str, Any]) -> dict[str, str]:
    """``Work.id`` → ``workspace_membership`` for nodes that carry the field (Phase 2)."""
    out: dict[str, str] = {}
    for n in payload.get("nodes") or []:
        if str(n.get("type") or "") != "Work":
            continue
        wid = str(n.get("id") or "")
        wm = str(n.get("workspace_membership") or "").strip()
        if wid and wm:
            out[wid] = wm
    return out
