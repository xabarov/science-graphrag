"""Smoke contracts for scripts/live_check/agent_trace_review.py."""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path
from typing import Any


_REPO = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO / "scripts" / "live_check" / "agent_trace_review.py"


def _load_module() -> Any:
    spec = importlib.util.spec_from_file_location("agent_trace_review_test_mod", _SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_agent_trace_review_quick_profile_writes_contract_files(
    tmp_path: Path, monkeypatch
) -> None:
    mod = _load_module()

    monkeypatch.setattr(mod, "_ensure_local_imports", lambda: None)
    monkeypatch.setattr(mod, "_load_dotenv", lambda *_a, **_k: None)
    monkeypatch.setattr(
        mod,
        "_run_http_suite",
        lambda **_k: [
            {"name": "health", "ok": True, "detail": "ok"},
            {"name": "agent_v2_sync_json", "ok": True, "detail": "ok"},
            {"name": "agent_v2_sse", "ok": True, "detail": "ok"},
        ],
    )
    monkeypatch.setattr(mod, "_run_optional_e2e", lambda *_a, **_k: None)
    monkeypatch.setattr(
        mod,
        "_runtime_attribution_from_env",
        lambda: ("single_agent_research", "single_agent_react"),
    )

    class _StubTraceReview:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

    schema_mod = types.ModuleType("trace_review_schema")
    schema_mod.REVIEW_VERSION = "trace-review-v1"
    schema_mod.TraceReviewV1 = _StubTraceReview
    schema_mod.aggregate_metrics_from_timeline = lambda _tl: {
        "tool_error_rate": 0.0,
        "missing_span_count": 0,
        "compaction_event_count": 0,
        "final_answer_missing_count": 0,
        "latency_p95_ms": None,
        "compaction_churn_score": None,
    }
    schema_mod.check_from_dict = lambda x: x
    schema_mod.merge_e2e_report_json_into_review = lambda **_k: []
    schema_mod.trace_review_to_dict = lambda review: {
        "review_version": "trace-review-v1",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "checks": list(review.kwargs["checks"]),
        "trace_timeline": [],
        "metrics": review.kwargs["metrics"],
        "verdict": {"status": "pass", "fail_reasons": [], "warn_reasons": []},
    }
    schema_mod.verdict_from_signals = lambda **_k: {
        "status": "pass",
        "fail_reasons": [],
        "warn_reasons": [],
    }
    monkeypatch.setitem(sys.modules, "trace_review_schema", schema_mod)

    out_json = tmp_path / "trace-review.json"
    out_md = tmp_path / "trace-review.md"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "agent_trace_review.py",
            "--profile",
            "quick",
            "--out-json",
            str(out_json),
            "--out-md",
            str(out_md),
        ],
    )

    rc = mod.main()
    assert rc == 0
    assert out_json.exists()
    assert out_md.exists()
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["review_version"] == "trace-review-v1"
    run_ctx = payload.get("run_context") or {}
    assert run_ctx.get("profile") == "quick"
    assert run_ctx.get("run_kind") == "single_agent_research"
    assert run_ctx.get("graph_id") == "single_agent_react"

