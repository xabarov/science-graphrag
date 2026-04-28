"""Tests for agent chat envelope builder (Wave A CH1)."""

from __future__ import annotations

from langchain_core.messages import HumanMessage

from science_graphrag.agent.chat_envelope import build_chat_envelope, heuristic_answer_class
from science_graphrag.agent.graph.state import AgentState


def test_build_chat_envelope_merges_inventory_from_specialist_results() -> None:
    state: AgentState = {
        "messages": [HumanMessage(content="list papers")],
        "workspace_id": "ws1",
        "citations": [],
        "tool_trace": [],
        "budget_remaining": 8,
        "metadata": {"raw_user_question": "list papers"},
        "specialist_results": {
            "retrieval_agent": [
                {"inventory": {"papers": [{"work_id": "w1", "title": "T"}]}, "row_count": 1},
            ],
        },
        "current_specialist": None,
        "routing_log": [],
        "debug_events": [],
        "thread_id": None,
        "session_summary": "",
        "answer_class": None,
        "history_digest": [],
    }
    trace = [{"step": 1, "tool": "workspace_inspect", "args_summary": {}, "row_count": 1}]
    env = build_chat_envelope(
        state=state,
        answer="ok",
        citations=[],
        tool_trace=trace,  # type: ignore[arg-type]
        answer_class_hint=None,
    )
    assert env.get("answer_class") == "inventory"
    assert env.get("inventory", {}).get("papers")


def test_no_workspace_warning_when_missing_workspace() -> None:
    state: AgentState = {
        "messages": [],
        "workspace_id": None,
        "citations": [],
        "tool_trace": [],
        "budget_remaining": 5,
        "metadata": {"raw_user_question": "q"},
        "specialist_results": {},
        "current_specialist": None,
        "routing_log": [],
        "debug_events": [],
        "thread_id": None,
        "session_summary": "",
        "answer_class": None,
        "history_digest": [],
    }
    env = build_chat_envelope(
        state=state,
        answer="x",
        citations=[],
        tool_trace=[],
        answer_class_hint=None,
    )
    assert "no_workspace" in (env.get("warnings") or [])


def test_no_quote_found_for_quote_class_without_payload() -> None:
    state: AgentState = {
        "messages": [],
        "workspace_id": "w1",
        "citations": [],
        "tool_trace": [],
        "budget_remaining": 5,
        "metadata": {"raw_user_question": "цитат"},
        "specialist_results": {},
        "current_specialist": None,
        "routing_log": [],
        "debug_events": [],
        "thread_id": None,
        "session_summary": "",
        "answer_class": None,
        "history_digest": [],
    }
    env = build_chat_envelope(
        state=state,
        answer="x",
        citations=[],
        tool_trace=[],
        answer_class_hint="quote_extraction",
    )
    assert "no_quote_found" in (env.get("warnings") or [])


def test_no_quote_found_after_idea_hits_when_trace_order_matches() -> None:
    state: AgentState = {
        "messages": [],
        "workspace_id": "w1",
        "citations": [],
        "tool_trace": [],
        "budget_remaining": 5,
        "metadata": {"raw_user_question": "цитат"},
        "specialist_results": {},
        "current_specialist": None,
        "routing_log": [],
        "debug_events": [],
        "thread_id": None,
        "session_summary": "",
        "answer_class": None,
        "history_digest": [],
    }
    trace = [
        {"tool": "idea_search", "row_count": 3},
        {"tool": "paper_quote_search", "row_count": 0},
        {"tool": "final_answer", "row_count": 1},
    ]
    env = build_chat_envelope(
        state=state,
        answer="x",
        citations=[],
        tool_trace=trace,
        answer_class_hint="quote_extraction",
    )
    assert "no_quote_found_after_idea_hits" in (env.get("warnings") or [])
    assert "no_quote_found" not in (env.get("warnings") or [])


def test_weak_evidence_grounded_without_citations() -> None:
    state: AgentState = {
        "messages": [],
        "workspace_id": "w1",
        "citations": [],
        "tool_trace": [],
        "budget_remaining": 5,
        "metadata": {"raw_user_question": "discuss method"},
        "specialist_results": {},
        "current_specialist": None,
        "routing_log": [],
        "debug_events": [],
        "thread_id": None,
        "session_summary": "",
        "answer_class": None,
        "history_digest": [],
    }
    env = build_chat_envelope(
        state=state,
        answer="x",
        citations=[],
        tool_trace=[],
        answer_class_hint="grounded_explanation",
    )
    assert "weak_evidence" in (env.get("warnings") or [])


