"""Unit tests for focused long-thread diagnostics in compaction_turn_review."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO / "scripts" / "live_check" / "compaction_turn_review.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("compaction_turn_review_test_mod", _SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_classify_turn_failure_default_timeout() -> None:
    mod = _load_module()
    fk, fr = mod._classify_turn_failure(
        mode="default",
        failure_kind_raw="http_timeout",
        turn_idx=2,
        elapsed_ms=1500,
        silent_hang_threshold_s=180.0,
    )
    assert fk == "http_timeout"
    assert fr == "http_timeout_turn_2"


def test_classify_turn_failure_focused_silent_hang() -> None:
    mod = _load_module()
    fk, fr = mod._classify_turn_failure(
        mode="focused_long_thread",
        failure_kind_raw="http_read_timeout",
        turn_idx=3,
        elapsed_ms=210000,
        silent_hang_threshold_s=180.0,
    )
    assert fk == "silent_hang"
    assert fr == "silent_hang_turn_3"


def test_compaction_in_turn_heartbeat_sec_focused_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from trace_review.orchestrator_env import compaction_in_turn_heartbeat_sec

    monkeypatch.delenv("AGENT_LIVE_COMPACTION_FOCUS_HEARTBEAT_SEC", raising=False)
    monkeypatch.delenv("AGENT_LIVE_COMPACTION_REVIEW_HEARTBEAT_SEC", raising=False)
    assert compaction_in_turn_heartbeat_sec(mode="focused_long_thread") == 15.0
    monkeypatch.delenv("AGENT_LIVE_COMPACTION_REVIEW_HEARTBEAT_SEC", raising=False)
    assert compaction_in_turn_heartbeat_sec(mode="default") == 30.0
