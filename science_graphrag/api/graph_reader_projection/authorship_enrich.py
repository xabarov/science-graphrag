"""Single import path for authorship batch enrich (delegates to graph_display / Neo4j)."""

from __future__ import annotations

from science_graphrag.api.graph_display import enrich_authorship_nodes

__all__ = ["enrich_authorship_nodes"]
