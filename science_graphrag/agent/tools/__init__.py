from __future__ import annotations

from langchain_core.tools import BaseTool

from science_graphrag.agent.tools.cypher_query import CypherQueryTool, _make_cypher_query_tool
from science_graphrag.agent.tools.edge_search import EdgeSearchTool, _make_edge_search_tool
from science_graphrag.agent.tools.entity_search import EntitySearchTool, _make_entity_search_tool
from science_graphrag.agent.tools.final_answer import FinalAnswerTool, _make_final_answer_tool
from science_graphrag.agent.tools.idea_search import IdeaSearchTool, _make_idea_search_tool
from science_graphrag.agent.tools.summarize_workspace import (
    SummarizeWorkspaceTool,
    _make_summarize_workspace_tool,
)
from science_graphrag.api.deps import StoreRegistry


def build_tool_registry(stores: StoreRegistry) -> list[BaseTool]:
    """Build LangChain tool list with injected stores."""
    return [
        _make_cypher_query_tool(stores.neo4j),
        _make_entity_search_tool(stores.neo4j),
        _make_edge_search_tool(stores.neo4j),
        _make_idea_search_tool(
            stores.qdrant_chunks,
            stores.qdrant_works,
            embedding_model=None,
        ),
        _make_summarize_workspace_tool(stores.neo4j),
        _make_final_answer_tool(),
    ]


__all__ = [
    "CypherQueryTool",
    "EntitySearchTool",
    "EdgeSearchTool",
    "IdeaSearchTool",
    "SummarizeWorkspaceTool",
    "FinalAnswerTool",
    "build_tool_registry",
]
