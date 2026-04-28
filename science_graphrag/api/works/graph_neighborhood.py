from __future__ import annotations

from typing import Any
from urllib.parse import quote

from neo4j import Session as Neo4jSession

from science_graphrag.api.deps import StoreRegistry
from science_graphrag.api.graph_display import (
    compute_node_display,
    edge_display_type,
    node_kind_priority,
    parse_priority_csv,
    resolve_node_kind,
)
from science_graphrag.api.graph_reader_meta import enrich_reader_graph_meta
from science_graphrag.api.graph_reader_projection.authorship_collapse import (
    build_authorship_to_reader_author_map,
    collapse_authorship_for_reader_view,
)
from science_graphrag.api.graph_reader_projection.authorship_enrich import enrich_authorship_nodes
from science_graphrag.api.graph_reader_projection.authorship_meta import (
    compute_authorship_projection_meta,
    strip_reader_only_authorship_properties,
)
from science_graphrag.api.graph_reader_projection.stable_edge_id import stable_graph_edge_id
from science_graphrag.api.workspace_graph.claims_projection import build_claim_graph_slice_for_work
from science_graphrag.api.workspace_graph.projection import (
    annotate_membership_and_cites,
    apply_workspace_node_kind,
    merge_nodes_edges_lists,
)

MAX_WORK_GRAPH_NEIGHBORS = 300
AGGREGATOR_THRESHOLD = 8
# Phase 3: optional Authorship–Institution hop merged into work graph JSON (ADR 011 addendum).
INSTITUTION_ATTACH_CAP = 32


def _fetch_work_authorship_institutions(
    session: Neo4jSession, work_id: str, cap: int
) -> list[dict[str, Any]]:
    lim = max(1, min(int(cap), 200))
    recs = session.run(
        """
        MATCH (w:Work {id: $wid})-[:HAS_AUTHORSHIP]->(ash:Authorship)-[:AFFILIATED_WITH]->(i:Institution)
        RETURN coalesce(ash.id, toString(elementId(ash))) AS ash_id,
               coalesce(i.id, toString(elementId(i))) AS inst_id,
               coalesce(i.name, '') AS inst_name,
               coalesce(i.country, '') AS inst_country
        LIMIT $lim
        """,
        wid=str(work_id).strip(),
        lim=lim,
    )
    return [dict(r) for r in recs]


def _attach_institutions_raw(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    rows: list[dict[str, Any]],
) -> int:
    """Attach ``Authorship–AFFILIATED_WITH–Institution`` for ``view=raw`` (Neo4j-shaped)."""
    node_ids = {str(n.get("id") or "") for n in nodes}
    node_ids.discard("")
    pair_seen: set[tuple[str, str]] = set()
    attached = 0
    seq = len(edges)
    for rec in rows:
        ash = str(rec.get("ash_id") or "").strip()
        iid = str(rec.get("inst_id") or "").strip()
        if not ash or not iid or ash not in node_ids:
            continue
        key = (ash, iid)
        if key in pair_seen:
            continue
        pair_seen.add(key)
        if iid not in node_ids:
            name = str(rec.get("inst_name") or "").strip()
            country = str(rec.get("inst_country") or "").strip()
            props: dict[str, Any] = {}
            if country:
                props["country"] = country
            rendered = compute_node_display("Institution", name, props)
            nodes.append(
                {
                    "id": iid,
                    "type": "Institution",
                    "label": str(rendered["display_label"]),
                    "display_label": str(rendered["display_label"]),
                    "subtitle": str(rendered["subtitle"]),
                    "node_kind": resolve_node_kind("Institution"),
                    "properties": dict(rendered["properties"]),
                    "distance": 2,
                }
            )
            node_ids.add(iid)
        edges.append(
            {
                "id": stable_graph_edge_id(ash, "AFFILIATED_WITH", iid, seq),
                "source": ash,
                "target": iid,
                "type": "AFFILIATED_WITH",
            }
        )
        seq += 1
        attached += 1
    return attached


