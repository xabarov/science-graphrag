"""Neo4j relationship type hints for Work-neighborhood tools and prompts.

``KNOWN_WORK_NEIGHBOR_REL_TYPES`` is a **hint list** from writers in
``science_graphrag/storage/neo4j/writes/`` and ``reads.py`` — not every type exists in every
workspace. The ``rel_types`` array returned by ``workspace_graph_reltypes`` is authoritative for the
active workspace sample.
"""

from __future__ import annotations

# Types commonly materialized on (Work)-[r]-(*) hops in this product (not exhaustive of Cypher).
KNOWN_WORK_NEIGHBOR_REL_TYPES: tuple[str, ...] = (
    "AFFILIATED_WITH",
    "ANCHORED_IN",
    "ARTICLE_CONTRADICTION_RECORD",
    "CITES",
    "CONTAINS",
    "EVALUATED_ON",
    "HAS_AUTHORSHIP",
    "HAS_EVIDENCE",
    "HAS_METHOD_EVIDENCE",
    "OF_AUTHOR",
    "PUBLISHED_IN",
    "RELATED_VERSION_OF",
    "SUPPORTED_BY",
    "USES_METHOD",
)

WORK_EDGE_REL_TYPES_HINT: str = (
    "Examples of ``type(r)`` on (Work)-[r]-(*) hops in this product: "
    + ", ".join(KNOWN_WORK_NEIGHBOR_REL_TYPES[:8])
    + ", … (not exhaustive). Prefer names from **workspace_graph_reltypes** for this workspace "
    "before passing ``rel_types`` to edge_search."
)
