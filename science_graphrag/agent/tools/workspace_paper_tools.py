"""LangChain tool bundle: workspace catalog, quote search, GOST bibliography (CH2).

Implementation is split across `workspace_catalog_tools`, `paper_quote_search_tool`,
and `format_bibliography_gost_tool` for reviewability.
"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool, tool

from science_graphrag.agent.tools.chunk_retrieval_defaults import DEFAULT_AGENT_CHUNK_TOP_K
from science_graphrag.agent.tools.format_bibliography_gost_tool import (
    BibGostArgs,
    FormatBibliographyGostTool,
)
from science_graphrag.agent.tools.paper_quote_search_tool import (
    PaperQuoteArgs,
    PaperQuoteSearchTool,
)
from science_graphrag.agent.tools.trace_wrappers import run_tool_result_with_span
from science_graphrag.agent.tools.workspace_catalog_tools import (
    FindWorksArgs,
    FindWorksTool,
    PaperProfileArgs,
    PaperProfileTool,
    WorkspaceGraphReltypesArgs,
    WorkspaceGraphReltypesTool,
    WorkspaceInspectArgs,
    WorkspaceInspectTool,
)
from science_graphrag.config import Settings
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.storage.qdrant_store import QdrantChunkStore

__all__ = [
    "FormatBibliographyGostTool",
    "FindWorksTool",
    "PaperProfileTool",
    "PaperQuoteSearchTool",
    "WorkspaceGraphReltypesTool",
    "WorkspaceInspectTool",
    "build_workspace_paper_langchain_tools",
]


def build_workspace_paper_langchain_tools(
    store: Neo4jGraphStore,
    chunk_store: QdrantChunkStore,
    *,
    settings: Settings,
) -> list[BaseTool]:
    """LangChain tools bound to stores."""
    inspect = WorkspaceInspectTool(store)
    graph_reltypes = WorkspaceGraphReltypesTool(store)
    profile = PaperProfileTool(store)
    find_works = FindWorksTool(store)
    quotes = PaperQuoteSearchTool(chunk_store, settings=settings)
    bib = FormatBibliographyGostTool(store)

    @tool("workspace_inspect", args_schema=WorkspaceInspectArgs, return_direct=False)
    def workspace_inspect_tool(
        workspace_id: str,
        mode: str = "stats",
        list_limit: int = 20,
    ) -> dict[str, Any]:
        """Return workspace facts, a truncated paper list, or a short blurb plus sample work ids.

        Use mode=stats for counts and flags only. Use mode=papers when the user needs titles
        in the workspace. Use mode=blurb for a one-line composition summary and cited_work_ids
        before a semantic idea_search. Do not use this tool for full-text title search across
        papers (use find_works instead).
        """
        r = run_tool_result_with_span(
            tool_name="workspace_inspect",
            tool_parameters={
                "workspace_id": workspace_id,
                "mode": mode,
                "list_limit": list_limit,
            },
            fn=lambda: inspect.run(
                workspace_id=workspace_id,
                mode=mode,
                list_limit=list_limit,
            ),
        )
        p = dict(r.payload)
        p.setdefault("row_count", r.row_count)
        p.setdefault("truncated", r.truncated)
        return p

    @tool("workspace_graph_reltypes", args_schema=WorkspaceGraphReltypesArgs, return_direct=False)
    def workspace_graph_reltypes_tool(
        workspace_id: str,
        work_sample_limit: int = 60,
        rel_types_limit: int = 64,
    ) -> dict[str, Any]:
        """Distinct ``type(r)`` values on Work hops within this workspace (read-only).

        Prefer ``rel_types`` from this response for ``edge_search(rel_types=...)`` filters.
        ``canonical_hints`` lists common types from the product schema—they may not all exist here.
        Pass ``workspace_id`` from the active workspace when the question is workspace-scoped.
        """
        r = run_tool_result_with_span(
            tool_name="workspace_graph_reltypes",
            tool_parameters={
                "workspace_id": workspace_id,
                "work_sample_limit": work_sample_limit,
                "rel_types_limit": rel_types_limit,
            },
            fn=lambda: graph_reltypes.run(
                workspace_id=workspace_id,
                work_sample_limit=work_sample_limit,
                rel_types_limit=rel_types_limit,
            ),
        )
        p = dict(r.payload)
        p.setdefault("row_count", r.row_count)
        p.setdefault("truncated", r.truncated)
        return p

    @tool("paper_profile", args_schema=PaperProfileArgs, return_direct=False)
    def paper_profile_tool(work_id: str) -> dict[str, Any]:
        """Card for one work: title, year, ids, abstract snippet, venue, authors.

        Payload includes ``metadata_completeness`` (present/absent per field),
        ``venue_resolution`` (``graph_linked`` vs ``no_venue_linked``), and ``metadata_source`` so
        the model can treat nulls as missing corpus data—not as license to invent values.

        Requires a real work_id from find_works, workspace_inspect with mode=papers or blurb
        (not stats), or graph tools. Do not guess ids.
        """
        r = run_tool_result_with_span(
            tool_name="paper_profile",
            tool_parameters={"work_id": work_id},
            fn=lambda: profile.run(work_id=work_id),
        )
        p = dict(r.payload)
        p.setdefault("row_count", r.row_count)
        p.setdefault("truncated", r.truncated)
        return p

    @tool("find_works", args_schema=FindWorksArgs, return_direct=False)
    def find_works_tool(
        query: str,
        workspace_id: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Full-text search for works; optionally restricted to the active workspace.

        Pass workspace_id (same as active workspace in the user message) when the user asks about
        papers *in this workspace*. Omit workspace_id or pass null only when the user needs a
        corpus-wide lookup (any work in the graph). Each hit includes work_id, score, title, and
        year when known.
        """
        r = run_tool_result_with_span(
            tool_name="find_works",
            tool_parameters={
                "query": query[:240],
                "workspace_id": workspace_id or "",
                "limit": limit,
            },
            fn=lambda: find_works.run(
                query=query,
                workspace_id=workspace_id,
                limit=limit,
            ),
        )
        p = dict(r.payload)
        p.setdefault("row_count", r.row_count)
        p.setdefault("truncated", r.truncated)
        return p

    @tool("paper_quote_search", args_schema=PaperQuoteArgs, return_direct=False)
    def paper_quote_search_tool(
        query: str,
        workspace_id: str | None = None,
        work_id: str | None = None,
        top_k: int = DEFAULT_AGENT_CHUNK_TOP_K,
    ) -> dict[str, Any]:
        """Semantic search over document chunks; returns ``quote_candidates`` for citations.

        Resolution chain for quotes: narrow with ``find_works`` / ``paper_profile`` / a short
        ``idea_search`` when needed, then call this tool. Prefer ``work_id`` when evidence must
        come from one paper; pass ``workspace_id`` for workspace-local questions.

        When ``row_count`` is 0, the payload may include ``empty_reason``: ``empty_query``;
        scoped ``no_hits_workspace_scoped`` / ``no_hits_for_work`` / ``no_hits_corpus_wide``;
        or ``qdrant_unavailable`` — use that to widen the query or reuse ``idea_search`` snippets.
        """
        r = run_tool_result_with_span(
            tool_name="paper_quote_search",
            tool_parameters={
                "query": query[:200],
                "workspace_id": workspace_id or "",
                "work_id": work_id or "",
                "top_k": top_k,
            },
            fn=lambda: quotes.run(
                query=query, workspace_id=workspace_id, work_id=work_id, top_k=top_k
            ),
        )
        p = dict(r.payload)
        p.setdefault("row_count", r.row_count)
        p.setdefault("truncated", r.truncated)
        return p

    @tool("format_bibliography_gost", args_schema=BibGostArgs, return_direct=False)
    def format_bibliography_gost_tool(workspace_id: str, work_ids: list[str]) -> dict[str, Any]:
        """Build deterministic GOST-like bibliography lines for given work_ids in a workspace.

        work_ids must belong to workspace_id; non-members are filtered with a warning in the
        payload.
        """
        r = run_tool_result_with_span(
            tool_name="format_bibliography_gost",
            tool_parameters={
                "workspace_id": workspace_id,
                "work_ids_count": len(work_ids or []),
            },
            fn=lambda: bib.run(workspace_id=workspace_id, work_ids=work_ids),
        )
        p = dict(r.payload)
        p.setdefault("row_count", r.row_count)
        p.setdefault("truncated", r.truncated)
        return p

    return [
        workspace_inspect_tool,
        workspace_graph_reltypes_tool,
        paper_profile_tool,
        find_works_tool,
        paper_quote_search_tool,
        format_bibliography_gost_tool,
    ]
