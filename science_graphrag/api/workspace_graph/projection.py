from __future__ import annotations

import hashlib
import re
from typing import Any

from science_graphrag.api.graph_display import (
    compute_node_display,
    edge_display_type,
    resolve_node_kind,
)

ALLOWED_NODE_TYPES = frozenset(
    {"Work", "Author", "Method", "Dataset", "Venue", "Institution", "Authorship", "Claim"}
)
AGGREGATOR_THRESHOLD = 8


def merge_graph_payloads(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    nodes_by_id: dict[str, dict[str, Any]] = {}
    edges_by_key: dict[str, dict[str, Any]] = {}
    semantic_any = False
    truncated_any = False
    for g in payloads:
        if not g:
            continue
        if g.get("meta", {}).get("semantic_available"):
            semantic_any = True
        if g.get("meta", {}).get("is_truncated"):
            truncated_any = True
        for n in g.get("nodes") or []:
            nid = str(n.get("id") or "")
            if nid:
                nodes_by_id[nid] = n
        for e in g.get("edges") or []:
            eid = str(e.get("id") or "")
            if eid:
                edges_by_key[eid] = e
                continue
            src = str(e.get("source_id") or e.get("source") or "")
            tgt = str(e.get("target_id") or e.get("target") or "")
            rt = str(e.get("rel_type") or e.get("type") or "")
            key = f"{src}|{rt}|{tgt}"
            edges_by_key[key] = e
    nodes = list(nodes_by_id.values())
    edges = list(edges_by_key.values())
    return {
        "work_id": "",
        "nodes": nodes,
        "edges": edges,
        "meta": {
            "semantic_available": semantic_any,
            "graph_scope": "workspace_union_1hop",
            "graph_depth_effective": 1,
            "workspace_node_count": len(nodes),
            "workspace_edge_count": len(edges),
            "is_truncated": truncated_any,
            "available_expansions": [],
        },
    }


def _primary_label(labels: list[Any]) -> str:
    order = ["Work", "Author", "Method", "Dataset", "Venue", "Institution", "Authorship", "Claim", "Evidence"]
    labs = [str(x) for x in (labels or [])]
    for item in order:
        if item in labs:
            return item
    return labs[0] if labs else "Node"


def node_dict_from_neo(node: Any) -> dict[str, Any] | None:
    if node is None:
        return None
    props = dict(node)
    nid = props.get("id")
    if nid is None:
        nid = str(node.element_id)
    nid = str(nid).strip()
    if not nid:
        return None
    ntype = _primary_label(list(node.labels))
    raw_title = str(
        props.get("title")
        or props.get("name")
        or props.get("full_name")
        or props.get("normalized_text")
        or props.get("text")
        or ""
    ).strip()
    center_props: dict[str, Any] = {}
    if props.get("publication_year") is not None:
        center_props["publication_year"] = props["publication_year"]
    if props.get("doi"):
        center_props["doi"] = str(props["doi"]).strip()
    if props.get("arxiv_id"):
        center_props["arxiv_id"] = str(props["arxiv_id"]).strip()
    if props.get("venue_name"):
        center_props["venue"] = str(props["venue_name"]).strip()[:200]
    if props.get("country"):
        center_props["country"] = str(props["country"]).strip()[:120]
    if props.get("venue_type"):
        center_props["venue_type"] = str(props["venue_type"]).strip()[:120]
    if props.get("issn"):
        center_props["issn"] = str(props["issn"]).strip()[:64]
    if ntype == "Claim":
        nt = str(props.get("normalized_text") or "").strip()
        tx = str(props.get("text") or "").strip()
        if nt:
            center_props["normalized_text"] = nt
        if tx:
            center_props["text"] = tx
        for key in ("claim_type", "polarity", "confidence"):
            if props.get(key) is not None:
                center_props[key] = props[key]
        # Optional JSON / structured extension (future Neo4j fields); surfaced as-is for graph UI.
        for ext_key in ("claim_metadata", "metadata_json", "extension"):
            raw_ext = props.get(ext_key)
            if raw_ext is not None and raw_ext != "":
                center_props["claim_metadata"] = raw_ext
                break
    rendered = compute_node_display(ntype, raw_title, center_props)
    label = str(rendered["display_label"])
    subtitle = str(rendered["subtitle"])
    center_props = dict(rendered["properties"])
    return {
        "id": nid,
        "type": ntype,
        "label": label,
        "display_label": label,
        "subtitle": subtitle,
        "node_kind": resolve_node_kind(ntype),
        "properties": center_props,
    }


def edge_key(aid: str, rt: str, bid: str) -> str:
    return f"{aid}|{rt}|{bid}"


def edge_dict_from_rel(a: Any, b: Any, rel: Any, seq: int) -> dict[str, Any]:
    rt = str(rel.type) if rel is not None else ""
    src = str(dict(a).get("id") or a.element_id)
    tgt = str(dict(b).get("id") or b.element_id)
    payload = f"{src}\0{rt}\0{tgt}\0{seq}".encode()
    eid = "e_" + hashlib.sha256(payload).hexdigest()[:22]
    return {"id": eid, "source": src, "target": tgt, "type": rt}


def edge_dict_from_ids(src: str, tgt: str, rt: str, seq: int) -> dict[str, Any]:
    payload = f"{src}\0{rt}\0{tgt}\0{seq}".encode()
    eid = "e_" + hashlib.sha256(payload).hexdigest()[:22]
    return {"id": eid, "source": src, "target": tgt, "type": rt}


def enrich_edges_workspace(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> None:
    by_id = {n["id"]: n for n in nodes}
    for edge in edges:
        src_id = str(edge.get("source") or "")
        tgt_id = str(edge.get("target") or "")
        src_n = by_id.get(src_id, {})
        tgt_n = by_id.get(tgt_id, {})
        sl = str(src_n.get("display_label") or src_n.get("label") or src_id)
        tl = str(tgt_n.get("display_label") or tgt_n.get("label") or tgt_id)
        rt = str(edge.get("type") or "")
        disp_t = edge_display_type(rt)
        edge["display_type"] = disp_t
        edge["source_label"] = sl
        edge["target_label"] = tl
        edge["summary"] = f"{sl} —[{disp_t}]→ {tl}"
        edge["direction"] = "lateral"


def apply_workspace_node_kind(nodes: list[dict[str, Any]]) -> None:
    for n in nodes:
        ntype = str(n.get("type") or "")
        if ntype == "Work":
            wm = str(n.get("workspace_membership") or "")
            n["node_kind"] = resolve_node_kind("Work", workspace_membership=wm)
            continue
        n["node_kind"] = resolve_node_kind(ntype)


def annotate_membership_and_cites(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    internal_work_ids: set[str],
) -> tuple[int, int]:
    iws = {str(x) for x in internal_work_ids}

    def _outgoing_cite_targets(wid: str) -> list[str]:
        out: list[str] = []
        for e in edges:
            if str(e.get("type") or "") != "CITES":
                continue
            if str(e.get("source") or "") == wid:
                out.append(str(e.get("target") or ""))
        return out

    internal_nodes = 0
    external_nodes = 0
    for n in nodes:
        nid = str(n["id"])
        ntype = str(n.get("type") or "")
        if ntype == "Work":
            if nid in iws:
                n["workspace_membership"] = "internal"
                internal_nodes += 1
            else:
                n["workspace_membership"] = "external"
                external_nodes += 1
            targets = _outgoing_cite_targets(nid)
            internal_cite = sum(1 for t in targets if t in iws)
            external_cite = sum(1 for t in targets if t and t not in iws)
            n["internal_cite_count"] = internal_cite
            n["external_cite_count"] = external_cite
        else:
            attached_internal = False
            for e in edges:
                s, t = str(e.get("source") or ""), str(e.get("target") or "")
                if s != nid and t != nid:
                    continue
                other = t if s == nid else s
                if other in iws:
                    attached_internal = True
                    break
            n["workspace_membership"] = "internal" if attached_internal else "external"
            if n["workspace_membership"] == "internal":
                internal_nodes += 1
            else:
                external_nodes += 1
    return internal_nodes, external_nodes


def filter_external_works_by_min_citers(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    internal_work_ids: set[str],
    min_citers: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if min_citers <= 0:
        return nodes, edges
    iws = internal_work_ids
    cite_count: dict[str, set[str]] = {}
    for e in edges:
        if str(e.get("type") or "") != "CITES":
            continue
        s, t = str(e.get("source") or ""), str(e.get("target") or "")
        if s in iws and t not in iws:
            cite_count.setdefault(t, set()).add(s)
    drop_works = {w for w, srcs in cite_count.items() if len(srcs) < min_citers}
    if not drop_works:
        return nodes, edges
    new_nodes = [
        n
        for n in nodes
        if not (str(n.get("type")) == "Work" and n["id"] in drop_works and n["id"] not in iws)
    ]
    kept = {n["id"] for n in new_nodes}
    new_edges = [
        e
        for e in edges
        if str(e.get("source") or "") in kept and str(e.get("target") or "") in kept
    ]
    return new_nodes, new_edges


def parse_node_types_csv(raw: str | None) -> list[str] | None:
    if not raw or not str(raw).strip():
        return None
    parts = [p.strip() for p in re.split(r"[,;]", str(raw)) if p.strip()]
    cleaned = [p for p in parts if p in ALLOWED_NODE_TYPES]
    return cleaned or None


def merge_nodes_edges_lists(
    base_nodes: list[dict[str, Any]],
    base_edges: list[dict[str, Any]],
    extra_nodes: list[dict[str, Any]],
    extra_edges: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    nb = {n["id"]: n for n in base_nodes}
    for node in extra_nodes:
        nb.setdefault(node["id"], node)
    eb: dict[str, dict[str, Any]] = {}
    for edge in base_edges:
        eb[edge_key(str(edge["source"]), str(edge["type"]), str(edge["target"]))] = edge
    for edge in extra_edges:
        eb[edge_key(str(edge["source"]), str(edge["type"]), str(edge["target"]))] = edge
    return list(nb.values()), list(eb.values())


def apply_workspace_aggregators(
    workspace_id: str,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    *,
    threshold: int = AGGREGATOR_THRESHOLD,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    node_by_id = {str(n.get("id") or ""): n for n in nodes}
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for edge in edges:
        src = str(edge.get("source") or "")
        tgt = str(edge.get("target") or "")
        edge_type = str(edge.get("type") or "")
        if edge_type.upper() == "HAS_CLAIM":
            continue
        for owner_id, other_id in ((src, tgt), (tgt, src)):
            owner = node_by_id.get(owner_id)
            other = node_by_id.get(other_id)
            if not owner or not other or str(owner.get("type") or "") != "Work":
                continue
            other_kind = str(other.get("node_kind") or other.get("type") or "Node")
            groups.setdefault((owner_id, other_kind, edge_type), []).append(edge)
    remove_nodes: set[str] = set()
    remove_edges: set[str] = set()
    add_nodes: list[dict[str, Any]] = []
    add_edges: list[dict[str, Any]] = []
    for (owner_id, kind, edge_type), grouped_edges in groups.items():
        uniq_neighbors: list[str] = []
        seen: set[str] = set()
        for edge in grouped_edges:
            src = str(edge.get("source") or "")
            tgt = str(edge.get("target") or "")
            other = tgt if src == owner_id else src
            if not other or other in seen:
                continue
            seen.add(other)
            uniq_neighbors.append(other)
        if len(uniq_neighbors) < threshold:
            continue
        agg_id = f"agg:{owner_id.replace(':', '%3A')}:{kind.lower()}:{edge_type.upper()}"
        preview = [
            str(
                node_by_id.get(nid, {}).get("display_label")
                or node_by_id.get(nid, {}).get("label")
                or nid
            )
            for nid in uniq_neighbors[:3]
        ]
        add_nodes.append(
            {
                "id": agg_id,
                "type": "Aggregator",
                "node_kind": "Aggregator",
                "label": f"{len(uniq_neighbors)} {kind.lower()}",
                "display_label": f"{len(uniq_neighbors)} {kind.lower()}",
                "subtitle": "Click to expand",
                "properties": {},
                "aggregation_hints": {
                    "aggregator_kind": f"{kind.lower()}_of_work",
                    "count": len(uniq_neighbors),
                    "preview_labels": preview,
                    "expand_endpoint": f"/v1/workspaces/{workspace_id}/graph/expand?aggregator_id={agg_id}",
                },
            }
        )
        remove_nodes.update(uniq_neighbors)
        for edge in grouped_edges:
            remove_edges.add(str(edge.get("id") or ""))
        add_edges.append(
            {
                "id": "e_"
                + hashlib.sha256(f"{owner_id}\0AGGREGATED\0{agg_id}".encode()).hexdigest()[:22],
                "source": owner_id,
                "target": agg_id,
                "type": "AGGREGATED",
                "display_type": f"{len(uniq_neighbors)} {kind.lower()} of Work",
                "summary": f"{len(uniq_neighbors)} {kind.lower()} · click to expand",
                "direction": "outgoing",
            }
        )
    if not add_nodes:
        return nodes, edges
    kept_nodes = [n for n in nodes if str(n.get("id") or "") not in remove_nodes]
    kept_edges = [e for e in edges if str(e.get("id") or "") not in remove_edges]
    kept_ids = {str(n.get("id") or "") for n in kept_nodes}
    kept_edges = [
        e
        for e in kept_edges
        if str(e.get("source") or "") in kept_ids and str(e.get("target") or "") in kept_ids
    ]
    return kept_nodes + add_nodes, kept_edges + add_edges
