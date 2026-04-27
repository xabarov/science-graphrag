"""Phase 0: benchmark logical id registry resolves to canonical repo paths."""

from __future__ import annotations

from pathlib import Path

from science_graphrag.artifacts import benchmark_paths as bp
from science_graphrag.artifacts.benchmark_registry import (
    BENCHMARK_REGISTRY,
    resolve_benchmark_artifact_path,
)


def test_metrics_summary_path_matches_eval_results_layout() -> None:
    expected = bp.REPO_ROOT / "eval" / "results" / "benchmark-metrics-summary.json"
    assert bp.benchmark_metrics_summary_path() == expected


def test_registry_covers_all_logical_ids() -> None:
    assert set(BENCHMARK_REGISTRY) == set(bp.BenchmarkLogicalId)


def test_resolve_metrics_summary() -> None:
    p = resolve_benchmark_artifact_path(bp.BenchmarkLogicalId.REPORT_METRICS_SUMMARY)
    assert p.name == "benchmark-metrics-summary.json"
    assert p.parent.name == "results"


def test_resolve_with_custom_repo_root(tmp_path: Path) -> None:
    p = resolve_benchmark_artifact_path(
        bp.BenchmarkLogicalId.CANONICAL_LAYER1_NIGHTLY_HEAVY,
        repo_root=tmp_path,
    )
    assert p.parent == tmp_path / "eval" / "results"
