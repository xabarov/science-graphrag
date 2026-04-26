from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from science_graphrag.agent.chat_envelope import build_chat_envelope
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
    answer_class: str = "grounded_explanation"
    evidence_summary: str | None = None
    warnings: list[str] = field(default_factory=list)
    inventory: dict[str, Any] | None = None
    relation_trace: dict[str, Any] | None = None
    quote_candidates: list[dict[str, Any]] | None = None
    idea_suggestions: list[dict[str, Any]] | None = None
    bibliography: dict[str, Any] | None = None
    debug_events: list[dict[str, Any]] = field(default_factory=list)


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
        answer_class_hint: str | None = None,
    ) -> AgentRunOutput:
        if self._legacy is not None:
            return self._legacy.run(
                question=question,
                workspace_id=workspace_id,
                max_tool_calls=max_tool_calls,
            )
        return self._run_langgraph(
            question=question,
            workspace_id=workspace_id,
            max_tool_calls=max_tool_calls,
            answer_class_hint=answer_class_hint,
        )

    def _run_langgraph(
        self,
        *,
        question: str,
        workspace_id: str | None,
        max_tool_calls: int,
        answer_class_hint: str | None = None,
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
                "debug_events": [],
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
            envelope = build_chat_envelope(
                state=final_state,
                answer=answer,
                citations=list(final_state.get("citations", [])),
                tool_trace=trace,
                answer_class_hint=answer_class_hint,
            )
            return AgentRunOutput(
                answer=answer,
                citations=list(final_state.get("citations", [])),
                tool_trace=trace,
                answer_class=str(envelope.get("answer_class") or "grounded_explanation"),
                evidence_summary=envelope.get("evidence_summary"),
                warnings=list(envelope.get("warnings") or []),
                inventory=envelope.get("inventory"),
                relation_trace=envelope.get("relation_trace"),
                quote_candidates=envelope.get("quote_candidates"),
                idea_suggestions=envelope.get("idea_suggestions"),
                bibliography=envelope.get("bibliography"),
                debug_events=list(final_state.get("debug_events") or []),
            )


def build_agent(
    *,
    settings: Settings,
    stores: StoreRegistry,
) -> RetrievalAgent:
    return RetrievalAgent(settings=settings, stores=stores)
