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
    *,
    synthetic_owner_work_id: str,
) -> tuple[str, list[str], bool]:
    """Resolve ``Author`` id, ``via`` trace, and whether the id is a reader-only surrogate.

    ``synthetic_owner_work_id`` is the :Work id from ``HAS_AUTHORSHIP`` (hash salt for ``va:`` ids).
    """
    aid = str(author_by_ash.get(ash_id) or "").strip()
    if aid:
        return aid, ["HAS_AUTHORSHIP", "OF_AUTHOR"], False
    rawp = (n_ash or {}).get("properties") or {}
    aid = str(rawp.get("author_entity_id") or "").strip()
    if aid:
        return aid, ["HAS_AUTHORSHIP", "enriched_authorship"], False
    return (
        _reader_synthetic_author_entity_id(synthetic_owner_work_id, ash_id),
        ["HAS_AUTHORSHIP", "enriched_authorship"],
        True,
    )


def build_authorship_to_reader_author_map(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    center_work_id: str,
) -> dict[str, str]:
    """Map each center-work :Authorship id to the reader ``Author`` id used after collapse.

    Must be computed on the **pre-collapse** enriched graph (same inputs as
    ``collapse_authorship_for_reader_view``). Used to attach Institution nodes
    post-collapse as ``Author–AFFILIATED_WITH→Institution``.
    """
    authorship_ids = {
        str(n.get("id") or "")
        for n in nodes
        if str(n.get("type") or "") == "Authorship"
        or str(n.get("node_kind") or "") == "AuthorshipReification"
    }
    authorship_ids.discard("")
    if not authorship_ids:
        return {}

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

    node_by_id = {str(n.get("id") or ""): n for n in nodes}
    out: dict[str, str] = {}
    cid = str(center_work_id).strip()
    for ash_id, wid in work_by_ash.items():
        if str(wid).strip() != cid:
            continue
        n_ash = node_by_id.get(ash_id)
        aid, _, _ = _reader_view_authored_target(
            ash_id, author_by_ash, n_ash, synthetic_owner_work_id=str(wid).strip()
        )
        if aid:
            out[str(ash_id)] = str(aid)
    return out


def collapse_authorship_for_reader_multicenter(  # pylint: disable=too-many-locals
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    *,
    focal_work_id: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """GR9 for payloads with many :Work owners (workspace graph).

    Synthetic ``va:`` author ids hash with the owning work id from ``HAS_AUTHORSHIP``, not a
    single global center. When ``focal_work_id`` is set, ``AUTHORED`` edges from that work use
    ``direction=outgoing``; others ``lateral``. If omitted, all use ``outgoing``.
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
    focal = str(focal_work_id or "").strip() or None
    ash_to_reader_author: dict[str, str] = {}

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
        wid_s = str(wid).strip()
        n_ash = node_by_id.get(ash_id)
        props = _authorship_props_for_authored_edge(n_ash)
        aid, via, synthetic = _reader_view_authored_target(
            ash_id, author_by_ash, n_ash, synthetic_owner_work_id=wid_s
        )
        ensure_author_node(aid, n_ash, synthetic=synthetic)
        ash_to_reader_author[str(ash_id)] = str(aid)
        outgoing = not focal or wid_s == focal
        virtual_edges.append(
            {
                "id": stable_graph_edge_id(wid_s, "AUTHORED", aid, seq),
                "source": wid_s,
                "target": aid,
                "type": "AUTHORED",
                "via": via,
                "properties": props,
                "direction": "outgoing" if outgoing else "lateral",
            }
        )
        seq += 1

    def _is_institution_node(n: dict[str, Any] | None) -> bool:
        if not n:
            return False
        return (
            str(n.get("type") or "") == "Institution"
            or str(n.get("node_kind") or "") == "Institution"
        )

    institution_edges: list[dict[str, Any]] = []
    inst_seq = 0
    for e in edges:
        if str(e.get("type") or "").upper() != "AFFILIATED_WITH":
            continue
        s = str(e.get("source") or "")
        t = str(e.get("target") or "")
        ash_nid = ""
        inst_nid = ""
        if s in authorship_ids and t not in authorship_ids:
            ash_nid, inst_nid = s, t
        elif t in authorship_ids and s not in authorship_ids:
            ash_nid, inst_nid = t, s
        else:
            continue
        reader_author = ash_to_reader_author.get(ash_nid)
        if not reader_author or not inst_nid:
            continue
        inst_node = node_by_id.get(inst_nid)
        if not _is_institution_node(inst_node):
            continue
        institution_edges.append(
            {
                "id": stable_graph_edge_id(
                    reader_author, "AFFILIATED_WITH", inst_nid, 5000 + inst_seq
                ),
                "source": reader_author,
                "target": inst_nid,
                "type": "AFFILIATED_WITH",
                "via": ["Authorship", "AFFILIATED_WITH"],
                "direction": "outgoing",
            }
        )
        inst_seq += 1

    new_nodes = [n for n in nodes if str(n.get("id") or "") not in authorship_ids]
    new_nodes.extend(author_nodes_to_add)
    new_edges = [
        e
        for e in edges
        if str(e.get("source") or "") not in authorship_ids
        and str(e.get("target") or "") not in authorship_ids
    ]
    new_edges.extend(virtual_edges)
    new_edges.extend(institution_edges)
    return new_nodes, new_edges


def collapse_authorship_for_reader_view(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    center_work_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """GR9: drop :Authorship reification; add virtual Work–[AUTHORED]→ Author.

    ``via`` records how each edge was derived. Without ``OF_AUTHOR`` in the payload
    (standalone work graph), uses ``author_entity_id`` from ``enrich_authorship_nodes``
    or a stable synthetic surrogate so reader view never drops authorship silently.

    Thin wrapper over :func:`collapse_authorship_for_reader_multicenter` with a focal work
    (the viewed paper) for edge ``direction`` labels.
    """
    return collapse_authorship_for_reader_multicenter(
        nodes, edges, focal_work_id=str(center_work_id or "").strip() or None
    )
