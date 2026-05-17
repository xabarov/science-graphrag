"""Contract tests for external research closeout validators."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parents[3] / "scripts" / "live_check"
_spec = importlib.util.spec_from_file_location(
    "external_research_closeout_validate",
    _SCRIPT_DIR / "external_research_closeout_validate.py",
)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)

_tool_names = _mod.tool_names_from_trace
_find_missing = _mod.find_missing_tools
_lane_issues = _mod.lane_issue_list
_gate_status = _mod.gate_status
_lane_md = _mod.markdown_for_lane_report


def test_tool_names_from_trace_extracts_tool_key() -> None:
    trace = [{"tool": "web_search"}, {"name": "web_fetch"}, {"detail": {}}]
    assert _tool_names(trace) == ["web_search", "web_fetch"]


def test_find_missing_tools_reports_absent_expected() -> None:
    missing = _find_missing(tools_seen=["web_search"], expected_tools=("web_search", "web_fetch"))
    assert missing == ["web_fetch"]


def test_lane_issue_list_reports_http_and_tool_gap() -> None:
    issues = _lane_issues(
        http_ok=False,
        response_data={"tool_trace": [{"tool": "web_search"}]},
        expected_tools=("web_search", "web_fetch"),
        phoenix_fetch_ok=False,
        diagnostics_ok=False,
    )
    assert "http_not_ok" in issues
    assert "missing_expected_tools:web_fetch" in issues
    assert "phoenix_fetch_failed" in issues
    assert "diagnostics_mismatch" in issues


def test_gate_status_pass_when_no_issues() -> None:
    assert _gate_status([]) == "pass"
    assert _gate_status(["x"]) == "fail"


def test_markdown_for_lane_report_has_required_rows() -> None:
    text = _lane_md(
        lane_id="openalex",
        expected_tools=("openalex_works_search",),
        tools_seen=["openalex_works_search"],
        phoenix_trace_id="trace-1",
        phoenix_fetch_ok=True,
        diagnostics_ok=True,
        issues=[],
    )
    assert "# openalex lane report" in text
    assert "gate_status: `pass`" in text
    assert "openalex_works_search" in text
