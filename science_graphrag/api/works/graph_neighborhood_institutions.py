"""Institution attachment for work-graph neighborhood (raw vs reader projection)."""

from __future__ import annotations

from typing import Any

from neo4j import Session as Neo4jSession

from science_graphrag.api.graph_display import compute_node_display, resolve_node_kind
from science_graphrag.api.graph_reader_projection.stable_edge_id import stable_graph_edge_id

# Phase 3: optional Authorship–Institution hop merged into work graph JSON (ADR 011 addendum).
INSTITUTION_ATTACH_CAP = 32


def fetch_work_authorship_institutions(
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


def attach_institutions_raw(
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


def attach_institutions_reader(
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


__all__ = [
    "INSTITUTION_ATTACH_CAP",
    "attach_institutions_raw",
    "attach_institutions_reader",
    "fetch_work_authorship_institutions",
]
