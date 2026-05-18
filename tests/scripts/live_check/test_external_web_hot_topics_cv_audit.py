"""Contract tests for external_web_hot_topics_cv_audit evaluator semantics."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parents[3] / "scripts" / "live_check"
_SPEC = importlib.util.spec_from_file_location(
    "external_web_hot_topics_cv_audit",
    _SCRIPT_DIR / "external_web_hot_topics_cv_audit.py",
)
_MOD = importlib.util.module_from_spec(_SPEC)
assert _SPEC is not None
assert _SPEC.loader is not None
_SPEC.loader.exec_module(_MOD)

_evaluate_verdicts = _MOD.evaluate_case_verdicts
_extract_terminal_reason = _MOD.extract_terminal_reason_from_run_metadata
_build_audit_diagnostics = _MOD.build_audit_diagnostics
_evaluate_next_slice_gates = _MOD.evaluate_next_slice_gates


def test_has_final_answer_span_uses_tool_final_answer_name() -> None:
    from eval.chat_agent.phoenix_export import has_final_answer_tool_span

    assert has_final_answer_tool_span(["tool.final_answer", "chat"])


def test_verdicts_tool_trace_final_answer_but_missing_phoenix_span() -> None:
    verdicts = _evaluate_verdicts(
        http_status=200,
        error=None,
        answer="Готовый ответ с цитатами.",
        citations=[
            {"url": "https://example.org/a"},
            {"url": "https://example.org/b"},
            {"url": "https://example.org/c"},
        ],
        tool_flags={
            "web_search": True,
            "web_fetch": True,
            "final_answer": True,
            "read_external_pdf": False,
            "semantic_scholar": False,
            "openalex": False,
            "arxiv": False,
            "unpaywall": False,
        },
        span_names=["chat", "tool.web_fetch", "route_react_tools_next"],
    )
    assert verdicts["runtime"]["ok"] is True
    assert verdicts["tool_trace"]["ok"] is True
    assert verdicts["phoenix"]["ok"] is False
    assert "missing_span_but_tool_trace_present" in verdicts["phoenix"]["issues"]


def test_extract_terminal_reason_prefers_top_level_field() -> None:
    tr = _extract_terminal_reason(
        {
            "terminal_reason": "partial_final_answer",
            "final_answer_validation": {"terminal_reason": "final_answer_ok"},
        }
    )
    assert tr == "partial_final_answer"


def test_build_audit_diagnostics_phoenix_mismatch() -> None:
    diag = _build_audit_diagnostics(
        tool_flags={"final_answer": True},
        span_names=["chat", "tool.web_fetch"],
    )
    assert diag.get("phoenix_missing_final_answer_span") == "missing_span_but_tool_trace_present"


def test_evaluate_next_slice_gates_passes_minimum_targets() -> None:
    gates = _evaluate_next_slice_gates(
        {
            "runtime_ok_cases": 6,
            "tool_trace_ok_cases": 6,
            "phoenix_ok_cases": 5,
            "with_final_answer": 8,
            "generic_fallback_with_evidence_cases": 0,
        }
    )
    assert gates["all_ok"] is True


def test_evaluate_next_slice_gates_fails_when_runtime_low() -> None:
    gates = _evaluate_next_slice_gates({"runtime_ok_cases": 4})
    assert gates["all_ok"] is False
    assert gates["checks"]["runtime_ok_cases"]["ok"] is False


def test_print_compare_delta_reports_diff(capsys) -> None:
    baseline = {
        "lane_label": "baseline",
        "coverage": {"runtime_ok_cases": 4, "with_final_answer": 3},
        "next_slice_gates": {"all_ok": False},
    }
    current = {
        "lane_label": "experiment",
        "coverage": {"runtime_ok_cases": 6, "with_final_answer": 8},
        "next_slice_gates": {"all_ok": True},
    }
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
        import json

        json.dump(baseline, fh)
        path = Path(fh.name)
    _MOD._print_compare_delta(path, current)
    out = capsys.readouterr().out
    assert "runtime_ok_cases" in out
    path.unlink(missing_ok=True)


def test_audit_diagnostics_keys_align_with_runtime_constants() -> None:
    from science_graphrag.agent.terminal_reason import (
        AUDIT_PHOENIX_MISSING_FINAL_ANSWER_SPAN,
        AUDIT_TOOL_TRACE_MISSING_FINAL_ANSWER,
    )

    diag = _build_audit_diagnostics(
        tool_flags={"final_answer": False},
        span_names=[],
    )
    assert AUDIT_TOOL_TRACE_MISSING_FINAL_ANSWER in diag
    assert AUDIT_PHOENIX_MISSING_FINAL_ANSWER_SPAN in diag


def test_verdicts_runtime_fallback_detected_even_with_http_200() -> None:
    verdicts = _evaluate_verdicts(
        http_status=200,
        error=None,
        answer="I could not produce a complete final answer for this turn. Please rephrase the request.",
        citations=[],
        tool_flags={
            "web_search": False,
            "web_fetch": False,
            "final_answer": False,
            "read_external_pdf": False,
            "semantic_scholar": False,
            "openalex": False,
            "arxiv": False,
            "unpaywall": False,
        },
        span_names=[],
    )
    assert verdicts["runtime"]["ok"] is False
    assert "fallback_answer" in verdicts["runtime"]["issues"]
    assert "few_citations" in verdicts["runtime"]["issues"]
    assert verdicts["tool_trace"]["ok"] is False
