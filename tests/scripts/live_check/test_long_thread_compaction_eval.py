"""CI coverage for ``scripts/live_check/long_thread_compaction_eval.py`` (Wave H §H1)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from science_graphrag.agent.context.session_backend import (
    InMemorySessionMemoryBackend,
    get_session_memory_backend,
    set_session_memory_backend,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_HARNESS_PATH = _REPO_ROOT / "scripts" / "live_check" / "long_thread_compaction_eval.py"


@pytest.fixture(scope="module")
def harness_module():
    spec = importlib.util.spec_from_file_location("wave_h_long_thread_eval", _HARNESS_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load harness at {_HARNESS_PATH}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["wave_h_long_thread_eval"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_long_thread_candidate_profile_meets_cache_gate(tmp_path: Path, harness_module) -> None:
    """Candidate profile (Wave H §H2) should produce ratio ≥ 0.4 over 50 turns."""
    out_json = tmp_path / "candidate.json"
    out_md = tmp_path / "candidate.md"
    rc = harness_module.main(
        [
            "--profile",
            "candidate",
            "--turns",
            "50",
            "--digest-cap",
            "10",
            "--min-side-llm-cache-read-ratio",
            "0.4",
            "--out-json",
            str(out_json),
            "--out-md",
            str(out_md),
        ]
    )
    assert rc == 0
    data = json.loads(out_json.read_text(encoding="utf-8"))
    metrics = data["metrics"]
    assert metrics["compaction_event_count"] >= 1
    assert metrics["side_llm_cache_read_ratio_avg"] is not None
    assert metrics["side_llm_cache_read_ratio_avg"] >= 0.4
    assert metrics["post_compact_paper_sources_restored_cases"] >= 1
    assert data["verdict"]["status"] == "pass"
    md = out_md.read_text(encoding="utf-8")
    assert "Wave H Long-thread Compaction Eval" in md


def test_long_thread_baseline_profile_warns_below_gate(tmp_path: Path, harness_module) -> None:
    """Baseline profile mirrors pre-Wave-H L4: cache ratio is 0.0 → warn (exit 3)."""
    out_json = tmp_path / "baseline.json"
    out_md = tmp_path / "baseline.md"
    rc = harness_module.main(
        [
            "--profile",
            "baseline",
            "--turns",
            "50",
            "--digest-cap",
            "10",
            "--min-side-llm-cache-read-ratio",
            "0.4",
            "--out-json",
            str(out_json),
            "--out-md",
            str(out_md),
        ]
    )
    assert rc == 3
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["verdict"]["status"] == "warn"
    assert any("side_llm_cache_read_ratio_avg" in r for r in data["verdict"]["warn_reasons"])
    # Paper restore must still work even on the baseline profile — that is the H1
    # invariant that does not depend on the cache-safe helper.
    metrics = data["metrics"]
    assert metrics["post_compact_paper_sources_restored_cases"] >= 1


def test_long_thread_paper_invariant_per_compaction(tmp_path: Path, harness_module) -> None:
    """Each compaction in the candidate run must persist + restore at least one paper item."""
    out_json = tmp_path / "candidate_invariant.json"
    out_md = tmp_path / "candidate_invariant.md"
    harness_module.main(
        [
            "--profile",
            "candidate",
            "--turns",
            "30",
            "--digest-cap",
            "5",
            "--out-json",
            str(out_json),
            "--out-md",
            str(out_md),
        ]
    )
    data = json.loads(out_json.read_text(encoding="utf-8"))
    compact_turns = [t for t in data["turns"] if t["compact_triggered"]]
    assert compact_turns, "expected at least one compaction event over 30 turns"
    for turn in compact_turns:
        assert turn["paper_sources_saved"] >= 1, turn
        assert turn["paper_sources_restored"] >= 1, turn


def test_long_thread_eval_restores_global_session_backend(tmp_path: Path, harness_module) -> None:
    """Harness must not permanently replace process-wide session backend."""
    original = get_session_memory_backend()
    sentinel = InMemorySessionMemoryBackend()
    set_session_memory_backend(sentinel)
    try:
        out_json = tmp_path / "backend_guard.json"
        out_md = tmp_path / "backend_guard.md"
        rc = harness_module.main(
            [
                "--profile",
                "candidate",
                "--turns",
                "10",
                "--digest-cap",
                "5",
                "--out-json",
                str(out_json),
                "--out-md",
                str(out_md),
            ]
        )
        assert rc in (0, 3)
        # Main contract: backend object is restored exactly to what caller had.
        assert get_session_memory_backend() is sentinel
    finally:
        set_session_memory_backend(original)
