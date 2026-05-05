"""LangGraph multi-agent supervisor graph (Wave Y4)."""

from __future__ import annotations

from typing import Literal

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph

from science_graphrag.agent.chat_envelope import heuristic_answer_class
from science_graphrag.agent.coordination.deterministic import _graph_intent_heuristic
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
from science_graphrag.agent.graph.react_edges import (
    final_answer_nudge_state_update,
    react_after_tools_decrement_budget,
    react_chat_response_budget_cutoff,
    route_react_chat_to_tools,
    route_react_tools_next,
)
from science_graphrag.agent.graph.state import AgentState
from science_graphrag.agent.llm.chat import (
    agent_chat_transport_max_attempts,
    build_chat_model,
    ensure_messages_safe_for_generation,
)
from science_graphrag.agent.tool_execution_pipeline import (
    apply_allowed_tools_matrix,
    build_tool_execution_node,
    effective_tool_policy,
)
from science_graphrag.agent.tool_message_compact import maybe_compact_agent_messages_for_react
from science_graphrag.agent.tool_search import shortlist_tools_for_single_agent
from science_graphrag.agent.tools import build_tool_registry
from science_graphrag.api.deps import StoreRegistry
from science_graphrag.config import Settings
from science_graphrag.llm.concurrency import invoke_chat_gated
from science_graphrag.observability.spans import (
    SpanAttributes,
    add_span_event,
    chain_span,
    llm_span,
)

ROUTE_FINISH = "finish"


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
- retrieval_agent: workspace inventory (workspace_inspect), full-text work search (find_works),
  paper profiles, semantic idea_search / paper_quote_search, bibliography formatting
- graph_agent: structural graph only — edge neighborhoods and read-only Cypher (no full-text work search)
- writer_agent: synthesize final answer with citations

If the user needs to find papers by title, author name fragment, or keywords without a known work id,
prefer retrieval_agent (find_works). Use graph_agent when the question is about relations, paths,
or patterns between known entities.

When the question requires mixed corpus evidence (semantic chunks plus verbatim quotes), keep routing
to retrieval_agent until idea_search / paper_quote_search have been tried unless specialist_results
already show those paths failed.

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
        tool_policy = effective_tool_policy(state)
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
            "agent.supervisor.route",
            {"agent.budget_remaining": budget},
        ):
            with llm_span(
                "llm.agent.supervisor_route",
                {
                    **SpanAttributes.llm_runtime_policy_attributes(
                        pool_name="agent_chat",
                        transport_timeout_seconds=float(settings.extraction_llm_timeout_seconds),
                        timeout_contract="transport_with_operation_deadline",
                        retry_extra_budget=0,
                        operation_deadline_seconds=min(
                            900.0,
                            float(settings.extraction_llm_timeout_seconds)
                            * float(agent_chat_transport_max_attempts(settings)),
                        ),
                        transport_max_attempts=agent_chat_transport_max_attempts(settings),
                    ),
                    "llm.invocation_name": "agent_supervisor_route",
                },
            ):
                response = invoke_chat_gated(
                    llm,
                    ensure_messages_safe_for_generation(route_msgs),
                    pool_name="agent_chat",
                    settings=settings,
                )
        choice = str(response.content or "").strip().lower()
        if choice not in {RETRIEVAL_SPECIALIST, GRAPH_SPECIALIST, WRITER_SPECIALIST, ROUTE_FINISH}:
            # Old unsafe default was retrieval; prefer writer on non-exact route tokens.
            add_span_event(
                "agent.supervisor.invalid_route_token",
                {"token": choice[:80]},
            )
            choice = WRITER_SPECIALIST
        add_span_event(
            "agent.supervisor.route_selected",
            {"to": choice, "budget_left": budget},
        )
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
    if settings.agent_runtime in ("retrieval_v1", "langgraph_research_v1"):
        return _build_single_agent_graph(stores, settings)
    # Unknown runtime id: keep supervisor graph for backward compatibility.
    return build_supervisor_graph(stores, settings)


