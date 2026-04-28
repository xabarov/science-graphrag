"""Shared reader-facing graph projection (authorship collapse, stable ids, enrich seam)."""

from science_graphrag.api.graph_reader_projection.authorship_collapse import (
    collapse_authorship_for_reader_view,
)
from science_graphrag.api.graph_reader_projection.authorship_enrich import enrich_authorship_nodes
from science_graphrag.api.graph_reader_projection.authorship_meta import (
    compute_authorship_projection_meta,
    strip_reader_only_authorship_properties,
)
from science_graphrag.api.graph_reader_projection.constants import (
    READER_SYNTHETIC_AUTHOR_HASH_MARKER,
    READER_SYNTHETIC_AUTHOR_ID_PREFIX,
)
from science_graphrag.api.graph_reader_projection.stable_edge_id import stable_graph_edge_id

__all__ = [
    "READER_SYNTHETIC_AUTHOR_HASH_MARKER",
    "READER_SYNTHETIC_AUTHOR_ID_PREFIX",
    "collapse_authorship_for_reader_view",
    "compute_authorship_projection_meta",
    "enrich_authorship_nodes",
    "stable_graph_edge_id",
    "strip_reader_only_authorship_properties",
]
