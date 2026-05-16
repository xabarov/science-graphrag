"""Validation helpers for MCP agent live E2E (unit-tested, no HTTP)."""

from __future__ import annotations

from typing import Any

MCP_E2E_DEFAULT_QUESTION = (
    "MCP acceptance test. You must call the call_mcp_tool tool exactly once with "
    'server="smoke", tool="ping", and arguments {}. Do not use any other tools. '
    "After the tool returns successfully, reply with exactly: MCP_E2E_OK"
)


def agent_sync_failure_issues(data: dict[str, Any]) -> list[str]:
    """Detect agent runs that failed before tool execution (e.g. LLM unreachable)."""
    rm = data.get("run_metadata")
    if not isinstance(rm, dict):
        return []
    if rm.get("agent_sync_error") is True:
        error_class = str(rm.get("error_class") or "unknown").strip() or "unknown"
        detail = str(rm.get("error_detail") or "").strip()
        if detail:
            return [f"agent_sync_error:{error_class}:{detail[:120]}"]
        return [f"agent_sync_error:{error_class}"]
    return []


def tool_names_from_trace(tool_trace: list[Any] | None) -> list[str]:
    names: list[str] = []
    for row in tool_trace or []:
        if not isinstance(row, dict):
            continue
        name = str(row.get("tool") or row.get("name") or "").strip()
        if name:
            names.append(name)
    return names


def validate_mcp_agent_response(
    data: dict[str, Any],
    *,
    expected_server: str = "smoke",
    expected_tool: str = "ping",
) -> tuple[bool, list[str]]:
    """Return (ok, issue_messages) for a sync ``/v2/agent/query`` body."""
    issues: list[str] = list(agent_sync_failure_issues(data))

    trace = data.get("tool_trace")
    if not isinstance(trace, list):
        issues.append("missing_tool_trace")
        trace = []

    tool_names = tool_names_from_trace(trace)
    if "call_mcp_tool" not in tool_names:
        issues.append("missing_call_mcp_tool_in_tool_trace")

    rm = data.get("run_metadata")
    if not isinstance(rm, dict):
        issues.append("missing_run_metadata")
        rm = {}

    mc = rm.get("mcp_audit_summary")
    if not isinstance(mc, dict):
        issues.append("missing_mcp_audit_summary")
    else:
        if int(mc.get("event_count") or 0) < 1:
            issues.append("mcp_audit_summary.event_count<1")
        last = mc.get("last")
        if not isinstance(last, dict):
            issues.append("mcp_audit_summary.last_missing")
        else:
            if str(last.get("phase") or "") != "call":
                issues.append(f"mcp_audit_last.phase={last.get('phase')!r}")
            if last.get("ok") is not True:
                issues.append("mcp_audit_last.ok_not_true")
            if str(last.get("server") or "") != expected_server:
                issues.append(f"mcp_audit_last.server={last.get('server')!r}")
            if expected_tool and str(last.get("tool") or "") != expected_tool:
                issues.append(f"mcp_audit_last.tool={last.get('tool')!r}")

    for row in trace:
        if not isinstance(row, dict):
            continue
        if str(row.get("tool") or "") != "call_mcp_tool":
            continue
        detail = row.get("detail") if isinstance(row.get("detail"), dict) else {}
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        merged = {**payload, **detail}
        if merged.get("ok") is False or str(merged.get("error") or "").strip():
            issues.append(f"call_mcp_tool_error={merged.get('error')!r}")
        break

    return (not issues, issues)
