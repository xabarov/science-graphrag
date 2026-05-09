"""Calibration window case list stays aligned with judge_pilot / holdout rules."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "tests/fixtures/benchmarks/agent_v3_quality"


def test_calibration_window_case_ids_valid() -> None:
    window_path = FIXTURE / "calibration_window_case_ids.json"
    tiers_path = FIXTURE / "case_tiers.json"
    window = json.loads(window_path.read_text(encoding="utf-8"))
    tiers = json.loads(tiers_path.read_text(encoding="utf-8"))
    ids = window["case_ids"]
    pilot = set(tiers["judge_pilot"])
    holdout = set(tiers["judge_holdout"])
    assert 6 <= len(ids) <= 10
    assert set(ids).issubset(pilot)
    assert not set(ids) & holdout
