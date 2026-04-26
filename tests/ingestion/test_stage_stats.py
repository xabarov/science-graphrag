from __future__ import annotations

from science_graphrag.ingestion.stage_stats import compute_weighted_progress_pct


def test_compute_weighted_progress_pct_completed() -> None:
    stages = [
        {"name": "a", "status": "completed"},
        {"name": "b", "status": "completed"},
    ]
    weights = {"a": 1000, "b": 1000}
    assert compute_weighted_progress_pct(stages, weights) == 1.0


def test_compute_weighted_progress_pct_running_half() -> None:
    stages = [
        {"name": "a", "status": "completed"},
        {"name": "b", "status": "running"},
    ]
    weights = {"a": 1000, "b": 1000}
    assert abs(compute_weighted_progress_pct(stages, weights) - 0.75) < 1e-9