def _attach_institutions_reader(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    ash_author_map: dict[str, str],
) -> int:
    """Attach ``Author–AFFILIATED_WITH–Institution`` after authorship collapse (reader projection)."""
    node_ids = {str(n.get("id") or "") for n in nodes}
    node_ids.discard("")
    pair_seen: set[tuple[str, str]] = set()
    attached = 0
    seq = len(edges)
    for rec in rows:
        ash = str(rec.get("ash_id") or "").strip()
        iid = str(rec.get("inst_id") or "").strip()
        author_id = str(ash_author_map.get(ash) or "").strip()
        if not author_id or not iid or author_id not in node_ids:
            continue
        key = (author_id, iid)
        if key in pair_seen:
            continue
        pair_seen.add(key)
        if iid not in node_ids:
            name = str(rec.get("inst_name") or "").strip()
            country = str(rec.get("inst_country") or "").strip()
            props: dict[str, Any] = {}
            if country:
                props["country"] = country
            rendered = compute_node_display("Institution", name, props)
            nodes.append(
                {
                    "id": iid,
                    "type": "Institution",
                    "label": str(rendered["display_label"]),
                    "display_label": str(rendered["display_label"]),
                    "subtitle": str(rendered["subtitle"]),
                    "node_kind": resolve_node_kind("Institution"),
                    "properties": dict(rendered["properties"]),
                    "distance": 2,
                }
            )
            node_ids.add(iid)
        edges.append(
            {
                "id": stable_graph_edge_id(author_id, "AFFILIATED_WITH", iid, seq),
                "source": author_id,
                "target": iid,
                "type": "AFFILIATED_WITH",
            }
        )
        seq += 1
        attached += 1
    return attached


def load_work_graph_workspace_internal_ids(
    session: Neo4jSession,
    *,
    workspace_id: str,
    center_work_id: str,
) -> tuple[set[str] | None, str | None]:
    """Load internal ``Work`` ids for workspace membership annotation.

    Returns ``(internal_ids, None)`` on success. On failure returns
    ``(None, "workspace_not_found")`` or ``(None, "work_not_in_workspace")``.
    """
    row = session.run(
        """
        MATCH (ws:Workspace {id: $wid})
        OPTIONAL MATCH (ws)-[:CONTAINS]->(cw:Work {id: $work_id})
        OPTIONAL MATCH (ws)-[:CONTAINS]->(iw:Work)
        RETURN ws.id AS wid,
               cw.id AS center_member,
               collect(DISTINCT iw.id) AS internal_ids
        """,
        wid=str(workspace_id).strip(),
        work_id=str(center_work_id).strip(),
    ).single()
    if not row or not str(row.get("wid") or "").strip():
        return None, "workspace_not_found"
    if not str(row.get("center_member") or "").strip():
        return None, "work_not_in_workspace"
    raw = row.get("internal_ids") or []
    iws = {str(x) for x in raw if x}
    return iws, None


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
    raw = str(aggregator_id or "").strip()
    if not raw.startswith("agg:"):
        raise ValueError("invalid_aggregator_id")
    _, owner_encoded, node_kind, edge_type = raw.split(":", 3)
    return owner_encoded.replace("%3A", ":"), node_kind, edge_type


