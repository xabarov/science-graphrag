"""Smoke contracts for scripts/live_check/agent_trace_review.py."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import types
from pathlib import Path
from typing import Any


_REPO = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO / "scripts" / "live_check" / "agent_trace_review.py"


def _run_script_subprocess(*, tmp_path: Path, profile: str) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    out_json = tmp_path / f"trace-review-subprocess-{profile}.json"
    out_md = tmp_path / f"trace-review-subprocess-{profile}.md"
    completed = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--profile",
            profile,
            "--base-url",
            "http://127.0.0.1:65535",
            "--timeout",
            "0.5",
            "--skip-e2e",
            "--out-json",
            str(out_json),
            "--out-md",
            str(out_md),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    return completed, payload


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
    schema_mod.e2e_failures_are_retryable_provider_flakes = lambda _report: False
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
    schema_mod.build_acceptance_summary = lambda _review: {}
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
    diag = run_ctx.get("execution_diagnostics") or {}
    assert diag.get("heartbeat_interval_sec") == 60.0
    stages = diag.get("stages") or []
    assert any(s.get("stage") == "http_suite" for s in stages)
    assert run_ctx.get("run_kind") == "single_agent_research"
    assert run_ctx.get("graph_id") == "single_agent_react"


def test_agent_trace_review_subprocess_quick_profile_fail_path_contract(
    tmp_path: Path,
) -> None:
    completed, payload = _run_script_subprocess(tmp_path=tmp_path, profile="quick")
    assert completed.returncode == 1
    assert payload["review_version"] == "trace-review-v1"
    run_ctx = payload.get("run_context") or {}
    assert run_ctx.get("profile") == "quick"
    assert isinstance(run_ctx.get("execution_diagnostics"), dict)
    verdict = payload.get("verdict") or {}
    assert verdict.get("status") == "fail"
    assert verdict.get("fail_reasons")


def test_agent_trace_review_acceptance_requires_workspace_id(tmp_path: Path) -> None:
    """Acceptance suite must fail fast when fanout probe cannot run (no workspace_id)."""
    out_json = tmp_path / "trace-review-no-ws.json"
    out_md = tmp_path / "trace-review-no-ws.md"
    env = {k: v for k, v in os.environ.items()}
    env.pop("AGENT_LIVE_WORKSPACE_ID", None)
    completed = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--suite",
            "acceptance",
            "--profile",
            "quick",
            "--skip-e2e",
            "--base-url",
            "http://127.0.0.1:65535",
            "--timeout",
            "0.5",
            "--out-json",
            str(out_json),
            "--out-md",
            str(out_md),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert completed.returncode == 2
    err = (completed.stderr or "").lower()
    assert "workspace" in err and ("--workspace-id" in err or "agent_live_workspace_id" in err)


def test_agent_trace_review_subprocess_default_profile_fail_path_contract(
    tmp_path: Path,
) -> None:
    completed, payload = _run_script_subprocess(tmp_path=tmp_path, profile="default")
    assert completed.returncode == 1
    assert payload["review_version"] == "trace-review-v1"
    run_ctx = payload.get("run_context") or {}
    assert run_ctx.get("profile") == "default"
    verdict = payload.get("verdict") or {}
    assert verdict.get("status") == "fail"
    assert verdict.get("fail_reasons")


def test_server_agent_runtime_from_checks_reads_sync_json_run_metadata() -> None:
    mod = _load_module()
    checks: list[dict[str, Any]] = [
        {
            "name": "agent_v2_sync_json",
            "ok": True,
            "data": {"run_metadata": {"agent_runtime": "langgraph_supervisor_v3"}},
        },
    ]
    assert mod._server_agent_runtime_from_checks(checks) == "langgraph_supervisor_v3"

