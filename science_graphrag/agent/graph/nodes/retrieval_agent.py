"""Retrieval specialist node for multi-agent supervisor."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, StateGraph

from science_graphrag.agent.forked_runtime import run_claim_verification_fork_bundle
from science_graphrag.agent.graph.react_edges import (
    react_after_tools_decrement_budget,
    react_chat_response_budget_cutoff,
    route_react_chat_to_tools,
    route_react_tools_next,
)
from science_graphrag.agent.graph.state import AgentState
from science_graphrag.agent.hooks.subagent_hooks import TerminalState as SubagentHookTerminalState
from science_graphrag.agent.hooks.subagent_hooks import (
    emit_subagent_start_hook,
    emit_subagent_stop_hook,
)
from science_graphrag.agent.llm.chat import (
    agent_chat_transport_max_attempts,
    build_chat_model,
    ensure_messages_safe_for_generation,
)
from science_graphrag.agent.subagents.specialist_results_v3 import (
    append_claim_verification_leg,
    append_parent_tool_leg,
    empty_specialist_results_v3,
    parse_verdict_from_text,
    prior_specialist_results_v3,
)
from science_graphrag.agent.tool_execution_pipeline import (
    apply_allowed_tools_matrix,
    build_tool_execution_node,
)
from science_graphrag.agent.tool_search import (
    build_tool_search_result_debug_event,
    shortlist_tools_for_specialist,
)
from science_graphrag.agent.tools import build_retrieval_tools
from science_graphrag.api.deps import StoreRegistry
from science_graphrag.config import Settings
from science_graphrag.llm.concurrency import invoke_chat_gated
from science_graphrag.observability.spans import SpanAttributes, add_span_event, llm_span

SPECIALIST_NAME = "retrieval_agent"


def _hook_terminal_state(term: str) -> SubagentHookTerminalState:
    if term == "timed_out":
        return "timed_out"
    if term == "cancelled":
        return "cancelled"
    if term == "succeeded":
        return "succeeded"
    return "failed"


SYSTEM_PROMPT = (
    "You are a retrieval specialist for a research workspace. Callable tools: "
    "workspace_inspect (mode=stats|papers|blurb — stats for counts, papers for title list, blurb for "
    "short summary + sample work ids), find_works (full-text work search; pass workspace_id when the "
    "user means this workspace, omit for corpus-wide search), paper_profile (metadata + authors for "
    "one work_id), paper_quote_search (semantic chunk quotes), format_bibliography_gost, idea_search. "
    "When <active_workspace_id> appears in the user message, use that exact UUID as workspace_id for "
    "workspace_inspect and for find_works whenever the question is scoped to this workspace. "
    "Use find_works (without workspace_id) only for global title search. Call paper_profile only "
    "when you have a real work_id (from find_works, workspace_inspect mode=papers or blurb—not "
    "stats alone). Use idea_search for open semantic discovery; use paper_quote_search for "
    "verbatim evidence. Return findings through tool outputs only. Do not call final_answer."
)


def _extract_tool_payloads(messages: list[Any], from_index: int) -> list[dict]:
    payloads: list[dict] = []
    for msg in messages[from_index:]:
        if not isinstance(msg, ToolMessage):
            continue
        content = msg.content
        if not isinstance(content, str):
            continue
        try:
            parsed = json.loads(content)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(parsed, dict):
            payloads.append(parsed)
    return payloads


def _last_user_text(state: AgentState) -> str:
    for msg in reversed(list(state.get("messages") or [])):
        if isinstance(msg, HumanMessage):
            return str(msg.content or "")
    return ""


def _compile_react_subgraph(
    tools: list[BaseTool],
    settings: Settings,
    system_prompt: str,
    *,
    sidechain_tag: str,
) -> Any:
    llm = build_chat_model(settings).bind_tools(tools)

    def chat_node(state: AgentState) -> dict:
        cutoff = react_chat_response_budget_cutoff(state, settings=settings)
        if cutoff is not None:
            add_span_event(
                "agent.response_budget_precheck_cutoff",
                {
                    "deadline_kind": "response_only",
                    "min_hop_reserve_seconds": float(settings.agent_min_llm_hop_reserve_seconds),
                    "specialist": SPECIALIST_NAME,
                },
            )
            return cutoff
        with llm_span(
            "llm.agent.retrieval_specialist",
            {"llm.invocation_name": "agent_retrieval_specialist"},
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
            response = invoke_chat_gated(
                llm,
                ensure_messages_safe_for_generation(
                    [HumanMessage(content=system_prompt), *list(state.get("messages") or [])]
                ),
                pool_name="agent_chat",
                settings=settings,
            )
        return {"messages": [response]}

    graph = StateGraph(AgentState)
    graph.add_node("chat", chat_node)
    graph.add_node(
        "tools",
        build_tool_execution_node(
            tools=tools,
            settings=settings,
            sidechain_id=f"{SPECIALIST_NAME}:{sidechain_tag}",
        ),
    )
    graph.add_node("after_tools", react_after_tools_decrement_budget)
    graph.set_entry_point("chat")
    graph.add_conditional_edges(
        "chat",
        route_react_chat_to_tools,
        # Retrieval tools do not include ``final_answer``; end the subgraph if the model
        # would have been nudged (plain text after catalog tools).
        {"tools": "tools", "final_answer_nudge": END, END: END},
    )
    graph.add_edge("tools", "after_tools")
    graph.add_conditional_edges(
        "after_tools",
        route_react_tools_next,
        {"chat": "chat", END: END},
    )
    return graph.compile()


def build_retrieval_subgraph(stores: StoreRegistry, settings: Settings) -> Any:
    """Compile retrieval ReAct subgraph with the full tool set (tests / diagnostics)."""
    all_tools = build_retrieval_tools(stores, settings)
    return _compile_react_subgraph(
        all_tools, settings, SYSTEM_PROMPT, sidechain_tag="diagnostics_full"
    )


def build_retrieval_agent_node(stores: StoreRegistry, settings: Settings):
    """Build retrieval specialist callable for supervisor graph."""
    subgraph_cache: dict[tuple[str, ...], Any] = {}
    subgraph_tags: dict[tuple[str, ...], str] = {}
    seq = {"n": 0}

    def _cached_subgraph(tools: list[BaseTool]) -> Any:
        key = tuple(sorted(getattr(t, "name", "") or "" for t in tools))
        if key not in subgraph_cache:
            seq["n"] += 1
            tag = subgraph_tags.setdefault(key, f"h{seq['n']}")
            subgraph_cache[key] = _compile_react_subgraph(
                tools, settings, SYSTEM_PROMPT, sidechain_tag=tag
            )
        return subgraph_cache[key]

    def retrieval_agent_node(state: AgentState) -> dict:
        before = len(state.get("messages") or [])
        all_tools = build_retrieval_tools(stores, settings)
        sess = None
        tid = str((state.get("metadata") or {}).get("thread_id") or "").strip()
        if tid:
            from science_graphrag.agent.context.session_store import get_session_for_thread

            sess = get_session_for_thread(tid)
        question = _last_user_text(state)
        has_ws = bool((state.get("workspace_id") or "").strip())
        ac = state.get("answer_class")
        answer_class = str(ac).strip() if isinstance(ac, str) and ac.strip() else None
        tools, meta = shortlist_tools_for_specialist(
            all_tools,
            question=question,
            specialist=SPECIALIST_NAME,
            settings=settings,
            has_workspace=has_ws,
            answer_class=answer_class,
            session=sess,
            lc_messages=list(state.get("messages") or []),
        )
        tools, mtx = apply_allowed_tools_matrix(tools, settings=settings, state=state)
        compiled = _cached_subgraph(tools)
        next_state = compiled.invoke(state)
        messages = list(next_state.get("messages") or [])
        specialist_results = dict(
            next_state.get("specialist_results") or state.get("specialist_results") or {}
        )
        # Accumulate across multiple supervisor visits: last hop may add no ToolMessages
        # (budget/route end) and must not wipe payloads from earlier hops in the same turn.
        new_payloads = _extract_tool_payloads(messages, before)
        prior = list(specialist_results.get(SPECIALIST_NAME) or [])
        specialist_results[SPECIALIST_NAME] = prior + new_payloads

        prev_v3 = prior_specialist_results_v3(state, next_state)
        if new_payloads:
            sr3 = append_parent_tool_leg(
                prev_v3,
                specialist_id=SPECIALIST_NAME,
                tool_payloads=new_payloads,
            )
        else:
            sr3 = prev_v3 if isinstance(prev_v3, dict) else empty_specialist_results_v3()
        extra_msgs: list[HumanMessage] = []
        extra_debug: list[dict[str, Any]] = []
        meta_out = dict(state.get("metadata") or {})
        spawn_rows = list(meta_out.get("subagent_spawn_rows") or [])
        parent_tid = str(meta_out.get("parent_turn_id") or "").strip()

        if (
            bool(getattr(settings, "agent_claim_verification_enabled", False))
            and str(settings.agent_runtime or "").strip() == "langgraph_supervisor_v3"
            and new_payloads
        ):
            cv_variants = meta_out.get("claim_verification_variant_suffixes")
            variant_list = (
                [str(x) for x in cv_variants if str(x).strip()]
                if isinstance(cv_variants, list)
                else None
            )
            cv_results = run_claim_verification_fork_bundle(
                stores=stores,
                settings=settings,
                question=question,
                retrieval_payloads=new_payloads,
                workspace_id=state.get("workspace_id"),
                thread_id=tid or None,
                agent_runtime=str(meta_out.get("agent_runtime") or settings.agent_runtime),
                variant_prompt_suffixes=variant_list,
            )
            cv_bucket = list(specialist_results.get("claim_verification") or [])
            for cv in cv_results:
                sid = str(cv.get("subagent_id") or "cv-unknown")
                term = str(cv.get("terminal_state") or "failed")
                fc = cv.get("failure_code")
                lat = cv.get("latency_ms")
                hook_local: list[dict[str, Any]] = []
                if parent_tid:
                    emit_subagent_start_hook(
                        out=hook_local,
                        subagent_id=sid,
                        parent_turn_id=parent_tid,
                        spawn_reason="claim_verification",
                        leg_kind="spawned",
                        execution_mode="sync",
                    )
                    emit_subagent_stop_hook(
                        out=hook_local,
                        subagent_id=sid,
                        parent_turn_id=parent_tid,
                        spawn_reason="claim_verification",
                        terminal_state=_hook_terminal_state(term),
                        leg_kind="spawned",
                        latency_ms=int(lat) if isinstance(lat, int) else None,
                        failure_code=str(fc) if fc is not None else None,
                    )
                    extra_debug.extend(hook_local)
                spawn_rows.append(
                    {
                        "subagent_id": sid,
                        "parent_turn_id": parent_tid,
                        "spawn_reason": "claim_verification",
                        "terminal_state": term,
                        "latency_ms": int(lat) if isinstance(lat, int) else None,
                        "failure_code": fc,
                        "tokens": None,
                        "cost_usd_estimate": None,
                        "kind": "spawned",
                    }
                )
                sr3 = append_claim_verification_leg(
                    sr3,
                    subagent_id=sid,
                    text=str(cv.get("text") or ""),
                    terminal_state=term,
                    failure_code=str(fc) if fc is not None else None,
                    issues=list(cv.get("issues") or []),
                    salvage_used=bool(cv.get("salvage_used")),
                )
                verdict = parse_verdict_from_text(str(cv.get("text") or ""))
                cv_bucket.append(
                    {
                        "subagent_id": sid,
                        "text": str(cv.get("text") or "")[:8000],
                        "issues": list(cv.get("issues") or [])[:24],
                        "terminal_state": term,
                        "failure_code": fc,
                        "verdict": verdict,
                    }
                )
                extra_msgs.append(
                    HumanMessage(
                        content="",
                        additional_kwargs={
                            "kind": "claim_verification_result",
                            "claim_verification_result": {
                                "schema_version": 1,
                                "subagent_id": sid,
                                "parent_turn_id": parent_tid or None,
                                "verdict": verdict,
                                "issues": list(cv.get("issues") or [])[:24],
                                "terminal_state": term,
                                "failure_code": fc,
                                "latency_ms": lat,
                            },
                        },
                    )
                )
            specialist_results["claim_verification"] = cv_bucket

        meta_out["subagent_spawn_rows"] = spawn_rows
        out: dict[str, Any] = {
            "messages": messages + extra_msgs,
            "budget_remaining": int(
                next_state.get("budget_remaining", state.get("budget_remaining", 0))
            ),
            "specialist_results": specialist_results,
            "specialist_results_v3": sr3,
            "current_specialist": SPECIALIST_NAME,
            "metadata": meta_out,
        }
        out["debug_events"] = [
            build_tool_search_result_debug_event(specialist=SPECIALIST_NAME, meta=meta),
            *(
                [{"type": "tool_permissions", "matrix": mtx}]
                if not bool(mtx.get("skipped"))
                else []
            ),
            *extra_debug,
        ]
        return out

    return retrieval_agent_node
