"""LangGraph multi-agent supervisor graph (Wave Y4)."""

from __future__ import annotations

from typing import Literal

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from science_graphrag.agent.graph.nodes.graph_agent import SPECIALIST_NAME as GRAPH_SPECIALIST
from science_graphrag.agent.graph.nodes.graph_agent import (
    build_graph_agent_node,
)
from science_graphrag.agent.graph.nodes.retrieval_agent import (
    SPECIALIST_NAME as RETRIEVAL_SPECIALIST,
)
from science_graphrag.agent.graph.nodes.retrieval_agent import (
    build_retrieval_agent_node,
)
from science_graphrag.agent.graph.nodes.writer_agent import SPECIALIST_NAME as WRITER_SPECIALIST
from science_graphrag.agent.graph.nodes.writer_agent import (
    build_writer_agent_node,
)
from science_graphrag.agent.coordination.deterministic import _graph_intent_heuristic
from science_graphrag.agent.graph.state import AgentState
from science_graphrag.agent.llm.chat import build_chat_model, ensure_messages_safe_for_generation
from science_graphrag.agent.tools import build_tool_registry
from science_graphrag.api.deps import StoreRegistry
from science_graphrag.config import Settings
from science_graphrag.observability.spans import add_span_event, chain_span

ROUTE_FINISH = "finish"


def _turn_tool_policy(state: AgentState) -> str:
    meta = state.get("metadata") or {}
    tp = meta.get("turn_policy")
    if isinstance(tp, dict):
        pol = str(tp.get("tool_policy") or "").strip()
        if pol in {"no_tools", "clarify", "allow_tools"}:
            return pol
    return "allow_tools"


def _first_user_plain_question(state: AgentState) -> str:
    meta = state.get("metadata") or {}
    raw = meta.get("raw_user_question")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    for msg in reversed(state.get("messages") or []):
        content = getattr(msg, "content", None)
        if isinstance(content, str) and content.strip():
            return content.strip()
    return ""


def _build_supervisor_route_messages(state: AgentState) -> list[HumanMessage]:
    """Build a provider-safe routing prompt without replaying tool-call transcripts."""
    specialist_context = str(state.get("specialist_results") or {})
    user_question = _first_user_plain_question(state)
    return [
        HumanMessage(content=ROUTING_PROMPT),
        HumanMessage(content=f"user_question={user_question[:4000]}"),
        HumanMessage(content=f"specialist_results={specialist_context[:12000]}"),
    ]


ROUTING_PROMPT = """You are a supervisor for scholarly research agents.
Available specialists:
- retrieval_agent: semantic search in papers and workspace summaries
- graph_agent: structural queries, entity lookup and graph traversal
- writer_agent: synthesize final answer with citations

Given the user question and accumulated specialist_results, decide the next specialist.
Respond with exactly one token:
retrieval_agent | graph_agent | writer_agent | FINISH
"""


