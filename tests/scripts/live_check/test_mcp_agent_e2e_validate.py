"""Unit tests for MCP agent E2E validation helpers."""

from __future__ import annotations

from scripts.live_check.mcp_agent_e2e_validate import (
    agent_sync_failure_issues,
    validate_mcp_agent_response,
)


def test_validate_mcp_agent_response_green() -> None:
    data = {
        "tool_trace": [
            {
                "tool": "call_mcp_tool",
                "ok": True,
                "payload": {"ok": True, "server": "smoke", "tool": "ping"},
            },
        ],
        "run_metadata": {
            "mcp_audit_summary": {
                "event_count": 1,
                "deny_hits": 0,
                "ok_false_hits": 0,
                "last": {"phase": "call", "server": "smoke", "tool": "ping", "ok": True},
            },
        },
    }
    ok, issues = validate_mcp_agent_response(data)
    assert ok is True
    assert issues == []


def test_agent_sync_failure_issues_detects_provider_unreachable() -> None:
    data = {
        "tool_trace": [],
        "run_metadata": {
            "agent_sync_error": True,
            "error_class": "provider_unreachable",
            "error_detail": "Connection error.",
        },
    }
    issues = agent_sync_failure_issues(data)
    assert len(issues) == 1
    assert issues[0].startswith("agent_sync_error:provider_unreachable")


def test_validate_mcp_agent_response_fails_on_agent_sync_error() -> None:
    data = {
        "tool_trace": [],
        "run_metadata": {"agent_sync_error": True, "error_class": "provider_unreachable"},
    }
    ok, issues = validate_mcp_agent_response(data)
    assert ok is False
    assert any(i.startswith("agent_sync_error:") for i in issues)


def test_validate_mcp_agent_response_missing_mcp_tool() -> None:
    data = {
        "tool_trace": [{"tool": "web_search"}],
        "run_metadata": {},
    }
    ok, issues = validate_mcp_agent_response(data)
    assert ok is False
    assert any("call_mcp_tool" in i for i in issues)