def test_graph_only_trace() -> None:
    state: AgentState = {
        "messages": [],
        "workspace_id": "w1",
        "citations": [{"work_id": "a"}],
        "tool_trace": [],
        "budget_remaining": 5,
        "metadata": {"raw_user_question": "q"},
        "specialist_results": {},
        "current_specialist": None,
        "routing_log": [],
        "debug_events": [],
        "thread_id": None,
        "session_summary": "",
        "answer_class": None,
        "history_digest": [],
    }
    tool_trace: list[dict] = [  # type: ignore[assignment]
        {
            "step": 1,
            "tool": "edge_search",
            "args_summary": {},
            "row_count": 1,
            "duration_ms": 0,
            "truncated": False,
            "error": None,
        }
    ]
    env = build_chat_envelope(
        state=state,
        answer="x",
        citations=[{"work_id": "a"}],
        tool_trace=tool_trace,  # type: ignore[arg-type]
        answer_class_hint="grounded_explanation",
    )
    assert "graph_only" in (env.get("warnings") or [])
    assert "graph_only" not in (env.get("product_markers") or [])


def test_bibliography_filtered_merges_warnings_to_top_level() -> None:
    state: AgentState = {
        "messages": [HumanMessage(content="гост список")],
        "workspace_id": "ws1",
        "citations": [{"work_id": "w1"}],
        "tool_trace": [],
        "budget_remaining": 5,
        "metadata": {"raw_user_question": "гост список"},
        "specialist_results": {
            "retrieval_agent": [
                {
                    "bibliography": {
                        "format": "gost",
                        "entries": ["Line 1"],
                        "filtered_work_ids": ["x"],
                        "warnings": ["some_work_ids_filtered"],
                    }
                }
            ],
        },
        "current_specialist": None,
        "routing_log": [],
        "debug_events": [],
        "thread_id": None,
        "session_summary": "",
        "answer_class": None,
        "history_digest": [],
    }
    trace = [{"step": 1, "tool": "format_bibliography_gost", "args_summary": {}, "row_count": 1}]
    env = build_chat_envelope(
        state=state,
        answer="ok",
        citations=[{"work_id": "w1"}],
        tool_trace=trace,  # type: ignore[arg-type]
        answer_class_hint=None,
    )
    w = env.get("warnings") or []
    assert "some_work_ids_filtered" in w
    assert env.get("bibliography", {}).get("filtered_work_ids") == ["x"]


def test_envelope_no_tools_turn_policy_ignores_trace_inventory() -> None:
    """Conversational turns must not inherit inventory from accidental tool names in trace."""
    state: AgentState = {
        "messages": [HumanMessage(content="привет")],
        "workspace_id": "ws1",
        "citations": [],
        "tool_trace": [],
        "budget_remaining": 8,
        "metadata": {
            "raw_user_question": "привет",
            "turn_policy": {
                "conversation_intent": "small_talk",
                "tool_policy": "no_tools",
                "route_hint": "writer_agent",
                "reason": "small_talk_pattern",
                "suggested_answer_class": "chat",
            },
        },
        "specialist_results": {},
        "current_specialist": None,
        "routing_log": [],
        "debug_events": [],
        "thread_id": None,
        "session_summary": "",
        "answer_class": None,
        "history_digest": [],
    }
    trace = [{"step": 1, "tool": "workspace_inspect", "args_summary": {}, "row_count": 3}]
    env = build_chat_envelope(
        state=state,
        answer="Здравствуйте!",
        citations=[],
        tool_trace=trace,  # type: ignore[arg-type]
        answer_class_hint=None,
    )
    assert env.get("answer_class") == "chat"
    assert env.get("inventory") is None


def test_collect_typed_payloads_bibliography_gost_without_entries() -> None:
    from science_graphrag.agent.chat_envelope import collect_typed_payloads

    state: AgentState = {
        "messages": [],
        "workspace_id": "ws1",
        "citations": [],
        "tool_trace": [],
        "budget_remaining": 8,
        "metadata": {},
        "specialist_results": {
            "retrieval_agent": [
                {"bibliography": {"format": "gost", "entries": [], "warnings": ["no_works"]}}
            ]
        },
        "current_specialist": None,
        "routing_log": [],
        "debug_events": [],
        "thread_id": None,
        "session_summary": "",
        "answer_class": None,
        "history_digest": [],
    }
    typed = collect_typed_payloads(state)
    assert typed.get("bibliography", {}).get("format") == "gost"


def test_collect_typed_payloads_merges_relation_trace() -> None:
    from science_graphrag.agent.chat_envelope import collect_typed_payloads

    state: AgentState = {
        "messages": [],
        "workspace_id": "ws1",
        "citations": [],
        "tool_trace": [],
        "budget_remaining": 8,
        "metadata": {},
        "specialist_results": {
            "graph_agent": [{"relation_trace": {"edges": [{"type": "CITES"}]}}],
        },
        "current_specialist": None,
        "routing_log": [],
        "debug_events": [],
        "thread_id": None,
        "session_summary": "",
        "answer_class": None,
        "history_digest": [],
    }
    typed = collect_typed_payloads(state)
    assert typed.get("relation_trace", {}).get("edges")


def test_infer_class_from_trace_prefers_relation_over_inventory() -> None:
    from science_graphrag.agent.chat_envelope import infer_class_from_trace

    names = {"workspace_inspect", "edge_search"}
    assert infer_class_from_trace(names) == "relation_tracing"


