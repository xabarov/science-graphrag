"""Neighbor aggregation, row materialization, and edge display helpers for work graph."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from science_graphrag.api.graph_display import (
    compute_node_display,
    edge_display_type,
    resolve_node_kind,
)
from science_graphrag.api.graph_reader_projection.stable_edge_id import stable_graph_edge_id

AGGREGATOR_THRESHOLD = 8

# GR8: per-neighbor-kind defaults (Work-owned groups only; global override via query param).
KIND_AGG_THRESHOLDS: dict[str, int] = {
    "authorship": 4,
    "authorshipreification": 4,
    "author": 4,
    "institution": 5,
    "venue": 6,
    "work": 8,
    "method": 6,
    "dataset": 6,
}


def _normalize_kind_key(kind: str) -> str:
    return str(kind or "").lower().replace(" ", "").replace("_", "")


def _parse_aggregator_disabled_kinds(csv: str | None) -> frozenset[str]:
    if not csv or not str(csv).strip():
        return frozenset()
    out: set[str] = set()
    for part in str(csv).split(","):
        k = _normalize_kind_key(part)
        if k:
            out.add(k)
    return frozenset(out)


def _agg_threshold_for_neighbor(neighbor_kind: str, *, global_override: int | None) -> int:
    if global_override is not None:
        return max(2, min(int(global_override), 200))
    nk = _normalize_kind_key(neighbor_kind)
    for key, val in KIND_AGG_THRESHOLDS.items():
        if key in nk:
            return val
    return AGGREGATOR_THRESHOLD


def _has_semantic_layer_cypher() -> str:
    return (
        "(EXISTS { MATCH (w)-[:USES_METHOD]->(:Method) }) OR "
        "(EXISTS { MATCH (w)-[:EVALUATED_ON]->(:Dataset) })"
    )


def _neighborhood_edge_endpoints(
    center_id: str, neighbor_id: str, raw_src: str, raw_tgt: str
) -> tuple[str, str]:
    endpoints = {center_id, neighbor_id}
    if raw_src and raw_tgt and raw_src != raw_tgt and {raw_src, raw_tgt} == endpoints:
        return raw_src, raw_tgt
    return center_id, neighbor_id


def _aggregator_id(owner_id: str, node_kind: str, edge_type: str) -> str:
    encoded_owner = owner_id.replace(":", "%3A")
    return f"agg:{encoded_owner}:{node_kind.lower()}:{edge_type.upper()}"


def parse_aggregator_id(aggregator_id: str) -> tuple[str, str, str]:
    """Parse ``agg:<owner>:<node_kind>:<EDGE_TYPE>`` into owner id, kind, and edge type."""
    raw = str(aggregator_id or "").strip()
    if not raw.startswith("agg:"):
        raise ValueError("invalid_aggregator_id")
    _, owner_encoded, node_kind, edge_type = raw.split(":", 3)
    return owner_encoded.replace("%3A", ":"), node_kind, edge_type


def _apply_aggregators(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    work_id: str,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    *,
    global_threshold: int | None = None,
    disabled_kind_keys: frozenset[str] | None = None,
    workspace_id_for_expand: str | None = None,
    include_institutions_for_expand: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """GR8 dense-neighbor bucketing (legacy).

    **Not** invoked from ``graph_neighborhood_payload._work_graph_neighborhood_payload``
    (aggregation disabled 2026-04-28).
    Kept for ``tests/storage/test_graph_aggregators.py`` and optional future re-enable.
    """
    node_by_id = {str(n.get("id") or ""): n for n in nodes}
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for edge in edges:
        src_id = str(edge.get("source") or "")
        tgt_id = str(edge.get("target") or "")
        edge_type = str(edge.get("type") or "")
        if edge_type.upper() == "HAS_CLAIM":
            continue
        for owner_id, neighbor_id in ((src_id, tgt_id), (tgt_id, src_id)):
            owner = node_by_id.get(owner_id)
            neighbor = node_by_id.get(neighbor_id)
            if not owner or not neighbor:
                continue
            if str(owner.get("type") or "") != "Work":
                continue
            neighbor_kind = str(neighbor.get("node_kind") or neighbor.get("type") or "Node")
            nk_key = _normalize_kind_key(neighbor_kind)
            if disabled_kind_keys and nk_key in disabled_kind_keys:
                continue
            key = (owner_id, neighbor_kind, edge_type)
            groups.setdefault(key, []).append(edge)
    to_remove_nodes: set[str] = set()
    to_remove_edges: set[str] = set()
    add_nodes: list[dict[str, Any]] = []
    add_edges: list[dict[str, Any]] = []
    for (owner_id, node_kind, edge_type), grouped_edges in groups.items():
        uniq_neighbors: list[str] = []
        seen_neighbors: set[str] = set()
        for edge in grouped_edges:
            src_id = str(edge.get("source") or "")
            tgt_id = str(edge.get("target") or "")
            other = tgt_id if src_id == owner_id else src_id
            if not other or other in seen_neighbors:
                continue
            seen_neighbors.add(other)
            uniq_neighbors.append(other)
        thresh = _agg_threshold_for_neighbor(node_kind, global_override=global_threshold)
        if len(uniq_neighbors) < thresh:
            continue
        preview_labels = []
        for nid in uniq_neighbors[:3]:
            n = node_by_id.get(nid, {})
            preview_labels.append(str(n.get("display_label") or n.get("label") or nid))
        aggregator_id = _aggregator_id(owner_id, node_kind, edge_type)
        expand_ep = f"/v1/works/{work_id}/graph/expand?aggregator_id={aggregator_id}"
        ws_for_ex = str(workspace_id_for_expand or "").strip()
        if ws_for_ex:
            expand_ep += f"&workspace_id={quote(ws_for_ex, safe='')}"
        if include_institutions_for_expand:
            expand_ep += "&include_institutions=1"
        add_nodes.append(
            {
                "id": aggregator_id,
                "type": "Aggregator",
                "node_kind": "Aggregator",
                "label": f"{len(uniq_neighbors)} {node_kind.lower()}",
                "display_label": f"{len(uniq_neighbors)} {node_kind.lower()}",
                "subtitle": "Click to expand",
                "properties": {},
                "aggregation_hints": {
                    "aggregator_kind": f"{node_kind.lower()}_of_work",
                    "count": len(uniq_neighbors),
                    "preview_labels": preview_labels,
                    "expand_endpoint": expand_ep,
                },
            }
        )
        for edge in grouped_edges:
            to_remove_edges.add(str(edge.get("id") or ""))
        to_remove_nodes.update(uniq_neighbors)
        add_edges.append(
            {
                "id": stable_graph_edge_id(owner_id, "AGGREGATED", aggregator_id, len(add_edges)),
                "source": owner_id,
                "target": aggregator_id,
                "type": "AGGREGATED",
                "display_type": f"{len(uniq_neighbors)} {node_kind.lower()} of Work",
                "summary": f"{len(uniq_neighbors)} {node_kind.lower()} · click to expand",
                "direction": "outgoing",
            }
        )
    if not add_nodes:
        return nodes, edges
    kept_nodes = [n for n in nodes if str(n.get("id") or "") not in to_remove_nodes]
    kept_edges = [e for e in edges if str(e.get("id") or "") not in to_remove_edges]
    kept_node_ids = {str(n.get("id") or "") for n in kept_nodes}
    kept_edges = [
        e
        for e in kept_edges
        if str(e.get("source") or "") in kept_node_ids
        and str(e.get("target") or "") in kept_node_ids
    ]
    return kept_nodes + add_nodes, kept_edges + add_edges


def _append_neighbor_edge(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    center_id: str,
    rec: Any,
) -> None:
    labs = rec["labs"] or []
    ntype = str(labs[0]) if labs else "Node"
    nid = str(rec["nid"])
    props: dict[str, Any] = {}
    for key, src, ln in (
        ("publication_year", "n_pub_year", None),
        ("doi", "n_doi", 256),
        ("arxiv_id", "n_arxiv", 256),
        ("venue", "n_venue", 200),
        ("workspace_membership", "n_workspace_membership", 32),
        ("country", "n_country", 120),
        ("venue_type", "n_venue_type", 120),
        ("issn", "n_issn", 64),
    ):
        val = rec.get(src)
        if val is None:
            continue
        sval = str(val).strip()
        if sval:
            props[key] = sval[:ln] if ln else val
    rendered = compute_node_display(
        ntype,
        str(rec.get("nlabel") or "").strip(),
        props,
        authorship_extra=(
            {
                "author_position": rec.get("n_ash_pos"),
                "author_name": rec.get("n_ash_author"),
                "raw_affiliation": rec.get("n_ash_aff"),
                "institution_name": rec.get("n_ash_inst"),
                "is_corresponding": rec.get("n_ash_corr"),
            }
            if ntype == "Authorship"
            else None
        ),
    )
    workspace_membership = str(
        props.get("workspace_membership") or rec.get("n_workspace_membership") or ""
    ).strip()
    if not any(x["id"] == nid for x in nodes):
        nodes.append(
            {
                "id": nid,
                "type": ntype,
                "label": str(rendered["display_label"]),
                "display_label": str(rendered["display_label"]),
                "subtitle": str(rendered["subtitle"]),
                "node_kind": resolve_node_kind(ntype, workspace_membership=workspace_membership),
                "properties": dict(rendered["properties"]),
            }
        )
    src_id, tgt_id = _neighborhood_edge_endpoints(
        center_id,
        nid,
        str(rec.get("src_id") or "").strip(),
        str(rec.get("tgt_id") or "").strip(),
    )
    edges.append({"source": src_id, "target": tgt_id, "type": rec["rt"] or ""})
    _append_of_author_topology_from_row(nodes, edges, ntype=ntype, authorship_id=nid, rec=rec)


def _append_of_author_topology_from_row(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    *,
    ntype: str,
    authorship_id: str,
    rec: Any,
) -> None:
    """Materialize ``(Authorship)-[:OF_AUTHOR]->(Author)`` when Neo4j has the link (Option A)."""
    if str(ntype or "") != "Authorship":
        return
    author_id = str(rec.get("n_auth_id") or "").strip()
    if not author_id:
        return
    if not any(str(n.get("id") or "") == author_id for n in nodes):
        name = str(rec.get("n_ash_author") or "").strip()
        rendered = compute_node_display("Author", name, {})
        nodes.append(
            {
                "id": author_id,
                "type": "Author",
                "label": str(rendered["display_label"]),
                "display_label": str(rendered["display_label"]),
                "subtitle": str(rendered["subtitle"]),
                "node_kind": resolve_node_kind("Author"),
                "properties": dict(rendered["properties"]),
            }
        )
    for e in edges:
        if str(e.get("type") or "").upper() == "OF_AUTHOR" and str(e.get("source") or "") == str(
            authorship_id
        ):
            if str(e.get("target") or "") == str(author_id):
                return
    seq = len(edges)
    edges.append(
        {
            "source": authorship_id,
            "target": author_id,
            "type": "OF_AUTHOR",
            "id": stable_graph_edge_id(authorship_id, "OF_AUTHOR", author_id, seq),
        }
    )


def _enrich_edges_with_display(
    center_id: str, nodes: list[dict[str, Any]], edges: list[dict[str, Any]]
) -> None:
    by_id = {n["id"]: n for n in nodes}
    for seq, edge in enumerate(edges):
        src_id, tgt_id = str(edge.get("source") or ""), str(edge.get("target") or "")
        src_n, tgt_n = by_id.get(src_id, {}), by_id.get(tgt_id, {})
        sl = str(src_n.get("display_label") or src_n.get("label") or src_id)
        tl = str(tgt_n.get("display_label") or tgt_n.get("label") or tgt_id)
        rt = str(edge.get("type") or "")
        disp_t = edge_display_type(rt)
        edge["id"] = str(edge.get("id") or "").strip() or stable_graph_edge_id(
            src_id, rt, tgt_id, seq
        )
        edge["display_type"] = disp_t
        edge["source_label"] = sl
        edge["target_label"] = tl
        edge["summary"] = f"{sl} —[{disp_t}]→ {tl}"
        edge["direction"] = (
            "outgoing" if src_id == center_id else "incoming" if tgt_id == center_id else "lateral"
        )
