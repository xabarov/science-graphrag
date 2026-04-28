"""Graph node display helpers shared across graph API projections."""

from __future__ import annotations

import re
from typing import Any

from neo4j import Session as Neo4jSession

UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{12}"
    r"(?::[A-Za-z0-9._-]+)*$",
)

EDGE_DISPLAY_TYPE_RAW: dict[str, str] = {
    # Authorship cluster
    "HAS_AUTHORSHIP": "authored by",
    "AUTHORED": "authored by",
    "OF_AUTHOR": "is author of",
    "AFFILIATED_WITH": "affiliated with",
    # Content relationships
    "CITES": "cites",
    "PUBLISHED_IN": "published in",
    # Workspace membership (workspace graph projections)
    "CONTAINS": "contains",
    # Semantic relationships
    "USES_METHOD": "uses method",
    "EVALUATED_ON": "evaluated on",
    "TRAINED_OR_TESTED_ON": "trained/tested on",
    # Claims
    "SUPPORTS": "supports",
    "CONTRADICTS": "contradicts",
    "MENTIONS": "mentions",
    "HAS_CLAIM": "has claim",
}

# Reader-oriented phrasing (subset overrides; see backlog graph_display EDGE_DISPLAY_TYPE_READER).
EDGE_DISPLAY_TYPE_READER: dict[str, str] = {
    **EDGE_DISPLAY_TYPE_RAW,
    "CITES": "references",
    "AUTHORED": "wrote",
    "HAS_AUTHORSHIP": "listed as author",
}

PRIORITY_NEIGHBOR_KINDS_DEFAULT: tuple[str, ...] = ("Method", "Dataset", "Work")
_NODE_KIND_PRIORITY: dict[str, int] = {
    "Work": 0,
    "WorkInternal": 0,
    "WorkExternal": 0,
    "Method": 1,
    "Dataset": 2,
    "Author": 3,
    "AuthorshipReification": 4,
    "Venue": 5,
    "Institution": 5,
    "Aggregator": 6,
    "Claim": 7,
    "Evidence": 7,
}


def _is_uuid_like(value: str) -> bool:
    s = (value or "").strip()
    return bool(s and UUID_RE.match(s))


def _clean_label(value: str) -> str:
    return (value or "").strip()[:200]


def edge_display_type(rel_type: str, *, view: str = "raw") -> str:
    """Map relation type to human-readable label."""
    key = (rel_type or "").strip().upper()
    if not key:
        return "related"
    view_norm = (view or "").strip().lower()
    mapping = EDGE_DISPLAY_TYPE_READER if view_norm == "reader" else EDGE_DISPLAY_TYPE_RAW
    if key in mapping:
        return mapping[key]
    return key.replace("_", " ").lower()


def resolve_node_kind(node_type: str, *, workspace_membership: str | None = None) -> str:
    """Return UI-oriented node kind independent from raw Neo4j label."""
    ntype = (node_type or "").strip() or "Node"
    if ntype == "Authorship":
        return "AuthorshipReification"
    if ntype == "Work":
        wm = (workspace_membership or "").strip().lower()
        if wm == "internal":
            return "WorkInternal"
        if wm == "external":
            return "WorkExternal"
        return "Work"
    return ntype


def node_kind_priority(node_kind: str) -> int:
    """Lower index means higher priority when truncating neighbors."""
    return _NODE_KIND_PRIORITY.get((node_kind or "").strip(), 99)


def parse_priority_csv(raw: str | None) -> tuple[str, ...]:
    """Parse `prioritize` CSV preserving order and removing duplicates."""
    if not raw or not str(raw).strip():
        return PRIORITY_NEIGHBOR_KINDS_DEFAULT
    parts = [p.strip() for p in str(raw).split(",")]
    cleaned: list[str] = []
    seen: set[str] = set()
    for part in parts:
        if not part:
            continue
        token = part[0].upper() + part[1:] if len(part) > 1 else part.upper()
        if token in seen:
            continue
        seen.add(token)
        cleaned.append(token)
    return tuple(cleaned) or PRIORITY_NEIGHBOR_KINDS_DEFAULT


