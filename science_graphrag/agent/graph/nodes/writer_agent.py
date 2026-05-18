"""Writer specialist node for multi-agent supervisor.

Terminal synthesis seam: the writer subgraph only binds ``final_answer`` (see
``build_writer_tools``). It does not run tool_search shortlisting or expand a
research catalog; routing and evidence gathering stay in supervisor + retrieval/graph.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, StateGraph

from science_graphrag.agent.final_answer_policy import has_completed_final_answer_tool
from science_graphrag.agent.final_answer_validation import is_generic_fallback_answer
from science_graphrag.agent.graph.nodes.retrieval_subgraph import merge_react_subgraph_debug_events
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
from science_graphrag.agent.prompt_protocol_cards import (
    WRITER_BASE_SYSTEM_PROMPT,
    build_writer_terminal_protocol_block,
)
from science_graphrag.agent.runtime_answer_salvage import (
    synthesize_partial_answer_from_specialist_context,
)
from science_graphrag.agent.subagent_output_contract import writer_system_prompt_suffix
from science_graphrag.agent.subagents.lifecycle import (
    coordinator_lane_stub_message,
    messages_for_completed_routing_leg,
)
from science_graphrag.agent.tool_execution_pipeline import (
    apply_allowed_tools_matrix,
    build_tool_execution_node,
)
from science_graphrag.agent.tools import build_writer_tools
from science_graphrag.config import Settings
from science_graphrag.llm.concurrency import invoke_chat_gated
from science_graphrag.observability.spans import SpanAttributes, add_span_event, llm_span
from science_graphrag.stores.registry import StoreRegistry

SPECIALIST_NAME = "writer_agent"
SYSTEM_PROMPT = WRITER_BASE_SYSTEM_PROMPT

DIRECT_SYSTEM_PROMPT = (
    "You are a helpful research assistant in a scholarly workspace UI. "
    "The user's message is conversational (greeting, thanks, or small talk) OR asks who you are / "
    "what you can do. Reply briefly and warmly in the user's language. "
    "Do NOT invent paper titles, workspace inventory, citations, or graph facts — "
    "specialist_results below are empty for this turn. Always call final_answer with citations=[] "
    "(no fabricated sources)."
)

CLARIFY_SYSTEM_PROMPT = (
    "You are a helpful research assistant. The user's request is ambiguous or "
    "too short to run tools. "
    "Ask one short clarifying question in the user's language (e.g. list papers, search ideas, "
    "graph relations, quotes). Do NOT call workspace or search tools yourself. "
    "Always call final_answer with citations=[]."
)


def _collect_writer_context(state: AgentState) -> str:
    v3 = state.get("specialist_results_v3")
    if isinstance(v3, dict) and (v3.get("legs") or v3.get("merge")):
        from science_graphrag.agent.subagents.specialist_results_v3 import serialize_for_writer

        return serialize_for_writer(v3, max_chars=12000)
    specialist_results = state.get("specialist_results") or {}
    return json.dumps(specialist_results, ensure_ascii=True)[:12000]


def _last_user_text(state: AgentState) -> str:
    for msg in reversed(list(state.get("messages") or [])):
        if isinstance(msg, HumanMessage):
            return str(msg.content or "")
    return ""


def _writer_mode_from_state(state: AgentState) -> str:
    meta = state.get("metadata") or {}
    tp = meta.get("turn_policy")
    if isinstance(tp, dict):
        pol = str(tp.get("tool_policy") or "").strip()
        if pol == "no_tools":
            return "direct"
        if pol == "clarify":
            return "clarify"
    return "normal"


def _answer_language_instruction(state: AgentState) -> str:
    """Return an explicit answer-language instruction for the writer."""
    meta = state.get("metadata") or {}
    tp = meta.get("turn_policy") if isinstance(meta, dict) else None
    qf = tp.get("question_features") if isinstance(tp, dict) else None
    lang = str(qf.get("language") or "").strip().lower() if isinstance(qf, dict) else ""
    if lang == "ru":
        return "Answer language: Russian. Keep English paper titles, model names, and domain terms unchanged."
    if lang == "en":
        return "Answer language: English."
    return "Answer language: match the user's instruction language; preserve technical titles as written."


def _system_prompt_for_mode(mode: str, *, settings: Settings) -> str:
    if mode == "direct":
        base = DIRECT_SYSTEM_PROMPT
    elif mode == "clarify":
        base = CLARIFY_SYSTEM_PROMPT
    else:
        base = SYSTEM_PROMPT
    parts = [
        base,
        build_writer_terminal_protocol_block(),
        writer_system_prompt_suffix(settings=settings, writer_mode=mode),
    ]
    return "\n\n".join(parts)


def _compile_writer_subgraph(
    tools: list[BaseTool],
    settings: Settings,
    *,
    mode: str,
    sidechain_tag: str,
    single_pass_shadow: bool,
) -> Any:
    system_prompt = _system_prompt_for_mode(mode, settings=settings)
    llm = build_chat_model(settings).bind_tools(tools)

    def chat_node(state: AgentState) -> dict:
        cutoff = react_chat_response_budget_cutoff(state, settings=settings)
        if cutoff is not None:
            add_span_event(
                "agent.response_budget_precheck_cutoff",
                {
                    "deadline_kind": "response_only",
                    "min_hop_reserve_seconds": float(settings.agent_min_llm_hop_reserve_seconds),
                    "writer_mode": mode,
                },
            )
            return cutoff
        context_message = HumanMessage(
            content=(
                f"{_answer_language_instruction(state)}\n"
                f"specialist_results={_collect_writer_context(state)}"
            )
        )
        base_msgs = [
            HumanMessage(content=system_prompt),
            context_message,
            *list(state.get("messages") or []),
        ]
        with llm_span(
            "llm.agent.writer",
            {"llm.invocation_name": "agent_writer_specialist"},
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
                ensure_messages_safe_for_generation(base_msgs),
                pool_name="agent_chat",
                settings=settings,
            )
        return {"messages": [response]}

    def final_answer_nudge_node(state: AgentState) -> dict:
        add_span_event(
            "agent.final_answer_nudge", {"specialist": SPECIALIST_NAME, "writer_mode": mode}
        )
        return final_answer_nudge_state_update(state)

    subgraph = StateGraph(AgentState)
    subgraph.add_node("chat", chat_node)
    subgraph.add_node("final_answer_nudge", final_answer_nudge_node)
    subgraph.add_node(
        "tools",
        build_tool_execution_node(
            tools=tools,
            settings=settings,
            sidechain_id=f"{SPECIALIST_NAME}:{mode}:{sidechain_tag}",
        ),
    )
    subgraph.add_node("after_tools", react_after_tools_decrement_budget)
    subgraph.set_entry_point("chat")
    subgraph.add_conditional_edges(
        "chat",
        route_react_chat_to_tools,
        {"tools": "tools", "final_answer_nudge": "final_answer_nudge", END: END},
    )
    subgraph.add_edge("final_answer_nudge", "chat")
    subgraph.add_edge("tools", "after_tools")

    def _route_after_tools(state: AgentState):
        if single_pass_shadow:
            add_span_event(
                "agent.writer_single_pass_shadow_cutoff",
                {"specialist": SPECIALIST_NAME, "writer_mode": mode},
            )
            return END
        return route_react_tools_next(state)

    subgraph.add_conditional_edges(
        "after_tools",
        _route_after_tools,
        {"chat": "chat", END: END},
    )
    return subgraph.compile()


def _ensure_final_answer_tool(tools: list[BaseTool], all_tools: list[BaseTool]) -> list[BaseTool]:
    """Guarantee writer subgraph always has ``final_answer`` terminal tool bound."""
    if any(str(getattr(t, "name", "") or "") == "final_answer" for t in tools):
        return tools
    for t in all_tools:
        if str(getattr(t, "name", "") or "") == "final_answer":
            return [*tools, t]
    return tools


def _normalize_synthetic_final_answer_text(text: str) -> str:
    """Strip literalized tool-name prefixes from bare writer output."""

    out = str(text or "").strip()
    lowered = out.lower()
    for prefix in ("final_answer:", "final answer:"):
        if lowered.startswith(prefix):
            return out[len(prefix) :].lstrip()
    return out


def _is_generic_writer_fallback_text(text: str) -> bool:
    return is_generic_fallback_answer(text)


def _synthesize_partial_answer_from_context(
    *,
    citations: list[dict[str, Any]] | None,
    specialist_results_v3: dict[str, Any] | None,
    language: str,
) -> str:
    """Backward-compatible alias for tests and terminal salvage paths."""
    return synthesize_partial_answer_from_specialist_context(
        citations=citations,
        specialist_results_v3=specialist_results_v3,
        language=language,
    )


def _record_synthetic_final_answer_tool_span(
    *,
    answer: str,
    citations: list[dict[str, Any]],
) -> None:
    """Emit ``tool.final_answer`` for writer synthetic closes (tool_trace without ToolNode)."""

    from science_graphrag.agent.tools.base import run_tool_result_with_span
    from science_graphrag.agent.tools.final_answer import FinalAnswerTool

    runtime_tool = FinalAnswerTool()
    run_tool_result_with_span(
        tool_name="final_answer",
        tool_parameters={
            "answer_chars": len(answer or ""),
            "citations_count": len(citations),
            "synthetic": True,
        },
        fn=lambda: runtime_tool.run(answer=answer, citations=citations),
    )


def _ensure_terminal_final_answer_tool_call(
    messages: list[Any],
    *,
    citations: list[dict[str, Any]] | None = None,
    specialist_results_v3: dict[str, Any] | None = None,
    answer_language: str = "unknown",
) -> list[Any]:
    """Close the writer leg with a synthetic ``final_answer`` when only bare text remains."""

    if has_completed_final_answer_tool(messages):
        return messages
    visible_text = ""
    for msg in reversed(messages):
        if not isinstance(msg, AIMessage):
            continue
        if getattr(msg, "tool_calls", None):
            continue
        candidate = _normalize_synthetic_final_answer_text(str(msg.content or ""))
        if candidate.strip():
            visible_text = candidate.strip()
            break
    cits = [c for c in list(citations or []) if isinstance(c, dict)]
    if not visible_text:
        if cits or isinstance(specialist_results_v3, dict):
            visible_text = _synthesize_partial_answer_from_context(
                citations=cits,
                specialist_results_v3=specialist_results_v3,
                language=answer_language,
            )
    elif _is_generic_writer_fallback_text(visible_text) and (
        cits or isinstance(specialist_results_v3, dict)
    ):
        visible_text = _synthesize_partial_answer_from_context(
            citations=cits,
            specialist_results_v3=specialist_results_v3,
            language=answer_language,
        )
    if not visible_text:
        return messages
    _record_synthetic_final_answer_tool_span(answer=visible_text, citations=cits)
    call_id = f"writer_final_answer_fallback_{uuid.uuid4().hex[:12]}"
    payload = {
        "answer": visible_text,
        "citations": cits,
    }
    return [
        *messages,
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "final_answer",
                    "id": call_id,
                    "args": payload,
                    "type": "tool_call",
                }
            ],
        ),
        ToolMessage(
            content=json.dumps(payload, ensure_ascii=False),
            tool_call_id=call_id,
            name="final_answer",
        ),
    ]


def _drop_non_final_tool_calls_from_tail(messages: list[Any]) -> list[Any]:
    """Strip trailing AI tool-call messages that are not ``final_answer``.

    Writer is terminal-only; if the model emits a stray tool call (e.g. arxiv_search),
    keeping it in the tail can route the parent graph to ``END`` without a completed
    ``final_answer``. We keep full history except the trailing non-terminal tool-call tail.
    """
    if not messages:
        return messages
    out = list(messages)
    while out:
        last = out[-1]
        if not isinstance(last, AIMessage):
            break
        tool_calls = list(getattr(last, "tool_calls", None) or [])
        if not tool_calls:
            break
        only_final = all(
            str((tc or {}).get("name") or "").strip() == "final_answer"
            for tc in tool_calls
            if isinstance(tc, dict)
        )
        if only_final:
            break
        out.pop()
    return out


def build_writer_agent_node(stores: StoreRegistry, settings: Settings):
    """Build writer specialist callable for supervisor graph."""
    subgraph_cache: dict[tuple[tuple[str, ...], str], Any] = {}
    subgraph_tags: dict[tuple[tuple[str, ...], str], str] = {}
    seq = {"n": 0}

    def _cached_subgraph(tools: list[BaseTool], mode: str) -> Any:
        shadow = bool(getattr(settings, "agent_writer_terminal_single_pass_shadow_enabled", False))
        key = (tuple(sorted(getattr(t, "name", "") or "" for t in tools)), mode, shadow)
        if key not in subgraph_cache:
            seq["n"] += 1
            tag = subgraph_tags.setdefault(key, f"h{seq['n']}")
            subgraph_cache[key] = _compile_writer_subgraph(
                tools,
                settings,
                mode=mode,
                sidechain_tag=tag,
                single_pass_shadow=shadow,
            )
        return subgraph_cache[key]

    def writer_agent_node(state: AgentState) -> dict:
        all_tools = build_writer_tools(stores)
        mode = _writer_mode_from_state(state)
        # Terminal seam: catalog is only ``final_answer`` — skip rule-based shortlist
        # (see also ``shortlist_tools_for_specialist`` fast-path for writer_agent).
        tools = list(all_tools)
        meta = {
            "skipped": True,
            "reason": "writer_terminal_synthesis_seam",
            "catalog_size": len(tools),
        }
        tools, mtx = apply_allowed_tools_matrix(tools, settings=settings, state=state)
        tools = _ensure_final_answer_tool(tools, all_tools)
        compiled = _cached_subgraph(tools, mode)
        next_state = compiled.invoke(state)
        messages = list(next_state.get("messages") or [])
        messages = _drop_non_final_tool_calls_from_tail(messages)
        tp = (state.get("metadata") or {}).get("turn_policy")
        qf = tp.get("question_features") if isinstance(tp, dict) else None
        answer_language = (
            str(qf.get("language") or "unknown").strip().lower()
            if isinstance(qf, dict)
            else "unknown"
        )
        sr3_for_fallback = next_state.get("specialist_results_v3")
        if not isinstance(sr3_for_fallback, dict):
            sr3_for_fallback = state.get("specialist_results_v3")
        citations_for_terminal = [
            c
            for c in list(next_state.get("citations") or state.get("citations") or [])
            if isinstance(c, dict)
        ]
        messages = _ensure_terminal_final_answer_tool_call(
            messages,
            citations=citations_for_terminal,
            specialist_results_v3=sr3_for_fallback if isinstance(sr3_for_fallback, dict) else None,
            answer_language=answer_language,
        )
        combo: AgentState = dict(state)
        nsr = next_state.get("specialist_results")
        if isinstance(nsr, dict):
            combo["specialist_results"] = nsr
        nsr3 = next_state.get("specialist_results_v3")
        if isinstance(nsr3, dict):
            combo["specialist_results_v3"] = nsr3
        elif isinstance(state.get("specialist_results_v3"), dict):
            combo["specialist_results_v3"] = state.get("specialist_results_v3")
        combo["current_specialist"] = SPECIALIST_NAME
        terminal_msgs = messages_for_completed_routing_leg(
            combo,
            settings,
            completed_subagent_id=SPECIALIST_NAME,
            next_subagent_id=SPECIALIST_NAME,
            force_terminal=True,
        )
        stub_lane = coordinator_lane_stub_message(combo, settings)
        messages = messages + terminal_msgs + stub_lane
        citations = list(state.get("citations") or [])
        for msg in reversed(messages):
            if isinstance(msg, ToolMessage) and isinstance(msg.content, str):
                try:
                    payload = json.loads(msg.content)
                except Exception:  # noqa: BLE001
                    continue
                if isinstance(payload, dict) and payload.get("citations"):
                    citations = list(payload.get("citations") or [])
                    break
        return {
            "messages": messages,
            "budget_remaining": int(
                next_state.get("budget_remaining", state.get("budget_remaining", 0))
            ),
            "citations": citations,
            "current_specialist": SPECIALIST_NAME,
            "debug_events": merge_react_subgraph_debug_events(
                specialist=SPECIALIST_NAME,
                tool_search_meta=meta,
                permissions_matrix=mtx,
                subgraph_state=next_state,
                writer_mode=mode,
            ),
        }

    return writer_agent_node
