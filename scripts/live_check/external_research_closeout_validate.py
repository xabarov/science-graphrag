"""Validation/report helpers for external-research closeout lane."""

from __future__ import annotations

from typing import Any


def tool_names_from_trace(trace: list[dict[str, Any]] | None) -> list[str]:
    """Extract normalized tool names from sync JSON tool_trace."""
    out: list[str] = []
    for row in trace or []:
        if not isinstance(row, dict):
            continue
        name = str(row.get("tool") or row.get("name") or "").strip()
        if name:
            out.append(name)
    return out


def find_missing_tools(*, tools_seen: list[str], expected_tools: tuple[str, ...]) -> list[str]:
    """Return expected tools that were not seen in the lane."""
    seen = {name.strip() for name in tools_seen if str(name).strip()}
    return [name for name in expected_tools if name not in seen]


def lane_issue_list(
    *,
    http_ok: bool,
    response_data: dict[str, Any] | None,
    expected_tools: tuple[str, ...],
    phoenix_fetch_ok: bool | None,
    diagnostics_ok: bool | None,
) -> list[str]:
    """Build normalized issue list for one source/tool lane."""
    issues: list[str] = []
    if not http_ok:
        issues.append("http_not_ok")
    payload = response_data if isinstance(response_data, dict) else {}
    tools_seen = tool_names_from_trace(
        payload.get("tool_trace") if isinstance(payload.get("tool_trace"), list) else []
    )
    missing = find_missing_tools(tools_seen=tools_seen, expected_tools=expected_tools)
    if missing:
        issues.append("missing_expected_tools:" + ",".join(missing))
    if phoenix_fetch_ok is False:
        issues.append("phoenix_fetch_failed")
    if diagnostics_ok is False:
        issues.append("diagnostics_mismatch")
    return issues


def gate_status(issues: list[str]) -> str:
    """Map issue list into normalized gate status."""
    return "pass" if not issues else "fail"


def markdown_for_lane_report(
    *,
    lane_id: str,
    expected_tools: tuple[str, ...],
    tools_seen: list[str],
    phoenix_trace_id: str,
    phoenix_fetch_ok: bool | None,
    diagnostics_ok: bool | None,
    issues: list[str],
) -> str:
    """Render compact markdown report for one lane."""
    status = gate_status(issues)
    return "\n".join(
        [
            f"# {lane_id} lane report",
            "",
            f"- gate_status: `{status}`",
            f"- expected_tools: `{', '.join(expected_tools)}`",
            f"- tools_seen: `{', '.join(tools_seen) if tools_seen else 'none'}`",
            f"- phoenix_trace_id: `{phoenix_trace_id or 'n/a'}`",
            f"- phoenix_fetch_ok: `{phoenix_fetch_ok}`",
            f"- diagnostics_ok: `{diagnostics_ok}`",
            f"- issues: `{', '.join(issues) if issues else 'none'}`",
            "",
        ]
    )