def build_supervisor_graph(stores: StoreRegistry, settings: Settings):
    """Build and compile Wave Y4 multi-agent supervisor graph."""
    llm = build_chat_model(settings)
    retrieval_node = build_retrieval_agent_node(stores, settings)
    graph_node = build_graph_agent_node(stores, settings)
    writer_node = build_writer_agent_node(stores, settings)

    def supervisor_node(state: AgentState) -> dict:
        budget = int(state.get("budget_remaining", settings.agent_max_tool_calls))
        prior = list(state.get("routing_log") or [])
        tool_policy = _turn_tool_policy(state)
        if not prior and tool_policy in {"no_tools", "clarify"}:
            meta = state.get("metadata") or {}
            tp = meta.get("turn_policy") if isinstance(meta.get("turn_policy"), dict) else {}
            reason = str(tp.get("reason") or "coordinator_gate")
            return {
                "current_specialist": WRITER_SPECIALIST,
                "routing_log": [
                    *prior,
                    {
                        "from": "supervisor",
                        "to": WRITER_SPECIALIST,
                        "reason": f"coordinator_gate:{reason}",
                        "tool_policy": tool_policy,
                        "budget_left": budget,
                    },
                ],
            }
        if budget <= 0:
            return {
                "current_specialist": WRITER_SPECIALIST,
                "routing_log": [
                    *list(state.get("routing_log") or []),
                    {"from": "supervisor", "to": WRITER_SPECIALIST, "reason": "budget_exhausted"},
                ],
            }
        meta = state.get("metadata") or {}
        tp = meta.get("turn_policy") if isinstance(meta.get("turn_policy"), dict) else {}
        route_hint = str(tp.get("route_hint") or "").strip()
        ans_cls = str(state.get("answer_class") or "").strip()

        # First hop: honor coordinator route_hint (single source of truth with TurnPolicy).
        if not prior and tool_policy == "allow_tools":
            if route_hint == GRAPH_SPECIALIST or ans_cls == "relation_tracing":
                reason = (
                    "coordinator_route_hint"
                    if route_hint == GRAPH_SPECIALIST
                    else "answer_class_relation_tracing"
                )
                return {
                    "current_specialist": GRAPH_SPECIALIST,
                    "routing_log": [
                        {
                            "from": "supervisor",
                            "to": GRAPH_SPECIALIST,
                            "reason": reason,
                            "route_hint": route_hint or None,
                            "budget_left": budget,
                        },
                    ],
                }
            if route_hint == WRITER_SPECIALIST:
                return {
                    "current_specialist": WRITER_SPECIALIST,
                    "routing_log": [
                        {
                            "from": "supervisor",
                            "to": WRITER_SPECIALIST,
                            "reason": "coordinator_route_hint",
                            "budget_left": budget,
                        },
                    ],
                }
            if route_hint == RETRIEVAL_SPECIALIST and settings.agent_semantic_query_fast_route:
                uq = _first_user_plain_question(state)
                if uq and not _graph_intent_heuristic(uq):
                    return {
                        "current_specialist": RETRIEVAL_SPECIALIST,
                        "routing_log": [
                            {
                                "from": "supervisor",
                                "to": RETRIEVAL_SPECIALIST,
                                "reason": "semantic_fast_route",
                                "budget_left": budget,
                            },
                        ],
                    }

        max_rounds = int(settings.agent_supervisor_max_rounds)
        sup_hops = len([x for x in prior if isinstance(x, dict) and x.get("from") == "supervisor"])
        if sup_hops >= max_rounds > 0:
            return {
                "current_specialist": WRITER_SPECIALIST,
                "routing_log": [
                    *list(state.get("routing_log") or []),
                    {
                        "from": "supervisor",
                        "to": WRITER_SPECIALIST,
                        "reason": "supervisor_round_cap",
                        "budget_left": budget,
                        "supervisor_hops": sup_hops,
                    },
                ],
            }

        route_msgs = _build_supervisor_route_messages(state)
        with chain_span(
            "agent.supervisor.route_llm",
            {"agent.budget_remaining": budget},
        ):
            response = llm.invoke(ensure_messages_safe_for_generation(route_msgs))
        choice = str(response.content or "").strip().lower()
        if choice not in {RETRIEVAL_SPECIALIST, GRAPH_SPECIALIST, WRITER_SPECIALIST, ROUTE_FINISH}:
            # Old unsafe default was retrieval; prefer writer on non-exact route tokens.
            add_span_event(
                "agent.supervisor.invalid_route_token",
                {"token": choice[:80]},
            )
            choice = WRITER_SPECIALIST
        return {
            "current_specialist": choice,
            "routing_log": [
                *list(state.get("routing_log") or []),
                {"from": "supervisor", "to": choice, "budget_left": budget},
            ],
        }

    def route_to_specialist(
        state: AgentState,
    ) -> Literal["retrieval_agent", "graph_agent", "writer_agent", "__end__"]:
        specialist = str(state.get("current_specialist") or WRITER_SPECIALIST)
        if specialist == ROUTE_FINISH:
            return END
        if specialist in {RETRIEVAL_SPECIALIST, GRAPH_SPECIALIST, WRITER_SPECIALIST}:
            return specialist
        return WRITER_SPECIALIST

    graph = StateGraph(AgentState)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node(RETRIEVAL_SPECIALIST, retrieval_node)
    graph.add_node(GRAPH_SPECIALIST, graph_node)
    graph.add_node(WRITER_SPECIALIST, writer_node)
    graph.set_entry_point("supervisor")
    graph.add_conditional_edges(
        "supervisor",
        route_to_specialist,
        {
            RETRIEVAL_SPECIALIST: RETRIEVAL_SPECIALIST,
            GRAPH_SPECIALIST: GRAPH_SPECIALIST,
            WRITER_SPECIALIST: WRITER_SPECIALIST,
            END: END,
        },
    )
    graph.add_edge(RETRIEVAL_SPECIALIST, "supervisor")
    graph.add_edge(GRAPH_SPECIALIST, "supervisor")
    graph.add_edge(WRITER_SPECIALIST, END)
    return graph.compile()


def build_retrieval_graph(stores: StoreRegistry, settings: Settings):
    """Build retrieval graph alias with runtime switch."""
    if settings.agent_runtime == "langgraph_supervisor_v1":
        return build_supervisor_graph(stores, settings)
    if settings.agent_runtime == "retrieval_v1":
        return _build_single_agent_graph(stores, settings)
    # Any non-legacy runtime defaults to the supervisor graph.
    return build_supervisor_graph(stores, settings)


def _build_single_agent_graph(stores: StoreRegistry, settings: Settings):
    """Wave Y2 fallback: single-agent ReAct graph."""
    tool_registry = build_tool_registry(stores)
    llm = build_chat_model(settings).bind_tools(tool_registry)

    def chat_node(state: AgentState) -> dict:
        response = llm.invoke(ensure_messages_safe_for_generation(state["messages"]))
        return {"messages": [response]}

    def budget_node(state: AgentState) -> dict:
        budget = int(state.get("budget_remaining", settings.agent_max_tool_calls))
        return {"budget_remaining": budget - 1}

    def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
        messages = state.get("messages") or []
        if not messages:
            return END
        last = messages[-1]
        budget = int(state.get("budget_remaining", 0))
        if budget <= 0:
            return END
        if getattr(last, "tool_calls", None):
            return "tools"
        return END

    graph = StateGraph(AgentState)
    graph.add_node("chat", chat_node)
    graph.add_node("budget", budget_node)
    graph.add_node("tools", ToolNode(tool_registry))
    graph.set_entry_point("chat")
    graph.add_edge("chat", "budget")
    graph.add_conditional_edges("budget", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "chat")
    return graph.compile()
