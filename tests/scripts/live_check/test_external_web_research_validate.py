"""Contract tests for external web research validators (no live API)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from science_graphrag.agent.web_evidence_policy import detect_unsupported_negative_official_claim

_SCRIPT_DIR = Path(__file__).resolve().parents[3] / "scripts" / "live_check"
_spec = importlib.util.spec_from_file_location(
    "external_web_research_validate",
    _SCRIPT_DIR / "external_web_research_validate.py",
)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
_evaluate = _mod.evaluate_external_web_research_case
_phoenix_has = _mod.phoenix_has_official_lookup_span


def test_evaluate_case_passes_with_official_citation() -> None:
    data = {
        "answer": "YOLO11 documented by Ultralytics (web summary).",
        "tool_trace": [{"tool": "official_web_lookup"}, {"tool": "web_fetch"}],
        "citations": [{"url": "https://docs.ultralytics.com/models/yolo11/"}],
    }
    out = _evaluate(data)
    assert out["ok"] is True
    assert out["issues"] == []


def test_evaluate_case_fails_on_negative_claim() -> None:
    data = {
        "answer": "Официальных анонсов от Ultralytics не зафиксировано.",
        "tool_trace": [{"tool": "web_search"}],
        "citations": [{"url": "https://doi.org/10.1/x"}],
    }
    out = _evaluate(data)
    assert out["ok"] is False
    assert "unsupported_negative_official_claim" in out["issues"]


def test_negative_claim_detector_matches_regression_phrase() -> None:
    assert detect_unsupported_negative_official_claim(
        "Официальных анонсов от разработчиков YOLO не зафиксировано"
    )


def test_phoenix_has_official_lookup_span() -> None:
    assert _phoenix_has(["tool.web_fetch", "official_web_lookup", "agent.query"])
    assert _phoenix_has(["tool.official_web_lookup"])
    assert not _phoenix_has(["tool.web_search", "web_fetch"])
