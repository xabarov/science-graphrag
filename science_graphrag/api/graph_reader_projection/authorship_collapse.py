"""GR9: collapse Authorship reification into Work–[AUTHORED]→ Author for reader view."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from science_graphrag.api.graph_reader_projection.constants import (
    READER_SYNTHETIC_AUTHOR_HASH_MARKER,
    READER_SYNTHETIC_AUTHOR_ID_PREFIX,
)
from science_graphrag.api.graph_reader_projection.stable_edge_id import stable_graph_edge_id


def _reader_synthetic_author_entity_id(center_work_id: str, ash_id: str) -> str:
    """Stable surrogate ``Author.id`` when the graph payload has no ``OF_AUTHOR`` edges.

    The synthetic prefix avoids collisions with canonical UUID ``Author`` ids from Neo4j.
    """
    payload = (f"{center_work_id}\0{ash_id}\0{READER_SYNTHETIC_AUTHOR_HASH_MARKER}").encode()
    return READER_SYNTHETIC_AUTHOR_ID_PREFIX + hashlib.sha256(payload).hexdigest()[:22]


def _author_label_from_authorship_node(n_ash: dict[str, Any] | None) -> str:
    """Human label for a virtual Author node (aligned with UI author projection)."""
    if not n_ash:
        return "Unknown author"
    dl = str(n_ash.get("display_label") or n_ash.get("label") or "").strip()
    dl = re.sub(r"\s*\(#\d+\)\s*$", "", dl).strip()
    if dl:
        return dl[:200]
    rawp = n_ash.get("properties") or {}
    pos = rawp.get("author_position")
    if pos is not None:
        try:
            return f"Author #{int(pos)}"
        except (TypeError, ValueError):
            return "Unknown author"
    return "Unknown author"


def _authorship_props_for_authored_edge(n_ash: dict[str, Any] | None) -> dict[str, Any]:
    """Copy display-oriented fields onto virtual ``AUTHORED`` edges (not ``author_entity_id``)."""
    if not n_ash:
        return {}
    rawp = n_ash.get("properties") or {}
    props: dict[str, Any] = {}
    for key in ("author_position", "is_corresponding", "raw_affiliation", "institution_name"):
        if key in rawp and rawp[key] is not None:
            props[key] = rawp[key]
    return props


def _reader_view_authored_target(
    ash_id: str,
    author_by_ash: dict[str, str],
    n_ash: dict[str, Any] | None,
    center_work_id: str,
) -> tuple[str, list[str], bool]:
    """Resolve ``Author`` id, ``via`` trace, and whether the id is a reader-only surrogate."""
    aid = str(author_by_ash.get(ash_id) or "").strip()
    if aid:
        return aid, ["HAS_AUTHORSHIP", "OF_AUTHOR"], False
    rawp = (n_ash or {}).get("properties") or {}
    aid = str(rawp.get("author_entity_id") or "").strip()
    if aid:
        return aid, ["HAS_AUTHORSHIP", "enriched_authorship"], False
    return (
        _reader_synthetic_author_entity_id(center_work_id, ash_id),
        ["HAS_AUTHORSHIP", "enriched_authorship"],
        True,
    )


def collapse_authorship_for_reader_view(  # pylint: disable=too-many-locals
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    center_work_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """GR9: drop :Authorship reification; add virtual Work–[AUTHORED]→ Author.

    ``via`` records how each edge was derived. Without ``OF_AUTHOR`` in the payload
    (standalone work graph), uses ``author_entity_id`` from ``enrich_authorship_nodes``
    or a stable synthetic surrogate so reader view never drops authorship silently.
    """

    authorship_ids = {
        str(n.get("id") or "")
        for n in nodes
        if str(n.get("type") or "") == "Authorship"
        or str(n.get("node_kind") or "") == "AuthorshipReification"
    }
    authorship_ids.discard("")
    if not authorship_ids:
        return nodes, edges

    work_by_ash: dict[str, str] = {}
    author_by_ash: dict[str, str] = {}
    for edge in edges:
        rt = str(edge.get("type") or "").upper()
        src_id = str(edge.get("source") or "")
        tgt_id = str(edge.get("target") or "")
        if rt == "HAS_AUTHORSHIP":
            if tgt_id in authorship_ids:
                work_by_ash[tgt_id] = src_id
            elif src_id in authorship_ids:
                work_by_ash[src_id] = tgt_id
        elif rt == "OF_AUTHOR":
            if src_id in authorship_ids:
                author_by_ash[src_id] = tgt_id
            elif tgt_id in authorship_ids:
                author_by_ash[tgt_id] = src_id

    virtual_edges: list[dict[str, Any]] = []
    author_nodes_to_add: list[dict[str, Any]] = []
    author_ids_with_node: set[str] = {
        str(n.get("id") or "")
        for n in nodes
        if str(n.get("type") or "") == "Author" or str(n.get("node_kind") or "") == "Author"
    }
    author_ids_with_node.discard("")

    node_by_id = {str(n.get("id") or ""): n for n in nodes}
    seq = 0

    def ensure_author_node(aid: str, n_ash: dict[str, Any] | None, *, synthetic: bool) -> None:
        if not aid or aid in author_ids_with_node:
            return
        label = _author_label_from_authorship_node(n_ash)
        node: dict[str, Any] = {
            "id": aid,
            "type": "Author",
            "node_kind": "Author",
            "label": label,
            "display_label": label,
            "subtitle": "Author",
            "properties": {},
            "distance": 1,
        }
        if synthetic:
            node["raw"] = {
                "type": "Author",
                "node_kind": "Author",
                "synthesized_from": "Authorship",
            }
        author_nodes_to_add.append(node)
        author_ids_with_node.add(aid)

    for ash_id, wid in work_by_ash.items():
        if not wid:
            continue
        n_ash = node_by_id.get(ash_id)
        props = _authorship_props_for_authored_edge(n_ash)
        aid, via, synthetic = _reader_view_authored_target(
            ash_id, author_by_ash, n_ash, center_work_id
        )
        ensure_author_node(aid, n_ash, synthetic=synthetic)
        virtual_edges.append(
            {
                "id": stable_graph_edge_id(wid, "AUTHORED", aid, seq),
                "source": wid,
                "target": aid,
                "type": "AUTHORED",
                "via": via,
                "properties": props,
                "direction": "outgoing" if wid == center_work_id else "lateral",
            }
        )
        seq += 1

    new_nodes = [n for n in nodes if str(n.get("id") or "") not in authorship_ids]
    new_nodes.extend(author_nodes_to_add)
    new_edges = [
        e
        for e in edges
        if str(e.get("source") or "") not in authorship_ids
        and str(e.get("target") or "") not in authorship_ids
    ]
    new_edges.extend(virtual_edges)
    return new_nodes, new_edges
