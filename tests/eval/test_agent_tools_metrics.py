"""Unit tests for agent_tools benchmark scoring."""

from __future__ import annotations

from eval.agent_tools.metrics import score_agent_case


def test_score_agent_case_subsequence_ignores_routing() -> None:
    report = {
        "answer": "ok",
        "citations": [],
        "tool_trace": [
            {"tool": "route_to_specialist", "args_summary": {"to": "retrieval_agent"}},
            {"tool": "idea_search", "args_summary": {}},
            {"tool": "workspace_inspect", "args_summary": {}},
            {"tool": "final_answer", "args_summary": {}},
        ],
        "routing_log": [],
    }
    gold = {
        "max_calls": 8,
        "min_tool_call_correctness": 0.7,
        "expected_tool_sequence": [{"tool": "idea_search"}, {"tool": "final_answer"}],
    }
    m = score_agent_case(report, gold)
    assert m["tool_call_correctness"] == 1.0
    assert m["tool_budget_ok"] is True
    assert m["passed"] is True


def test_score_agent_case_normalizes_tool_name_and_args_match() -> None:
    report = {
        "answer": "ok",
        "citations": [],
        "tool_trace": [
            {
                "tool": "vector_search",
                "args_summary": {"q": "focal loss dense detector"},
            },
            {"tool": "cypher_query", "args_summary": {"query": "MATCH focal_loss MENTIONS_METHOD"}},
        ],
    }
    gold = {
        "max_calls": 8,
        "min_tool_call_correctness": 1.0,
        "expected_tool_sequence": [
            {
                "tool_name": "vector_search",
                "args_match": {"query_contains_any": ["focal loss", "class imbalance"]},
            },
            {
                "tool_name": "cypher_query",
                "args_match": {"query_contains_all": ["focal_loss"]},
            },
        ],
    }
    m = score_agent_case(report, gold)
    assert m["tool_call_correctness"] == 1.0
    assert m["passed"] is True


def test_score_agent_case_prefix_mode() -> None:
    report = {
        "answer": "ok",
        "citations": [],
        "tool_trace": [
            {"tool": "idea_search", "args_summary": {}},
            {"tool": "final_answer", "args_summary": {}},
        ],
    }
    gold = {
        "tool_sequence_match_mode": "prefix",
        "max_calls": 8,
        "min_tool_call_correctness": 1.0,
        "expected_tool_sequence": [{"tool": "idea_search"}, {"tool": "final_answer"}],
    }
    m = score_agent_case(report, gold)
    assert m["tool_call_correctness"] == 1.0
    assert m["passed"] is True
