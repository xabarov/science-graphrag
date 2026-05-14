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

import pytest

_REPO = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO / "scripts" / "live_check" / "agent_trace_review.py"


def _run_script_subprocess(
    *, tmp_path: Path, profile: str
) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
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

    hb_mod = types.ModuleType("agent_trace_review_heartbeat")

    class _StubStageHeartbeat:
        def __init__(self, _name: str, *, interval_s: float) -> None:
            self.interval_s = interval_s

        def start(self) -> None:
            return None

        def stop(self) -> None:
            return None

    def _record_stage(
        stages: list[dict[str, Any]],
        *,
        stage: str,
        elapsed_ms: float,
        ok: bool,
        detail: str | None = None,
    ) -> None:
        row: dict[str, Any] = {
            "stage": stage,
            "elapsed_ms": round(float(elapsed_ms), 3),
            "ok": bool(ok),
        }
        if detail:
            row["detail"] = detail[:2000]
        stages.append(row)

    hb_mod.StageHeartbeat = _StubStageHeartbeat
    hb_mod.record_stage = _record_stage
    monkeypatch.setitem(sys.modules, "agent_trace_review_heartbeat", hb_mod)

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

    dotenv_mod = types.ModuleType("dotenv_util")
    dotenv_mod.resolve_live_base_url = lambda url: str(url)  # type: ignore[misc]
    dotenv_mod.load_dotenv_or_warn = lambda *_a, **_k: None  # type: ignore[misc]
    monkeypatch.setitem(sys.modules, "dotenv_util", dotenv_mod)

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


def test_agent_trace_review_accepts_dev_base_alias(tmp_path: Path) -> None:
    """Alias ``AGENT_LIVE_BASE=dev`` is normalized before network calls."""
    out_json = tmp_path / "trace-review-dev-alias.json"
    out_md = tmp_path / "trace-review-dev-alias.md"
    env = {k: v for k, v in os.environ.items()}
    env["AGENT_LIVE_DEV_URL"] = "http://127.0.0.1:65535"
    completed = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--profile",
            "quick",
            "--base-url",
            "dev",
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
        env=env,
    )
    assert completed.returncode == 1
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    run_ctx = payload.get("run_context") or {}
    assert run_ctx.get("base_url") == "http://127.0.0.1:65535"


