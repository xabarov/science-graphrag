from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from science_graphrag.agent.graph.supervisor import build_retrieval_graph
from science_graphrag.agent.graph.tracing import collect_tool_trace
from science_graphrag.agent.trace import ToolCallTrace
from science_graphrag.api.deps import StoreRegistry
from science_graphrag.config import Settings
from science_graphrag.observability.spans import chain_span


@dataclass
class AgentRunOutput:
    answer: str
    citations: list[dict[str, Any]]
    tool_trace: list[ToolCallTrace]


class RetrievalAgent:
    """Production retrieval agent runtime (Wave Y2: LangGraph ReAct)."""

    def __init__(
        self,
        *,
        settings: Settings,
        stores: StoreRegistry,
    ) -> None:
        self._settings = settings
        self._stores = stores
        if settings.agent_runtime == "retrieval_v1":
            from science_graphrag.agent.runtime_legacy import LegacyRetrievalAgent

            self._legacy = LegacyRetrievalAgent(
                settings=settings,
                neo4j=stores.neo4j,
                chunks=stores.qdrant_chunks,
                works=stores.qdrant_works,
            )
            self._graph = None
        else:
            self._legacy = None
            self._graph = build_retrieval_graph(stores, settings)

    def run(
        self,
        *,
        question: str,
        workspace_id: str | None,
        max_tool_calls: int,
    ) -> AgentRunOutput:
        if self._legacy is not None:
            return self._legacy.run(
                question=question,
                workspace_id=workspace_id,
                max_tool_calls=max_tool_calls,
            )
        return self._run_langgraph(
            question=question, workspace_id=workspace_id, max_tool_calls=max_tool_calls
        )

    def _run_langgraph(
        self,
        *,
        question: str,
        workspace_id: str | None,
        max_tool_calls: int,
    ) -> AgentRunOutput:
        attrs = {
            "agent.runtime": self._settings.agent_runtime,
            "agent.max_tool_calls": max_tool_calls or self._settings.agent_max_tool_calls,
            "user.id": workspace_id or "",
            "input.value": question[:500],
        }
        with chain_span("agent.query", attrs):
            budget = max_tool_calls or self._settings.agent_max_tool_calls
            initial_state = {
                "messages": [HumanMessage(content=question)],
                "workspace_id": workspace_id,
                "citations": [],
                "tool_trace": [],
                "budget_remaining": budget,
                "metadata": {"agent_runtime": self._settings.agent_runtime},
                "specialist_results": {},
                "current_specialist": None,
                "routing_log": [],
            }
            assert self._graph is not None
            final_state = self._graph.invoke(
                initial_state,
                config={"recursion_limit": self._settings.agent_supervisor_recursion_limit},
            )
            messages = final_state.get("messages", [])
            trace = collect_tool_trace(final_state)
            answer = ""
            for msg in reversed(messages):
                if isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", None):
                    answer = str(msg.content or "")
                    break
            return AgentRunOutput(
                answer=answer,
                citations=list(final_state.get("citations", [])),
                tool_trace=trace,
            )


def build_agent(
    *,
    settings: Settings,
    stores: StoreRegistry,
) -> RetrievalAgent:
    return RetrievalAgent(settings=settings, stores=stores)
