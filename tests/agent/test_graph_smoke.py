from __future__ import annotations

from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage

from science_graphrag.agent.graph.supervisor import build_retrieval_graph


def test_langgraph_compile_smoke() -> None:
    stores = MagicMock()
    stores.neo4j = MagicMock()
    stores.qdrant_chunks = MagicMock()
    stores.qdrant_works = MagicMock()

    settings = MagicMock()
    settings.agent_max_tool_calls = 4
    settings.agent_supervisor_recursion_limit = 10
    settings.extraction_llm_model = "test-model"
    settings.extraction_llm_api_key = "test-key"
    settings.extraction_llm_base_url = "http://localhost"
    settings.extraction_llm_timeout_seconds = 30
    settings.agent_chat_temperature = 0.0
    settings.agent_chat_max_tokens = 512

    with patch("science_graphrag.agent.graph.supervisor.build_chat_model") as mock_llm:
        mock_llm.return_value.bind_tools.return_value.invoke.return_value = AIMessage(
            content="test answer", tool_calls=[]
        )
        graph = build_retrieval_graph(stores, settings)
        assert graph is not None
