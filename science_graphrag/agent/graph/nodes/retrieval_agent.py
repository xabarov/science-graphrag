"""Retrieval specialist node for multi-agent supervisor (thin assembly over Wave A seams)."""

from __future__ import annotations

from typing import Any

from science_graphrag.agent.graph.nodes.retrieval_completion import (
    annotate_retrieval_completion_state,
)
from science_graphrag.agent.graph.nodes.retrieval_fork_legs import run_retrieval_fork_bundles
from science_graphrag.agent.graph.nodes.retrieval_subgraph import (
    SYSTEM_PROMPT,
    _compile_react_subgraph,
    _extract_tool_payloads,
    _last_user_text,
)
from science_graphrag.agent.graph.nodes.retrieval_subgraph import (
    build_retrieval_subgraph as build_retrieval_subgraph_impl,
)
from science_graphrag.agent.graph.state import AgentState
from science_graphrag.agent.subagents.specialist_results_v3 import (
    append_parent_tool_leg,
    empty_specialist_results_v3,
    prior_specialist_results_v3,
)
from science_graphrag.agent.tool_execution_pipeline import apply_allowed_tools_matrix
from science_graphrag.agent.tool_search import (
    build_tool_search_result_debug_event,
    shortlist_tools_for_specialist,
)
from science_graphrag.agent.tools import build_retrieval_tools
from science_graphrag.stores.registry import StoreRegistry
from science_graphrag.config import Settings

SPECIALIST_NAME = "retrieval_agent"


def build_retrieval_subgraph(stores: StoreRegistry, settings: Settings) -> Any:
    """Compile retrieval ReAct subgraph with the full tool set (tests / diagnostics)."""
    return build_retrieval_subgraph_impl(stores, settings, specialist_name=SPECIALIST_NAME)


def build_retrieval_agent_node(stores: StoreRegistry, settings: Settings):
    """Build retrieval specialist callable for supervisor graph."""
    subgraph_cache: dict[tuple[str, ...], Any] = {}
    subgraph_tags: dict[tuple[str, ...], str] = {}
    seq = {"n": 0}

    def _cached_subgraph(tools: list[Any]) -> Any:
        key = tuple(sorted(getattr(t, "name", "") or "" for t in tools))
        if key not in subgraph_cache:
            seq["n"] += 1
            tag = subgraph_tags.setdefault(key, f"h{seq['n']}")
            subgraph_cache[key] = _compile_react_subgraph(
                tools,
                settings,
                SYSTEM_PROMPT,
                specialist_name=SPECIALIST_NAME,
                sidechain_tag=tag,
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

        sr3 = annotate_retrieval_completion_state(
            sr3=sr3,
            messages=messages,
            question=question,
            state=state,
            new_payloads=new_payloads,
            specialist_results=specialist_results,
            specialist_name=SPECIALIST_NAME,
        )

        meta_out = dict(state.get("metadata") or {})
        spawn_rows = list(meta_out.get("subagent_spawn_rows") or [])
        parent_tid = str(meta_out.get("parent_turn_id") or "").strip()

        fork_msgs, fork_debug, fork_spawns = run_retrieval_fork_bundles(
            stores=stores,
            settings=settings,
            state=state,
            question=question,
            new_payloads=new_payloads,
            tid=tid,
            parent_tid=parent_tid,
            sr3=sr3,
            specialist_results=specialist_results,
            meta_out=meta_out,
        )
        spawn_rows.extend(fork_spawns)
        meta_out["subagent_spawn_rows"] = spawn_rows

        out: dict[str, Any] = {
            "messages": messages + fork_msgs,
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
            *fork_debug,
        ]
        return out

    return retrieval_agent_node
