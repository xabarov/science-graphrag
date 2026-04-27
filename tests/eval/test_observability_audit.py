from __future__ import annotations

from eval.chat_agent.observability_audit import build_observability_trace_audit


def test_observability_no_phoenix_defaults_pass() -> None:
    obs = build_observability_trace_audit(
        tool_trace=[{"tool": "workspace_overview"}, {"tool": "final_answer"}],
        phoenix_http_snapshot=None,
    )
    assert obs["observability_passed"] is True
    assert obs["tool_trace_vs_phoenix_match"] is None
    assert "tool.workspace_overview" in obs["expected_span_names"]


def test_observability_phoenix_missing_tool_span() -> None:
    snap = {
        "ok": True,
        "payload_valid": True,
        "payload": {"spans": [{"name": "tool.final_answer"}]},
    }
    obs = build_observability_trace_audit(
        tool_trace=[{"tool": "idea_search"}, {"tool": "final_answer"}],
        phoenix_http_snapshot=snap,
    )
    assert obs["observability_passed"] is False
    assert obs["observability_match_reliable"] is True
    assert "tool.idea_search" in obs["missing_tool_spans"]


def test_observability_invalid_payload_not_a_gate() -> None:
    snap = {
        "ok": True,
        "payload_valid": False,
        "payload_kind": "html_shell",
        "payload": {"raw": "<!DOCTYPE html><html>"},
    }
    obs = build_observability_trace_audit(
        tool_trace=[{"tool": "idea_search"}, {"tool": "final_answer"}],
        phoenix_http_snapshot=snap,
    )
    assert obs["observability_passed"] is True
    assert obs["observability_match_reliable"] is False
    assert obs["phoenix_fetch_ok"] is True
