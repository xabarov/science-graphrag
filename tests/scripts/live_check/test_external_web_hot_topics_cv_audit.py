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
