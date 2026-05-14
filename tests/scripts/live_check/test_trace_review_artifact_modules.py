"""Unit tests for trace-review artifact writers and compaction review splits."""

from __future__ import annotations

import importlib
import io
import json
import sys
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[3]
_LIVE_CHECK = _REPO / "scripts" / "live_check"


def _ensure_live_check_path() -> None:
    lc = str(_LIVE_CHECK)
    if lc not in sys.path:
        sys.path.insert(0, lc)


def test_merge_compaction_into_review_file_patches_merge_target(tmp_path: Path) -> None:
    """Compaction meta is merged into the on-disk review JSON with diagnostics patch."""
    _ensure_live_check_path()
    writers = importlib.import_module("trace_review.artifact_writers")
    merge_target = tmp_path / "review.json"
    merge_target.write_text(
        json.dumps(
            {
                "review_version": "trace-review-v1",
                "verdict": {"status": "pass"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    out_md = tmp_path / "review.md"
    primary = tmp_path / "primary.json"
    fallback: dict[str, Any] = {
        "review_version": "trace-review-v1",
        "verdict": {"status": "pass"},
    }
    compaction_meta = {"ok": True, "turns": 2}

    writers.merge_compaction_into_review_file(
        merge_target,
        compaction_meta,
        primary_out_json=primary,
        out_md=out_md,
        fallback_review_dict=fallback,
        exec_stages=[{"stage": "compaction_turn_review", "ok": True, "elapsed_ms": 1.0}],
        hb_sec=30.0,
        e2e_subprocess_timeout_sec=120.0,
        with_acceptance_summary=False,
        build_acceptance_summary=lambda _r: {},
    )
    merged = json.loads(merge_target.read_text(encoding="utf-8"))
    assert merged.get("compaction_turn_review") == compaction_meta
    assert out_md.exists()


def test_merge_compaction_into_review_file_fallback_writes_primary(
    tmp_path: Path,
) -> None:
    """Corrupt merge-target JSON falls back to primary_out_json + in-memory dict."""
    _ensure_live_check_path()
    writers = importlib.import_module("trace_review.artifact_writers")
    merge_target = tmp_path / "bad.json"
    merge_target.write_text("{ not json", encoding="utf-8")
    out_md = tmp_path / "review.md"
    primary = tmp_path / "primary.json"
    primary.write_text('{"verdict":{"status":"pass"}}\n', encoding="utf-8")
    fallback = json.loads(primary.read_text(encoding="utf-8"))
    compaction_meta = {"ok": False}

    writers.merge_compaction_into_review_file(
        merge_target,
        compaction_meta,
        primary_out_json=primary,
        out_md=out_md,
        fallback_review_dict=fallback,
        exec_stages=[],
        hb_sec=30.0,
        e2e_subprocess_timeout_sec=120.0,
        with_acceptance_summary=False,
        build_acceptance_summary=lambda _r: {},
    )
    repaired = json.loads(primary.read_text(encoding="utf-8"))
    assert repaired.get("compaction_turn_review") == compaction_meta
    assert out_md.exists()


def test_build_compaction_verdict_flags_missing_kinds() -> None:
    """Verdict fails when compaction kinds are absent after the required turn."""
    _ensure_live_check_path()
    mod = importlib.import_module("compaction_review.result_aggregator")
    reports: list[dict[str, Any]] = [{"turn": 3, "compaction": {}}]
    verdict = mod.build_compaction_verdict(
        failure_reason=None,
        turn_reports=reports,
        require_compaction_after=2,
    )
    assert verdict["status"] == "fail"
    assert any("missing_compaction_kinds_turn_3" in r for r in (verdict.get("reasons") or []))


def test_build_compaction_events_thread_id() -> None:
    """Compaction events carry thread_id for trace merge."""
    _ensure_live_check_path()
    mod = importlib.import_module("compaction_review.report_schema")
    events = mod.build_compaction_events(
        [{"turn": 1, "compaction": {"kinds": ["ctx"]}}],
        thread_id="tid-abc",
    )
    assert len(events) == 1
    assert events[0]["thread_id"] == "tid-abc"
    assert events[0]["type"] == "context_compacted"


def test_compaction_heartbeat_stderr_turn_start_shape() -> None:
    """Turn start stderr line remains grep-friendly for operators."""
    _ensure_live_check_path()
    mod = importlib.import_module("compaction_review.heartbeat_monitor")

    buf = io.StringIO()
    with redirect_stderr(buf):
        mod.log_turn_start(
            turn_idx=2,
            attempt=1,
            thread_id="t-x",
            hb_sec=15.0,
            mode="focused_long_thread",
        )
    line = buf.getvalue().strip()
    assert line.startswith("[compaction-review] turn_start")
    assert "turn=2" in line
    assert "hb_sec=15.0" in line
