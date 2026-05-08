"""Tier manifest invariants for agent v3 quality fixtures."""

from __future__ import annotations

import json
from pathlib import Path


def test_holdout_disjoint_from_pilot() -> None:
    root = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "fixtures"
        / "benchmarks"
        / "agent_v3_quality"
    )
    data = json.loads((root / "case_tiers.json").read_text(encoding="utf-8"))
    pilot = set(data["judge_pilot"])
    hold = set(data["judge_holdout"])
    assert not (pilot & hold)