def _apply_aggregators(
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

    **Not** invoked from ``_work_graph_neighborhood_payload`` (aggregation disabled 2026-04-28).
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


def _work_neighbors_rows(
    session: Neo4jSession,
    *,
    work_id: str,
    lim: int,
    priority_types: tuple[str, ...],
    prefer_priority: bool,
    exclude_ids: list[str] | None = None,
) -> list[Any]:
    q = """
        MATCH (w:Work {id: $id})-[r]-(n)
        WHERE ($prefer_priority AND any(l IN labels(n) WHERE l IN $priority_types))
           OR ((NOT $prefer_priority) AND NOT any(l IN labels(n) WHERE l IN $priority_types))
        """
    if exclude_ids:
        q += " AND NOT coalesce(n.id, toString(elementId(n))) IN $exclude_ids "
    q += """
        OPTIONAL MATCH (n)-[:OF_AUTHOR]->(auth:Author)
        OPTIONAL MATCH (n)-[:AFFILIATED_WITH]->(inst:Institution)
        RETURN coalesce(n.id, toString(elementId(n))) AS nid, labels(n) AS labs, type(r) AS rt,
               coalesce(n.title, n.name, n.full_name, '') AS nlabel,
               coalesce(startNode(r).id, toString(elementId(startNode(r)))) AS src_id,
               coalesce(endNode(r).id, toString(elementId(endNode(r)))) AS tgt_id,
               n.publication_year AS n_pub_year, coalesce(n.doi, '') AS n_doi, coalesce(n.arxiv_id, '') AS n_arxiv,
               coalesce(n.venue_name, '') AS n_venue, coalesce(n.country, '') AS n_country,
               coalesce(n.venue_type, '') AS n_venue_type, coalesce(n.issn, '') AS n_issn,
               n.author_position AS n_ash_pos, coalesce(n.raw_affiliation, '') AS n_ash_aff,
               n.is_corresponding AS n_ash_corr, coalesce(auth.full_name, '') AS n_ash_author,
               coalesce(inst.name, '') AS n_ash_inst,
               coalesce(auth.id, '') AS n_auth_id
        LIMIT $lim
    """
    params: dict[str, Any] = {
        "id": work_id,
        "lim": lim,
        "priority_types": list(priority_types),
        "prefer_priority": bool(prefer_priority),
    }
    if exclude_ids:
        params["exclude_ids"] = exclude_ids
    return list(session.run(q, **params))


def _work_graph_neighborhood_payload(
    session: Neo4jSession,
    work_id: str,
    *,
    neighbor_limit: int = 200,
    depth: int = 1,
    prioritize: str | None = None,
    view: str = "reader",
    workspace_id: str | None = None,
    workspace_internal_work_ids: set[str] | None = None,
    aggregator_threshold: int | None = None,
    aggregator_disabled_kinds: str | None = None,
    include_claims: bool = False,
    claims_limit: int = 24,
    include_authorship_debug: bool = False,
    include_institutions: bool = False,
) -> dict[str, Any] | None:
    # Query params kept for API stability; neighbor bucketing (GR8) is permanently off.
    _ = (aggregator_threshold, aggregator_disabled_kinds)
    row = session.run(
        """
        MATCH (w:Work {id: $id})
        RETURN w.id AS wid, coalesce(w.title, '') AS wtitle, w.publication_year AS wyear,
               coalesce(w.doi, '') AS wdoi, coalesce(w.arxiv_id, '') AS warxiv,
               coalesce(w.venue_name, '') AS wvenue,
        """
        + _has_semantic_layer_cypher()
        + """ AS has_semantic
        """,
        id=work_id,
    ).single()
    if not row:
        return None
    counts_row = session.run(
        """
        MATCH (w:Work {id: $id})
        OPTIONAL MATCH (wi:Work)-[:CITES]->(w)
        OPTIONAL MATCH (w)-[:CITES]->(wo:Work)
        OPTIONAL MATCH (w)-[:HAS_AUTHORSHIP]->(:Authorship)-[:OF_AUTHOR]->(auth:Author)
        RETURN count(DISTINCT wi) AS cites_in_count,
               count(DISTINCT wo) AS cites_out_count,
               count(DISTINCT auth) AS authors_count
        """,
        id=work_id,
    ).single()
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    center_id = str(row["wid"])
    cprops: dict[str, Any] = {}
    for k, v in (
        ("publication_year", row.get("wyear")),
        ("doi", str(row.get("wdoi") or "").strip()),
        ("arxiv_id", str(row.get("warxiv") or "").strip()),
        ("venue", str(row.get("wvenue") or "").strip()[:200]),
    ):
        if v:
            cprops[k] = v
    if counts_row:
        cprops["cites_in_count"] = int(counts_row.get("cites_in_count") or 0)
        cprops["cites_out_count"] = int(counts_row.get("cites_out_count") or 0)
        cprops["authors_count"] = int(counts_row.get("authors_count") or 0)
    cr = compute_node_display("Work", str(row.get("wtitle") or "").strip(), cprops)
    nodes.append(
        {
            "id": center_id,
            "type": "Work",
            "label": str(cr["display_label"]),
            "display_label": str(cr["display_label"]),
            "subtitle": str(cr["subtitle"]),
            "node_kind": resolve_node_kind("Work"),
            "properties": dict(cr["properties"]),
            "distance": 0,
        }
    )
    total_neighbors = int(
        session.run("MATCH (w:Work {id: $id})-[r]-(n) RETURN count(r) AS c", id=work_id).single()[
            "c"
        ]
    )
    kind_distribution: dict[str, int] = {
        str(rec["kind"] or "Unknown"): int(rec["c"])
        for rec in session.run(
            "MATCH (w:Work {id: $id})-[r]-(n) WITH labels(n) AS labs, count(r) AS c "
            "RETURN labs[0] AS kind, c",
            id=work_id,
        )
    }
    depth_req = max(1, min(int(depth), 3))
    cap = min(MAX_WORK_GRAPH_NEIGHBORS, max(1, min(int(neighbor_limit), 2000)))
    hop1_lim, hop2_lim, effective_depth = (
        (cap, 0, 1)
        if depth_req <= 1
        else (max(1, (cap * 2) // 3), max(1, cap - max(1, (cap * 2) // 3)), 2)
    )
    priority_types = parse_priority_csv(prioritize)
    primary_rows = _work_neighbors_rows(
        session, work_id=work_id, lim=hop1_lim, priority_types=priority_types, prefer_priority=True
    )
    primary_take = min(len(primary_rows), max(hop1_lim // 2, hop1_lim - 50))
    primary_used = primary_rows[:primary_take]
    taken_ids = [str(rec.get("nid") or "") for rec in primary_used if str(rec.get("nid") or "")]
    secondary_rows: list[Any] = []
    if hop1_lim - len(primary_used) > 0:
        secondary_rows = _work_neighbors_rows(
            session,
            work_id=work_id,
            lim=hop1_lim - len(primary_used),
            priority_types=priority_types,
            prefer_priority=False,
            exclude_ids=taken_ids,
        )
    for rec in [*primary_used, *secondary_rows]:
        _append_neighbor_edge(nodes, edges, center_id, rec)
    for n in nodes[1:]:
        n.setdefault("distance", 1)
    if effective_depth >= 2 and hop2_lim > 0:
        hop1_work_ids = [
            str(n["id"])
            for n in nodes
            if str(n.get("type") or "") == "Work" and str(n.get("id") or "") != center_id
        ][:30]
        h1_ids = [str(n["id"]) for n in nodes]
        if hop1_work_ids:
            for rec in session.run(
                """
                UNWIND $h1 AS wid
                MATCH (w:Work {id: wid})-[r:CITES]-(n:Work)
                WHERE n.id <> $center AND NOT n.id IN $h1set
                RETURN coalesce(n.id, toString(elementId(n))) AS nid,
                       labels(n) AS labs, type(r) AS rt,
                       coalesce(n.name, n.full_name, n.title, '') AS nlabel,
                       coalesce(startNode(r).id, toString(elementId(startNode(r)))) AS src_id,
                       coalesce(endNode(r).id, toString(elementId(endNode(r)))) AS tgt_id,
                       n.publication_year AS n_pub_year, coalesce(n.doi, '') AS n_doi,
                       coalesce(n.arxiv_id, '') AS n_arxiv,
                       coalesce(n.venue_name, '') AS n_venue
                LIMIT $lim2
                """,
                h1=hop1_work_ids,
                center=center_id,
                h1set=h1_ids,
                lim2=hop2_lim,
            ):
                nid = str(rec["nid"] or "")
                if not nid or any(x["id"] == nid for x in nodes):
                    continue
                _append_neighbor_edge(nodes, edges, center_id, rec)
                for n in nodes:
                    if n.get("id") == nid:
                        n["distance"] = 2
                        break
    center_node = next((n for n in nodes if str(n.get("id") or "") == center_id), None)
    neighbor_nodes = [n for n in nodes if str(n.get("id") or "") != center_id]
    neighbor_nodes.sort(
        key=lambda n: (node_kind_priority(str(n.get("node_kind") or "")), str(n.get("id") or ""))
    )
    skipped_by_kind: dict[str, int] = {}
    if len(neighbor_nodes) > cap:
        neighbor_nodes = neighbor_nodes[:cap]
    # Compute skipped counts from graph-level kind distribution vs what is returned.
    # This covers both cap-truncated and never-fetched nodes.
    if kind_distribution:
        fetched_by_type: dict[str, int] = {}
        for node in neighbor_nodes:
            t = str(node.get("type") or "Unknown")
            fetched_by_type[t] = fetched_by_type.get(t, 0) + 1
        for kind, available in kind_distribution.items():
            fetched = fetched_by_type.get(kind, 0)
            if available > fetched:
                skipped_by_kind[kind] = available - fetched
    kept_ids = {center_id, *[str(n.get("id") or "") for n in neighbor_nodes]}
    nodes = ([center_node] if center_node else []) + neighbor_nodes
    edges = [
        e
        for e in edges
        if str(e.get("source") or "") in kept_ids and str(e.get("target") or "") in kept_ids
    ]
    claims_meta: dict[str, Any] = {"include_claims": bool(include_claims), "claims_included": False}
    if include_claims:
        cn, ce, cm = build_claim_graph_slice_for_work(
            session,
            work_id,
            claims_limit=max(1, min(int(claims_limit), 120)),
        )
        nodes, edges = merge_nodes_edges_lists(nodes, edges, cn, ce)
        claims_meta = {"include_claims": True, "claims_included": True, **cm}
    enrich_authorship_nodes(session, nodes)
    vnorm = str(view or "reader").strip().lower()
    inst_rows: list[dict[str, Any]] = []
    if include_institutions:
        inst_rows = _fetch_work_authorship_institutions(session, work_id, INSTITUTION_ATTACH_CAP)
    ash_author_map: dict[str, str] = {}
    if include_institutions and vnorm == "reader":
        ash_author_map = build_authorship_to_reader_author_map(nodes, edges, center_id)
    institutions_attached = 0
    if vnorm == "raw":
        strip_reader_only_authorship_properties(nodes)
    if include_institutions and vnorm == "raw":
        institutions_attached = _attach_institutions_raw(nodes, edges, inst_rows)
    if vnorm == "reader":
        nodes, edges = collapse_authorship_for_reader_view(nodes, edges, center_id)
    if include_institutions and vnorm == "reader":
        institutions_attached = _attach_institutions_reader(nodes, edges, inst_rows, ash_author_map)
    reader_authorship_projection = (
        compute_authorship_projection_meta(center_id, edges) if vnorm == "reader" else None
    )
    _enrich_edges_with_display(center_id, nodes, edges)
    # GR8 neighbor aggregation disabled (2026-04-28): return concrete nodes within neighbor caps;
    # ``aggregator_threshold`` / ``aggregator_disabled_kinds`` query params are accepted but ignored.
    if workspace_internal_work_ids is not None and str(workspace_id or "").strip():
        annotate_membership_and_cites(nodes, edges, workspace_internal_work_ids)
        apply_workspace_node_kind(nodes)
    truncated = bool(skipped_by_kind) or total_neighbors > hop1_lim
    expansions = ["increase_neighbor_limit"] if truncated else []
    if depth_req > effective_depth:
        expansions.append("multi_hop_depth")
    meta: dict[str, Any] = {
        "neighbor_aggregation": "none",
        "semantic_available": bool(row["has_semantic"]),
        "graph_scope": "work_2hop" if effective_depth >= 2 else "work_1hop",
        "graph_depth_requested": int(depth),
        "graph_depth_effective": effective_depth,
        "neighbor_match_count": total_neighbors,
        "neighbor_limit_applied": hop1_lim + (hop2_lim if effective_depth >= 2 else 0),
        "nodes_returned": len(nodes),
        "edges_returned": len(edges),
        "is_truncated": truncated,
        "skipped_by_kind": skipped_by_kind if skipped_by_kind else {},
        "available_expansions": expansions,
        "include_institutions": bool(include_institutions),
        **claims_meta,
    }
    if include_institutions:
        meta["reader_extra_hops"] = ["institution"]
        meta["institutions"] = {
            "cap": INSTITUTION_ATTACH_CAP,
            "returned": int(institutions_attached),
        }
    _ws_ctx = workspace_internal_work_ids is not None and bool(str(workspace_id or "").strip())
    enrich_reader_graph_meta(
        meta,
        neighbor_limit=int(neighbor_limit),
        prioritize=prioritize,
        view=view,
        workspace_id=workspace_id,
        graph_mode="work_workspace_context" if _ws_ctx else None,
    )
    if include_authorship_debug and reader_authorship_projection is not None:
        meta["authorship_projection"] = reader_authorship_projection
    return {
        "work_id": work_id,
        "nodes": nodes,
        "edges": edges,
        "meta": meta,
    }


def work_graph_neighborhood(
    stores: StoreRegistry | Any,
    work_id: str,
    *,
    neighbor_limit: int = 200,
    depth: int = 1,
    prioritize: str | None = None,
    view: str = "reader",
    workspace_id: str | None = None,
    workspace_internal_work_ids: set[str] | None = None,
    aggregator_threshold: int | None = None,
    aggregator_disabled_kinds: str | None = None,
    include_claims: bool = False,
    claims_limit: int = 24,
    include_authorship_debug: bool = False,
    include_institutions: bool = False,
) -> dict[str, Any] | None:
    # Backward compatibility: older callers pass Settings instead of StoreRegistry.
    if not hasattr(stores, "neo4j"):
        from science_graphrag.storage.neo4j_store import Neo4jGraphStore

        temp = Neo4jGraphStore(stores.neo4j_uri, stores.neo4j_user, stores.neo4j_password)
        try:
            with temp.session() as session:
                return _work_graph_neighborhood_payload(
                    session,
                    work_id,
                    neighbor_limit=neighbor_limit,
                    depth=depth,
                    prioritize=prioritize,
                    view=view,
                    workspace_id=workspace_id,
                    workspace_internal_work_ids=workspace_internal_work_ids,
                    aggregator_threshold=aggregator_threshold,
                    aggregator_disabled_kinds=aggregator_disabled_kinds,
                    include_claims=include_claims,
                    claims_limit=claims_limit,
                    include_authorship_debug=include_authorship_debug,
                    include_institutions=include_institutions,
                )
        finally:
            temp.close()
    with stores.neo4j.session() as session:
        return _work_graph_neighborhood_payload(
            session,
            work_id,
            neighbor_limit=neighbor_limit,
            depth=depth,
            prioritize=prioritize,
            view=view,
            workspace_id=workspace_id,
            workspace_internal_work_ids=workspace_internal_work_ids,
            aggregator_threshold=aggregator_threshold,
            aggregator_disabled_kinds=aggregator_disabled_kinds,
            include_claims=include_claims,
            claims_limit=claims_limit,
            include_authorship_debug=include_authorship_debug,
            include_institutions=include_institutions,
        )


def expand_work_aggregator(
    stores: StoreRegistry | Any,
    work_id: str,
    aggregator_id: str,
    *,
    limit: int = 50,
    workspace_id: str | None = None,
    workspace_internal_work_ids: set[str] | None = None,
    include_institutions: bool = False,
) -> dict[str, Any] | None:
    owner_id, node_kind, edge_type = parse_aggregator_id(aggregator_id)
    # Reader collapse uses virtual Work—[AUTHORED]→Author edges; raw payload has
    # HAS_AUTHORSHIP→Authorship instead. Re-fetch reader with author aggregation disabled
    # so expand returns the same logical neighbors as the pre-aggregation graph.
    use_reader_authored = (
        str(edge_type or "").upper() == "AUTHORED"
        and str(node_kind or "").lower() == "author"
        and str(owner_id or "").strip() == str(work_id or "").strip()
    )
    payload = work_graph_neighborhood(
        stores,
        work_id,
        neighbor_limit=max(200, limit * 4),
        depth=1,
        prioritize="Method,Dataset,Work,Author,Authorship,Institution,Venue",
        view="reader" if use_reader_authored else "raw",
        workspace_id=workspace_id,
        workspace_internal_work_ids=workspace_internal_work_ids,
        aggregator_disabled_kinds="Author" if use_reader_authored else None,
        include_institutions=include_institutions,
    )
    if not payload:
        return None
    nodes = list(payload.get("nodes") or [])
    edges = list(payload.get("edges") or [])
    node_by_id = {str(n.get("id") or ""): n for n in nodes}
    picked_nodes: list[dict[str, Any]] = []
    picked_edges: list[dict[str, Any]] = []
    for edge in edges:
        src = str(edge.get("source") or "")
        tgt = str(edge.get("target") or "")
        rt = str(edge.get("type") or "").upper()
        if rt != edge_type.upper():
            continue
        if src == owner_id:
            other = tgt
        elif tgt == owner_id:
            other = src
        else:
            continue
        node = node_by_id.get(other)
        kind = str(node.get("node_kind") or node.get("type") or "").lower() if node else ""
        if kind != node_kind.lower():
            continue
        picked_edges.append(edge)
        if node:
            picked_nodes.append(node)
        if len(picked_nodes) >= max(1, int(limit)):
            break
    uniq_nodes = {owner_id: node_by_id.get(owner_id)}
    for node in picked_nodes:
        uniq_nodes[str(node.get("id") or "")] = node
    final_nodes = [n for n in uniq_nodes.values() if n]
    kept_ids = {str(n.get("id") or "") for n in final_nodes}
    final_edges = [
        e
        for e in picked_edges
        if str(e.get("source") or "") in kept_ids and str(e.get("target") or "") in kept_ids
    ]
    expand_meta: dict[str, Any] = {"expanded_aggregator_id": aggregator_id}
    _ws_norm = str(workspace_id or "").strip() or None
    enrich_reader_graph_meta(
        expand_meta,
        neighbor_limit=max(200, limit * 4),
        prioritize="Method,Dataset,Work,Author,Authorship,Institution,Venue",
        view="reader" if use_reader_authored else "raw",
        workspace_id=_ws_norm,
        graph_mode="work_expand_aggregator",
    )
    pm = payload.get("meta") or {}
    expand_meta["include_institutions"] = bool(include_institutions)
    if include_institutions:
        if pm.get("reader_extra_hops"):
            expand_meta["reader_extra_hops"] = list(pm["reader_extra_hops"])
        if pm.get("institutions"):
            expand_meta["institutions"] = dict(pm["institutions"])
    return {
        "nodes": final_nodes,
        "edges": final_edges,
        "meta": expand_meta,
    }
