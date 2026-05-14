"""LangGraph multi-agent supervisor graph (Wave Y4)."""

from __future__ import annotations

from typing import Any, Literal

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph

from science_graphrag.agent.chat_envelope import heuristic_answer_class
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
from science_graphrag.agent.graph.partial_state_checkpoint import record_partial_state
from science_graphrag.agent.graph.react_edges import (
    final_answer_nudge_state_update,
    react_after_tools_decrement_budget,
    react_chat_response_budget_cutoff,
    route_react_chat_to_tools,
    route_react_tools_next,
)
from science_graphrag.agent.graph.state import AgentState
from science_graphrag.agent.graph.supervisor_decisions import (
    compute_first_hop_decision,
    compute_post_retrieval_handoff,
    compute_round_cap_decision,
    first_user_plain_question,
    maybe_replan_via_llm,
    should_skip_llm_router,
)
from science_graphrag.agent.llm.chat import (
    agent_chat_transport_max_attempts,
    build_chat_model,
    ensure_messages_safe_for_generation,
)
from science_graphrag.agent.subagents.lifecycle import merge_routing_leg_notifications_into_update
from science_graphrag.agent.tool_call_normalization import normalize_tool_call_name
from science_graphrag.agent.tool_execution_pipeline import (
    apply_allowed_tools_matrix,
    build_tool_execution_node,
    effective_tool_policy,
)
from science_graphrag.agent.tool_message_compact import maybe_compact_agent_messages_for_react
from science_graphrag.agent.tool_search import (
    build_tool_search_result_debug_event,
    shortlist_tools_for_single_agent,
)
from science_graphrag.agent.tools import build_tool_registry
from science_graphrag.stores.registry import StoreRegistry
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
    """Re-export of :func:`first_user_plain_question` for legacy single-agent fallback."""
    return first_user_plain_question(state)