def test_run_compaction_turn_review_surfaces_failure_reason(tmp_path: Path, monkeypatch) -> None:
    mod = _load_module()
    out_json = tmp_path / "compaction.json"
    out_json.write_text(
        json.dumps(
            {
                "review_version": "trace-review-v1",
                "failed_turn": 3,
                "failure_kind": "http_timeout",
                "verdict": {"status": "fail", "reasons": ["http_timeout_turn_3"]},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    class _Completed:
        returncode = 1
        stdout = "x"
        stderr = "y"

    def _fake_run(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return _Completed()

    monkeypatch.setattr(mod.subprocess, "run", _fake_run)
    out = mod._run_compaction_turn_review(
        base_url="http://127.0.0.1:65535",
        workspace_id="ws1",
        timeout=0.5,
        turns=3,
        require_after=2,
        out_json=out_json,
        emit_merged_into=None,
    )
    assert out.get("ok") is False
    assert out.get("failure_reason") == "http_timeout_turn_3"
    assert out.get("failed_turn") == 3
    assert out.get("failure_kind") == "http_timeout"


def test_run_compaction_turn_review_timeout_sets_failure_reason(
    tmp_path: Path, monkeypatch
) -> None:
    mod = _load_module()
    out_json = tmp_path / "compaction-timeout.json"

    def _fake_timeout(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        err = subprocess.TimeoutExpired(
            cmd=["python", "compaction_turn_review.py"],
            timeout=3.0,
            output="partial",
            stderr="timeout",
        )
        raise err

    monkeypatch.setattr(mod.subprocess, "run", _fake_timeout)
    out = mod._run_compaction_turn_review(
        base_url="http://127.0.0.1:65535",
        workspace_id="ws1",
        timeout=0.5,
        turns=3,
        require_after=2,
        out_json=out_json,
        emit_merged_into=None,
    )
    assert out.get("ok") is False
    assert out.get("timeout_expired") is True
    assert out.get("failure_reason") == "compaction_turn_review_timeout"


def test_run_compaction_turn_review_forwards_mode_and_retries(tmp_path: Path, monkeypatch) -> None:
    """CLI passes mode/retries; subprocess timeout uses wall budget (floor 120s for tiny per-turn timeouts)."""
    mod = _load_module()
    out_json = tmp_path / "compaction-mode.json"
    captured: dict[str, Any] = {}

    class _Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    def _fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
        captured["cmd"] = list(cmd)
        captured["subprocess_timeout"] = kwargs.get("timeout")
        return _Completed()

    monkeypatch.setattr(mod.subprocess, "run", _fake_run)
    out = mod._run_compaction_turn_review(
        base_url="http://127.0.0.1:65535",
        workspace_id="ws1",
        timeout=0.5,
        turns=3,
        require_after=2,
        out_json=out_json,
        emit_merged_into=None,
        mode="focused_long_thread",
        max_retries_per_turn=2,
    )
    assert out.get("ok") is True
    cmd = captured.get("cmd") or []
    assert "--mode" in cmd
    assert "focused_long_thread" in cmd
    assert "--max-retries-per-turn" in cmd
    assert "2" in cmd
    # Wall budget: max(120, timeout * turns * (1 + retries) * 1.25); floor 120 for tiny httpx timeouts.
    assert captured.get("subprocess_timeout") == max(120.0, 0.5 * 3.0 * 3.0 * 1.25)


def test_run_compaction_turn_review_subprocess_timeout_scales_past_floor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When timeout*turns*attempts exceeds 120s floor, subprocess timeout matches scaled wall budget."""
    mod = _load_module()
    out_json = tmp_path / "compaction-wall.json"
    captured: dict[str, Any] = {}

    class _Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    def _fake_run(_cmd, **kwargs):  # type: ignore[no-untyped-def]
        captured["subprocess_timeout"] = kwargs.get("timeout")
        return _Completed()

    monkeypatch.setattr(mod.subprocess, "run", _fake_run)
    mod._run_compaction_turn_review(
        base_url="http://127.0.0.1:65535",
        workspace_id=None,
        timeout=100.0,
        turns=2,
        require_after=1,
        out_json=out_json,
        emit_merged_into=None,
        mode="focused_long_thread",
        max_retries_per_turn=1,
    )
    assert captured.get("subprocess_timeout") == max(120.0, 100.0 * 2.0 * 2.0 * 1.25)


def test_run_compaction_turn_review_prefers_top_level_failure_reason(
    tmp_path: Path, monkeypatch
) -> None:
    """Merge metadata prefers JSON ``failure_reason`` over first ``verdict.reasons`` entry."""
    mod = _load_module()
    out_json = tmp_path / "compaction-top-fr.json"
    out_json.write_text(
        json.dumps(
            {
                "review_version": "trace-review-v1",
                "failed_turn": 2,
                "failure_kind": "silent_hang",
                "failure_reason": "silent_hang_turn_2",
                "verdict": {"status": "fail", "reasons": ["missing_compaction_kinds_turn_4"]},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    class _Completed:
        returncode = 1
        stdout = ""
        stderr = ""

    monkeypatch.setattr(mod.subprocess, "run", lambda *_a, **_k: _Completed())
    out = mod._run_compaction_turn_review(
        base_url="http://127.0.0.1:65535",
        workspace_id=None,
        timeout=1.0,
        turns=4,
        require_after=2,
        out_json=out_json,
        emit_merged_into=None,
    )
    assert out.get("failure_reason") == "silent_hang_turn_2"


def test_json_safe_value_decodes_bytes_recursively() -> None:
    mod = _load_module()
    payload = {
        "stdout_tail": b"ok\xff",
        "nested": {"stderr_tail": b"fail\xfe"},
        "list_like": [b"a", (b"b",)],
    }
    out = mod._json_safe_value(payload)
    assert out["stdout_tail"] == "ok\ufffd"
    assert out["nested"]["stderr_tail"] == "fail\ufffd"
    assert out["list_like"] == ["a", ["b"]]
