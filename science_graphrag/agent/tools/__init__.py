from __future__ import annotations

from langchain_core.tools import BaseTool

from science_graphrag.agent.tools.cypher_query import CypherQueryTool, _make_cypher_query_tool
from science_graphrag.agent.tools.edge_search import EdgeSearchTool, _make_edge_search_tool
from science_graphrag.agent.tools.entity_search import EntitySearchTool
from science_graphrag.agent.tools.final_answer import FinalAnswerTool, _make_final_answer_tool
from science_graphrag.agent.tools.idea_search import IdeaSearchTool, _make_idea_search_tool
from science_graphrag.agent.tools.summarize_workspace import SummarizeWorkspaceTool
from science_graphrag.agent.tools.workspace_paper_tools import build_workspace_paper_langchain_tools
from science_graphrag.api.deps import StoreRegistry
from science_graphrag.config import Settings, get_settings


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
    return catalog + core


def build_graph_tools(stores: StoreRegistry) -> list[BaseTool]:
    """Tools for graph specialist node (structural graph only; work full-text is find_works in retrieval)."""
    return [
        _make_cypher_query_tool(stores.neo4j),
        _make_edge_search_tool(stores.neo4j),
    ]


def build_writer_tools(_stores: StoreRegistry) -> list[BaseTool]:
    """Tools for writer specialist node."""
    return [_make_final_answer_tool()]


def build_tool_registry(stores: StoreRegistry) -> list[BaseTool]:
    """Build LangChain tool list with injected stores."""
    return build_graph_tools(stores) + build_retrieval_tools(stores) + build_writer_tools(stores)


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