def build_supervisor_graph(stores: StoreRegistry, settings: Settings):
    """Build and compile Wave Y4 multi-agent supervisor graph."""
    llm = build_chat_model(settings)
    retrieval_node = build_retrieval_agent_node(stores, settings)
    graph_node = build_graph_agent_node(stores, settings)
    writer_node = build_writer_agent_node(stores, settings)

    def supervisor_node(state: AgentState) -> dict:
        # Snapshot the latest accumulated state for runtime salvage. This is
        # the only place that runs between every specialist hop, so it is
        # the right seam for partial-state checkpointing on global deadline.
        record_partial_state(dict(state))
        budget = int(state.get("budget_remaining", settings.agent_max_tool_calls))
        prior = list(state.get("routing_log") or [])
        tool_policy = effective_tool_policy(state)
        if not prior and tool_policy in {"no_tools", "clarify"}:
            meta = state.get("metadata") or {}
            tp = meta.get("turn_policy") if isinstance(meta.get("turn_policy"), dict) else {}
            reason = str(tp.get("reason") or "coordinator_gate")
            return merge_routing_leg_notifications_into_update(
                state,
                settings,
                {
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
                },
            )
        if budget <= 0:
            return merge_routing_leg_notifications_into_update(
                state,
                settings,
                {
                    "current_specialist": WRITER_SPECIALIST,
                    "routing_log": [
                        *list(state.get("routing_log") or []),
                        {
                            "from": "supervisor",
                            "to": WRITER_SPECIALIST,
                            "reason": "budget_exhausted",
                        },
                    ],
                },
            )
        ready_reason = compute_post_retrieval_handoff(
            state=state,
            settings=settings,
        )
        if ready_reason:
            return merge_routing_leg_notifications_into_update(
                state,
                settings,
                {
                    "current_specialist": WRITER_SPECIALIST,
                    "routing_log": [
                        *list(state.get("routing_log") or []),
                        {
                            "from": "supervisor",
                            "to": WRITER_SPECIALIST,
                            "reason": ready_reason,
                            "budget_left": budget,
                        },
                    ],
                },
            )
        meta = state.get("metadata") or {}
        tp = meta.get("turn_policy") if isinstance(meta.get("turn_policy"), dict) else {}
        route_hint = str(tp.get("route_hint") or "").strip()
        ans_cls = str(state.get("answer_class") or "").strip()

        # First hop / coordinator route_hint / fast-route — delegated to pure helper.
        if not prior:
            first_hop = compute_first_hop_decision(
                state=state,
                settings=settings,
                tool_policy=tool_policy,
                route_hint=route_hint,
                answer_class=ans_cls,
            )
            if first_hop is not None:
                entry: dict[str, Any] = {
                    "from": "supervisor",
                    "to": first_hop.specialist,
                    "reason": first_hop.reason,
                    "budget_left": budget,
                }
                if first_hop.extra:
                    if first_hop.extra.get("from_route_plan"):
                        entry["decision_source"] = "route_plan"
                    for k, v in first_hop.extra.items():
                        if v is None or k == "from_route_plan":
                            continue
                        entry.setdefault(k, v)
                return merge_routing_leg_notifications_into_update(
                    state,
                    settings,
                    {
                        "current_specialist": first_hop.specialist,
                        "routing_log": [entry],
                    },
                )

        round_cap = compute_round_cap_decision(state=state, settings=settings)
        if round_cap.triggered:
            return merge_routing_leg_notifications_into_update(
                state,
                settings,
                {
                    "current_specialist": WRITER_SPECIALIST,
                    "routing_log": [
                        *list(state.get("routing_log") or []),
                        {
                            "from": "supervisor",
                            "to": WRITER_SPECIALIST,
                            "reason": round_cap.reason,
                            "budget_left": budget,
                            "supervisor_hops": round_cap.supervisor_hops,
                        },
                    ],
                },
            )

        # Phase 4: when RoutePlan + replan_only_llm flag are enabled, follow the
        # plan deterministically; LLM router is invoked only on explicit replan.
        plan_choice = should_skip_llm_router(state=state, settings=settings)
        if plan_choice is not None:
            add_span_event(
                "agent.supervisor.route_plan_step",
                {"to": plan_choice, "budget_left": budget},
            )
            return merge_routing_leg_notifications_into_update(
                state,
                settings,
                {
                    "current_specialist": plan_choice,
                    "routing_log": [
                        *list(state.get("routing_log") or []),
                        {
                            "from": "supervisor",
                            "to": plan_choice,
                            "reason": "route_plan_step",
                            "budget_left": budget,
                            "decision_source": "route_plan",
                        },
                    ],
                },
            )

        replan = maybe_replan_via_llm(
            state=state,
            settings=settings,
            llm=llm,
            budget_left=budget,
        )
        return merge_routing_leg_notifications_into_update(
            state,
            settings,
            {
                "current_specialist": replan.specialist,
                "routing_log": [
                    *list(state.get("routing_log") or []),
                    {
                        "from": "supervisor",
                        "to": replan.specialist,
                        "budget_left": budget,
                        "reason": ("supervisor_finish_guard" if replan.finish_remapped else None),
                    },
                ],
            },
        )

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
    if settings.agent_runtime in ("langgraph_supervisor_v1", "langgraph_supervisor_v3"):
        return build_supervisor_graph(stores, settings)
    if settings.agent_runtime in ("retrieval_v1", "langgraph_research_v1"):
        return _build_single_agent_graph(stores, settings)
    # Unknown runtime id: keep supervisor graph for backward compatibility.
    return build_supervisor_graph(stores, settings)


def _build_single_agent_graph(stores: StoreRegistry, settings: Settings):
    """Wave Y2 fallback: single-agent ReAct graph."""
    tool_registry = build_tool_registry(stores, settings)
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
            lc_messages=list(state.get("messages") or []),
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
            react_msgs, compact_audit = maybe_compact_agent_messages_for_react(
                state["messages"],
                settings=settings,
                client_idle_ms=(
                    int(meta["client_idle_ms"])
                    if isinstance(meta.get("client_idle_ms"), int)
                    else None
                ),
            )
            response = invoke_chat_gated(
                llm_turn,
                ensure_messages_safe_for_generation(react_msgs),
                pool_name="agent_chat",
                settings=settings,
            )
        dbg = [
            build_tool_search_result_debug_event(
                specialist="single_agent_react",
                meta=ts_meta,
            )
        ]
        if compact_audit:
            dbg.append({"type": "tool_message_compact_audit", **compact_audit})
        meta_out = dict(state.get("metadata") or {})
        meta_out["react_bound_tool_names"] = [
            n
            for n in (normalize_tool_call_name(getattr(t, "name", "") or "") for t in bound_tools)
            if n
        ]
        return {
            "messages": [response],
            "debug_events": dbg,
            "metadata": meta_out,
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