def test_build_chat_envelope_extra_warnings_and_markers() -> None:
    state: AgentState = {
        "messages": [HumanMessage(content="q")],
        "workspace_id": "ws1",
        "citations": [],
        "tool_trace": [],
        "budget_remaining": 5,
        "metadata": {"raw_user_question": "q"},
        "specialist_results": {},
        "current_specialist": None,
        "routing_log": [],
        "debug_events": [],
        "thread_id": None,
        "session_summary": "",
        "answer_class": None,
        "history_digest": [],
    }
    env = build_chat_envelope(
        state=state,
        answer="ok",
        citations=[{"work_id": "w1"}],
        tool_trace=[{"step": 1, "tool": "idea_search", "args_summary": {}, "row_count": 1}],
        answer_class_hint=None,
        extra_warnings=["agent_turn_deadline_exceeded", "partial_after_deadline"],
        extra_product_markers=["partial_after_deadline"],
    )
    warns = list(env.get("warnings") or [])
    assert "agent_turn_deadline_exceeded" in warns
    assert "partial_after_deadline" in warns
    markers = list(env.get("product_markers") or [])
    assert "partial_after_deadline" in markers


def test_build_chat_envelope_graph_salvage_skips_agent_finished_without_final_answer() -> None:
    state: AgentState = {
        "messages": [HumanMessage(content="q")],
        "workspace_id": "ws1",
        "citations": [],
        "tool_trace": [],
        "budget_remaining": 0,
        "metadata": {"raw_user_question": "q", "turn_policy": {"tool_policy": "allow_tools"}},
        "specialist_results": {},
        "current_specialist": None,
        "routing_log": [],
        "debug_events": [],
        "thread_id": None,
        "session_summary": "",
        "answer_class": None,
        "history_digest": [],
    }
    trace = [
        {"step": 1, "tool": "cypher_query", "args_summary": {}, "row_count": 1},
    ]
    env = build_chat_envelope(
        state=state,
        answer="Salvaged graph preview text",
        citations=[],
        tool_trace=trace,  # type: ignore[arg-type]
        answer_class_hint=None,
        extra_warnings=["answer_salvaged_from_graph_tool"],
    )
    assert "answer_salvaged_from_graph_tool" in (env.get("warnings") or [])
    assert "agent_finished_without_final_answer_tool" not in (env.get("warnings") or [])


def test_build_chat_envelope_warns_agent_finished_without_final_answer_tool() -> None:
    state: AgentState = {
        "messages": [HumanMessage(content="q")],
        "workspace_id": "ws1",
        "citations": [],
        "tool_trace": [],
        "budget_remaining": 0,
        "metadata": {"raw_user_question": "q", "turn_policy": {"tool_policy": "allow_tools"}},
        "specialist_results": {},
        "current_specialist": None,
        "routing_log": [],
        "debug_events": [],
        "thread_id": None,
        "session_summary": "",
        "answer_class": None,
        "history_digest": [],
    }
    trace = [
        {"step": 1, "tool": "workspace_inspect", "args_summary": {}, "row_count": 1},
        {"step": 2, "tool": "paper_profile", "args_summary": {}, "row_count": 1},
    ]
    env = build_chat_envelope(
        state=state,
        answer="Some synthesized text",
        citations=[],
        tool_trace=trace,  # type: ignore[arg-type]
        answer_class_hint=None,
    )
    assert "agent_finished_without_final_answer_tool" in (env.get("warnings") or [])


def test_build_chat_envelope_no_warn_when_last_tool_is_final_answer() -> None:
    state: AgentState = {
        "messages": [HumanMessage(content="q")],
        "workspace_id": "ws1",
        "citations": [],
        "tool_trace": [],
        "budget_remaining": 0,
        "metadata": {"raw_user_question": "q"},
        "specialist_results": {},
        "current_specialist": None,
        "routing_log": [],
        "debug_events": [],
        "thread_id": None,
        "session_summary": "",
        "answer_class": None,
        "history_digest": [],
    }
    trace = [
        {"step": 1, "tool": "workspace_inspect", "args_summary": {}, "row_count": 1},
        {"step": 2, "tool": "final_answer", "args_summary": {}, "row_count": 0},
    ]
    env = build_chat_envelope(
        state=state,
        answer="Done",
        citations=[],
        tool_trace=trace,  # type: ignore[arg-type]
        answer_class_hint=None,
    )
    assert "agent_finished_without_final_answer_tool" not in (env.get("warnings") or [])


def test_heuristic_answer_class_evidence_tradeoff_is_quote_extraction() -> None:
    q = (
        "What trade-offs between speed and accuracy for real-time object detection does this "
        "workspace support with evidence? Use at least two distinct retrieval paths."
    )
    assert heuristic_answer_class(q, None) == "quote_extraction"


def test_heuristic_answer_class_hint_overrides_question() -> None:
    q = (
        "What trade-offs between speed and accuracy for real-time object detection does this "
        "workspace support with evidence?"
    )
    assert heuristic_answer_class(q, "inventory") == "inventory"