def _build_single_agent_graph(stores: StoreRegistry, settings: Settings):
    """Wave Y2 fallback: single-agent ReAct graph."""
    tool_registry = build_tool_registry(stores)
    full_tool_node = build_tool_execution_node(
        tools=tool_registry,
        settings=settings,
        sidechain_id="single_agent_react:full_registry",
    )

    def chat_node(state: AgentState) -> dict:
        cutoff = react_chat_response_budget_cutoff(state, settings=settings)
        if cutoff is not None:
            add_span_event(
                "agent.response_budget_precheck_cutoff",
                {
                    "deadline_kind": "response_only",
                    "min_hop_reserve_seconds": float(settings.agent_min_llm_hop_reserve_seconds),
                },
            )
            return cutoff
        meta = state.get("metadata") or {}
        hint = meta.get("answer_class_hint")
        answer_class_hint = (
            str(hint).strip() if isinstance(hint, str) and str(hint).strip() else None
        )
        question = _first_user_plain_question(state)
        effective_ac = answer_class_hint or heuristic_answer_class(question, None)
        sess = None
        tid = str((state.get("metadata") or {}).get("thread_id") or "").strip()
        if tid:
            from science_graphrag.agent.context.session_store import get_session_for_thread

            sess = get_session_for_thread(tid)

        bound_tools, _ts_meta = shortlist_tools_for_single_agent(
            tool_registry,
            question=question,
            settings=settings,
            has_workspace=bool((state.get("workspace_id") or "").strip()),
            answer_class=effective_ac,
            session=sess,
        )
        bound_tools, _mtx = apply_allowed_tools_matrix(bound_tools, settings=settings, state=state)
        ts_meta = dict(_ts_meta or {})
        llm_turn = build_chat_model(settings).bind_tools(bound_tools)
        with llm_span(
            "llm.agent.react_turn",
            {"llm.invocation_name": "agent_single_react"},
        ):
            transport = float(settings.extraction_llm_timeout_seconds)
            max_attempts = agent_chat_transport_max_attempts(settings)
            SpanAttributes.set_llm_runtime_policy(
                pool_name="agent_chat",
                transport_timeout_seconds=transport,
                timeout_contract="transport_with_operation_deadline",
                retry_extra_budget=0,
                operation_deadline_seconds=min(
                    900.0,
                    transport * float(max_attempts),
                ),
                transport_max_attempts=max_attempts,
            )
            react_msgs = maybe_compact_agent_messages_for_react(
                state["messages"],
                settings=settings,
            )
            response = invoke_chat_gated(
                llm_turn,
                ensure_messages_safe_for_generation(react_msgs),
                pool_name="agent_chat",
                settings=settings,
            )
        return {
            "messages": [response],
            "debug_events": [
                {
                    "type": "tool_search_result",
                    "specialist": "single_agent_react",
                    "tools": ts_meta.get("matched"),
                    "reason": ts_meta.get("reason"),
                    "top_score": ts_meta.get("top_score"),
                    "score_band": ts_meta.get("score_band"),
                    "catalog_size": ts_meta.get("catalog_size"),
                    "shortlist_size": ts_meta.get("shortlist_size"),
                    "shortlist_ratio": ts_meta.get("shortlist_ratio"),
                    "deferred_schema_mode": ts_meta.get("deferred_schema_mode"),
                    "deferred_schema_refs": ts_meta.get("deferred_schema_refs"),
                    "skipped": bool(ts_meta.get("skipped")),
                    "carryover_tools": ts_meta.get("carryover_tools"),
                }
            ],
        }

    def final_answer_nudge_node(state: AgentState) -> dict:
        add_span_event("agent.final_answer_nudge", {})
        return final_answer_nudge_state_update(state)

    graph = StateGraph(AgentState)
    graph.add_node("chat", chat_node)
    graph.add_node("final_answer_nudge", final_answer_nudge_node)

    graph.add_node("tools", full_tool_node)
    graph.add_node("after_tools", react_after_tools_decrement_budget)
    graph.set_entry_point("chat")
    graph.add_conditional_edges(
        "chat",
        route_react_chat_to_tools,
        {"tools": "tools", "final_answer_nudge": "final_answer_nudge", END: END},
    )
    graph.add_edge("final_answer_nudge", "chat")
    graph.add_edge("tools", "after_tools")
    graph.add_conditional_edges(
        "after_tools",
        route_react_tools_next,
        {"chat": "chat", END: END},
    )
    return graph.compile()