def compute_node_display(
    ntype: str,
    raw_label: str,
    props: dict[str, Any],
    *,
    authorship_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return node display fields with UUID-safe human fallbacks."""
    node_type = (ntype or "").strip() or "Node"
    p = dict(props or {})
    label = _clean_label(raw_label)
    if _is_uuid_like(label):
        label = ""

    subtitle = node_type
    display_label = label

    if node_type == "Work":
        year = p.get("publication_year")
        display_label = display_label or "Untitled work"
        subtitle = f"Work · {int(year)}" if year is not None else "Work"
    elif node_type == "Author":
        display_label = display_label or "Unnamed author"
        subtitle = "Author"
    elif node_type == "Institution":
        display_label = display_label or "Unnamed institution"
        country = _clean_label(str(p.get("country") or ""))
        subtitle = f"Institution · {country}" if country else "Institution"
    elif node_type == "Venue":
        display_label = display_label or "Unknown venue"
        venue_type = _clean_label(str(p.get("venue_type") or ""))
        issn = _clean_label(str(p.get("issn") or ""))
        subtitle = (
            f"Venue · {venue_type}" if venue_type else (f"Venue · {issn}" if issn else "Venue")
        )
    elif node_type == "Method":
        display_label = display_label or "Unnamed method"
        mk = _clean_label(str(p.get("method_kind") or ""))
        ds = _clean_label(str(p.get("description_short") or ""))
        if mk:
            subtitle = f"Method · {mk}"[:200]
        elif ds:
            subtitle = (ds[:120] + ("…" if len(ds) > 120 else "")) or "Method"
        else:
            subtitle = "Method"
    elif node_type == "Dataset":
        display_label = display_label or "Unnamed dataset"
        subtitle = "Dataset"
    elif node_type == "Claim":
        body = _clean_label(str(p.get("normalized_text") or p.get("text") or raw_label or ""))
        display_label = (body[:180] if body else "") or "Claim"
        pol = _clean_label(str(p.get("polarity") or ""))
        ct = _clean_label(str(p.get("claim_type") or ""))
        bits = [b for b in (ct, pol) if b]
        subtitle = ("Claim · " + " · ".join(bits)) if bits else "Claim"
    elif node_type == "Authorship":
        extra = authorship_extra or {}
        position = extra.get("author_position")
        author_name = _clean_label(str(extra.get("author_name") or ""))
        if _is_uuid_like(author_name):
            author_name = ""
        raw_aff = _clean_label(str(extra.get("raw_affiliation") or ""))
        inst_name = _clean_label(str(extra.get("institution_name") or ""))
        affiliation = inst_name or raw_aff

        if position is not None:
            if author_name:
                display_label = f"{author_name} (#{int(position)})"
            else:
                display_label = f"Author #{int(position)}"
            subtitle = f"Author #{int(position)}"
            if affiliation:
                subtitle = f"{subtitle} · {affiliation}"
        else:
            display_label = author_name or display_label or "Authorship"
            subtitle = "Authorship"

        if position is not None:
            p["author_position"] = int(position)
        if extra.get("is_corresponding") is not None:
            p["is_corresponding"] = bool(extra.get("is_corresponding"))
        if raw_aff:
            p["raw_affiliation"] = raw_aff
        if inst_name:
            p["institution_name"] = inst_name
    else:
        display_label = display_label or node_type
        subtitle = node_type

    return {
        "display_label": display_label[:200],
        "subtitle": subtitle[:200],
        "properties": p,
    }


def enrich_authorship_nodes(session: Neo4jSession, nodes: list[dict[str, Any]]) -> None:
    """Hydrate Authorship display fields from related Author/Institution nodes.

    When ``OF_AUTHOR`` resolves, ``properties.author_entity_id`` is set for
    ``graph_reader_projection.authorship_collapse.collapse_authorship_for_reader_view``.
    Work-graph ``view=raw`` strips that
    key after enrich so the raw payload stays topology-oriented.
    """
    ids = [str(n.get("id") or "") for n in nodes if str(n.get("type") or "") == "Authorship"]
    ids = [x for x in ids if x]
    if not ids:
        return

    by_id = {str(n.get("id") or ""): n for n in nodes}
    rows = session.run(
        """
        UNWIND $ids AS aid
        MATCH (x:Authorship {id: aid})
        OPTIONAL MATCH (x)-[:OF_AUTHOR]->(au:Author)
        OPTIONAL MATCH (x)-[:AFFILIATED_WITH]->(i:Institution)
        RETURN aid,
               x.author_position AS pos,
               coalesce(x.raw_affiliation, '') AS raw_aff,
               x.is_corresponding AS corr,
               coalesce(au.full_name, '') AS auth_name,
               coalesce(i.name, '') AS inst_name,
               coalesce(au.id, '') AS author_entity_id
        """,
        ids=ids,
    )
    for row in rows:
        nid = str(row.get("aid") or "")
        node = by_id.get(nid)
        if not node:
            continue
        rendered = compute_node_display(
            "Authorship",
            str(node.get("display_label") or node.get("label") or ""),
            dict(node.get("properties") or {}),
            authorship_extra={
                "author_position": row.get("pos"),
                "author_name": row.get("auth_name"),
                "raw_affiliation": row.get("raw_aff"),
                "institution_name": row.get("inst_name"),
                "is_corresponding": row.get("corr"),
            },
        )
        node["label"] = rendered["display_label"]
        node["display_label"] = rendered["display_label"]
        node["subtitle"] = rendered["subtitle"]
        props = dict(rendered["properties"])
        aeid = str(row.get("author_entity_id") or "").strip()
        if aeid:
            props["author_entity_id"] = aeid
        node["properties"] = props
