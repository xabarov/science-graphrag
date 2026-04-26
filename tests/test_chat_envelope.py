"""Tests for agent chat envelope builder (Wave A CH1)."""

from __future__ import annotations

from langchain_core.messages import HumanMessage

from science_graphrag.agent.chat_envelope import build_chat_envelope
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
    trace = [{"step": 1, "tool": "workspace_list_papers", "args_summary": {}, "row_count": 1}]
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
            "tool": "entity_search",
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
