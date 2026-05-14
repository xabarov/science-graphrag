from __future__ import annotations

from langchain_core.tools import BaseTool

from science_graphrag.agent.tools.cypher_query import CypherQueryTool, _make_cypher_query_tool
from science_graphrag.agent.tools.edge_search import EdgeSearchTool, _make_edge_search_tool
from science_graphrag.agent.tools.entity_search import EntitySearchTool
from science_graphrag.agent.tools.final_answer import FinalAnswerTool, _make_final_answer_tool
from science_graphrag.agent.tools.idea_search import IdeaSearchTool, _make_idea_search_tool
from science_graphrag.agent.tools.plan_mode_tools import build_plan_mode_tools
from science_graphrag.agent.tools.product_interaction_tools import build_product_interaction_tools
from science_graphrag.agent.tools.summarize_workspace import SummarizeWorkspaceTool
from science_graphrag.agent.tools.web_research_tools import build_web_research_tools
from science_graphrag.agent.tools.workspace_paper_tools import build_workspace_paper_langchain_tools
from science_graphrag.agent.tools.worktree_isolation_tools import build_worktree_isolation_tools
from science_graphrag.config import Settings, get_settings
from science_graphrag.stores.registry import StoreRegistry


def _append_agent_surface_tools(
    out: list[BaseTool], stores: StoreRegistry, settings: Settings
) -> None:
    """Feature-gated MCP/LSP/monitor + product interaction tools (shared by retrieval + full registry)."""
    if getattr(settings, "agent_mcp_tools_enabled", False):
        from science_graphrag.agent.tools.mcp_surface import build_mcp_surface_tools

        out.extend(build_mcp_surface_tools(settings))
    if getattr(settings, "agent_lsp_tool_enabled", False):
        from science_graphrag.agent.tools.lsp_surface import build_lsp_tool

        out.extend(build_lsp_tool(settings))
    if getattr(settings, "agent_runtime_monitor_tool_enabled", False):
        from science_graphrag.agent.tools.runtime_monitor_surface import build_runtime_monitor_tools

        out.extend(build_runtime_monitor_tools(settings))

    out.extend(build_product_interaction_tools(settings))
    out.extend(build_worktree_isolation_tools(settings))
    out.extend(build_plan_mode_tools(settings))
    _ = stores  # reserved for future store-backed adapters


def build_retrieval_tools(
    stores: StoreRegistry, settings: Settings | None = None
) -> list[BaseTool]:
    """Tools for retrieval specialist node (catalog + semantic + workspace summary)."""
    settings = settings or get_settings()
    catalog = build_workspace_paper_langchain_tools(
        stores.neo4j,
        stores.qdrant_chunks,
        settings=settings,
    )
    core: list[BaseTool] = [
        _make_idea_search_tool(
            stores.qdrant_chunks,
            stores.qdrant_works,
            settings=settings,
        ),
    ]
    out = catalog + core
    out.extend(build_web_research_tools(settings=settings))
    _append_agent_surface_tools(out, stores, settings)
    return out


def build_graph_tools(stores: StoreRegistry) -> list[BaseTool]:
    """Tools for graph specialist node (structural graph only; work full-text is find_works in retrieval)."""
    return [
        _make_cypher_query_tool(stores.neo4j),
        _make_edge_search_tool(stores.neo4j),
    ]


def build_writer_tools(_stores: StoreRegistry) -> list[BaseTool]:
    """Tools for writer specialist node."""
    return [_make_final_answer_tool()]


def build_tool_registry(stores: StoreRegistry, settings: Settings | None = None) -> list[BaseTool]:
    """Build LangChain tool list with injected stores."""
    settings = settings or get_settings()
    out: list[BaseTool] = []
    out.extend(build_graph_tools(stores))
    out.extend(build_retrieval_tools(stores, settings))
    if getattr(settings, "agent_doi_resolver_tool_enabled", False):
        from science_graphrag.agent.tools.doi_resolver_tool import build_doi_resolver_tool

        out.append(build_doi_resolver_tool(stores.neo4j, settings))
    out.extend(build_writer_tools(stores))
    return out


__all__ = [
    "CypherQueryTool",
    "EntitySearchTool",
    "EdgeSearchTool",
    "IdeaSearchTool",
    "SummarizeWorkspaceTool",
    "FinalAnswerTool",
    "build_retrieval_tools",
    "build_graph_tools",
    "build_writer_tools",
    "build_tool_registry",
]
