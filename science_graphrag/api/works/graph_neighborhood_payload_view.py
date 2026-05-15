"""View-specific post-processing for work graph neighborhood payloads (raw vs reader)."""

from __future__ import annotations

from typing import Any

from neo4j import Session as Neo4jSession

from science_graphrag.api.graph_reader_projection.authorship_collapse import (
    build_authorship_to_reader_author_map,
    collapse_authorship_for_reader_view,
)
from science_graphrag.api.graph_reader_projection.authorship_meta import (
    compute_authorship_projection_meta,
    strip_reader_only_authorship_properties,
)
from science_graphrag.api.works.graph_neighborhood_aggregation import _enrich_edges_with_display
from science_graphrag.api.works.graph_neighborhood_institutions import (
    INSTITUTION_ATTACH_CAP,
    attach_institutions_raw,
    attach_institutions_reader,
    fetch_work_authorship_institutions,
)


def apply_neighborhood_view_shape(
    session: Neo4jSession,
    *,
    work_id: str,
    center_id: str,
    view: str,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    include_institutions: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int, dict[str, Any] | None]:
    """Apply raw/reader transforms, optional institutions, and edge display labels.

    Returns ``(nodes, edges, institutions_attached, reader_authorship_projection)``.
    """

    vnorm = str(view or "reader").strip().lower()
    inst_rows: list[dict[str, Any]] = []
    if include_institutions:
        inst_rows = fetch_work_authorship_institutions(session, work_id, INSTITUTION_ATTACH_CAP)
    ash_author_map: dict[str, str] = {}
    if include_institutions and vnorm == "reader":
        ash_author_map = build_authorship_to_reader_author_map(nodes, edges, center_id)
    institutions_attached = 0
    if vnorm == "raw":
        strip_reader_only_authorship_properties(nodes)
    if include_institutions and vnorm == "raw":
        institutions_attached = attach_institutions_raw(nodes, edges, inst_rows)
    if vnorm == "reader":
        nodes, edges = collapse_authorship_for_reader_view(nodes, edges, center_id)
    if include_institutions and vnorm == "reader":
        institutions_attached = attach_institutions_reader(nodes, edges, inst_rows, ash_author_map)
    reader_authorship_projection = (
        compute_authorship_projection_meta(center_id, edges) if vnorm == "reader" else None
    )
    _enrich_edges_with_display(center_id, nodes, edges)
    return nodes, edges, institutions_attached, reader_authorship_projection
