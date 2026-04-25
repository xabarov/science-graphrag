"""Backward-compat shim for workspace graph API router."""

from science_graphrag.api.workspace_graph.router import router  # noqa: F401

__all__ = ["router"]
