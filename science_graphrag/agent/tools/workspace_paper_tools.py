"""LangChain tool bundle: workspace catalog, quote search, GOST bibliography (CH2).

Implementation is split across `workspace_catalog_tools`, `paper_quote_search_tool`,
and `format_bibliography_gost_tool` for reviewability.
"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool, tool

from science_graphrag.agent.tools.format_bibliography_gost_tool import (
    BibGostArgs,
    FormatBibliographyGostTool,
)
from science_graphrag.agent.tools.paper_quote_search_tool import (
    PaperQuoteArgs,
    PaperQuoteSearchTool,
)
from science_graphrag.agent.tools.workspace_catalog_tools import (
    PaperAuthorsTool,
    PaperCountsTool,
    PaperLookupArgs,
    PaperLookupTool,
    PaperMetadataTool,
    WorkIdArgs,
    WorkspaceListPapersTool,
    WorkspaceOverviewTool,
    WsIdArgs,
    WsListArgs,
)
from science_graphrag.config import Settings
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.storage.qdrant_store import QdrantChunkStore

__all__ = [
    "FormatBibliographyGostTool",
    "PaperAuthorsTool",
    "PaperCountsTool",
    "PaperLookupTool",
    "PaperMetadataTool",
    "PaperQuoteSearchTool",
    "WorkspaceListPapersTool",
    "WorkspaceOverviewTool",
    "build_workspace_paper_langchain_tools",
]


def build_workspace_paper_langchain_tools(
    store: Neo4jGraphStore,
    chunk_store: QdrantChunkStore,
    *,
    settings: Settings,
) -> list[BaseTool]:
    """LangChain tools bound to stores."""
    overview = WorkspaceOverviewTool(store)
    lst = WorkspaceListPapersTool(store)
    lookup = PaperLookupTool(store)
    meta = PaperMetadataTool(store)
    authors = PaperAuthorsTool(store)
    counts = PaperCountsTool(store)
    quotes = PaperQuoteSearchTool(chunk_store, settings=settings)
    bib = FormatBibliographyGostTool(store)

    @tool("workspace_overview", args_schema=WsIdArgs, return_direct=False)
    def workspace_overview_tool(workspace_id: str) -> dict[str, Any]:
        """Return workspace id, name, work count, and unbounded flag."""
        r = overview.run(workspace_id=workspace_id)
        p = dict(r.payload)
        p.setdefault("row_count", r.row_count)
        p.setdefault("truncated", r.truncated)
        return p

    @tool("workspace_list_papers", args_schema=WsListArgs, return_direct=False)
    def workspace_list_papers_tool(workspace_id: str, limit: int = 20) -> dict[str, Any]:
        """List papers in the workspace with title/year/doi (truncated)."""
        r = lst.run(workspace_id=workspace_id, limit=limit)
        p = dict(r.payload)
        p.setdefault("row_count", r.row_count)
        p.setdefault("truncated", r.truncated)
        return p

    @tool("paper_lookup", args_schema=PaperLookupArgs, return_direct=False)
    def paper_lookup_tool(workspace_id: str, query: str, limit: int = 10) -> dict[str, Any]:
        """Full-text work search restricted to workspace work ids."""
        r = lookup.run(workspace_id=workspace_id, query=query, limit=limit)
        p = dict(r.payload)
        p.setdefault("row_count", r.row_count)
        p.setdefault("truncated", r.truncated)
        return p

    @tool("paper_metadata", args_schema=WorkIdArgs, return_direct=False)
    def paper_metadata_tool(work_id: str) -> dict[str, Any]:
        """Fetch title, year, doi, venue, abstract snippet for one work."""
        r = meta.run(work_id=work_id)
        p = dict(r.payload)
        p.setdefault("row_count", r.row_count)
        p.setdefault("truncated", r.truncated)
        return p

    @tool("paper_authors", args_schema=WorkIdArgs, return_direct=False)
    def paper_authors_tool(work_id: str) -> dict[str, Any]:
        """List authors linked to a work."""
        r = authors.run(work_id=work_id)
        p = dict(r.payload)
        p.setdefault("row_count", r.row_count)
        p.setdefault("truncated", r.truncated)
        return p

    @tool("paper_counts", args_schema=WsIdArgs, return_direct=False)
    def paper_counts_tool(workspace_id: str) -> dict[str, Any]:
        """Return number of works linked to the workspace."""
        r = counts.run(workspace_id=workspace_id)
        p = dict(r.payload)
        p.setdefault("row_count", r.row_count)
        p.setdefault("truncated", r.truncated)
        return p

    @tool("paper_quote_search", args_schema=PaperQuoteArgs, return_direct=False)
    def paper_quote_search_tool(
        query: str,
        workspace_id: str | None = None,
        work_id: str | None = None,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """Semantic search over chunks; returns quote_candidates for grounding."""
        r = quotes.run(query=query, workspace_id=workspace_id, work_id=work_id, top_k=top_k)
        p = dict(r.payload)
        p.setdefault("row_count", r.row_count)
        p.setdefault("truncated", r.truncated)
        return p

    @tool("format_bibliography_gost", args_schema=BibGostArgs, return_direct=False)
    def format_bibliography_gost_tool(workspace_id: str, work_ids: list[str]) -> dict[str, Any]:
        """Build deterministic GOST-like bibliography lines for workspace works."""
        r = bib.run(workspace_id=workspace_id, work_ids=work_ids)
        p = dict(r.payload)
        p.setdefault("row_count", r.row_count)
        p.setdefault("truncated", r.truncated)
        return p

    return [
        workspace_overview_tool,
        workspace_list_papers_tool,
        paper_lookup_tool,
        paper_metadata_tool,
        paper_authors_tool,
        paper_counts_tool,
        paper_quote_search_tool,
        format_bibliography_gost_tool,
    ]
