"""Release-train compare gate (Wave D)."""

from __future__ import annotations

import json
from pathlib import Path

from eval.agent_v3_quality.compare import release_train_gate_violations


def _write_pair(tmp_path: Path, *, b_md: float, c_md: float, c_branch: int) -> tuple[Path, Path]:
    base = {"summary": {"mean_delta": b_md, "cases_with_any_branch_non_ok": 0}}
    cand = {"summary": {"mean_delta": c_md, "cases_with_any_branch_non_ok": c_branch}}
    p1 = tmp_path / "baseline.json"
    p2 = tmp_path / "candidate.json"
    p1.write_text(json.dumps(base), encoding="utf-8")
    p2.write_text(json.dumps(cand), encoding="utf-8")
    return p1, p2


def test_release_gate_ok_when_within_margin(tmp_path: Path) -> None:
    """Candidate within mean_delta margin and branch_ok cap passes."""

    p1, p2 = _write_pair(tmp_path, b_md=0.0, c_md=-0.05, c_branch=0)
    assert not release_train_gate_violations(p1, p2)


def test_release_gate_fails_mean_delta(tmp_path: Path) -> None:
    """Large negative mean_delta vs baseline fails."""

    p1, p2 = _write_pair(tmp_path, b_md=0.0, c_md=-0.5, c_branch=0)
    errs = release_train_gate_violations(p1, p2, mean_delta_margin=0.10)
    assert len(errs) == 1
    assert "mean_delta regression" in errs[0]


def test_release_gate_fails_branch_non_ok(tmp_path: Path) -> None:
    """Non-zero branch_non_ok beyond cap fails."""

    p1, p2 = _write_pair(tmp_path, b_md=0.0, c_md=0.0, c_branch=1)
    errs = release_train_gate_violations(p1, p2, max_branch_non_ok=0)
    assert len(errs) == 1
    assert "cases_with_any_branch_non_ok" in errs[0]


def test_release_gate_fails_missing_mean_delta(tmp_path: Path) -> None:
    """Missing numeric mean_delta on candidate fails the gate."""

    base = {"summary": {"mean_delta": 0.0, "cases_with_any_branch_non_ok": 0}}
    cand = {"summary": {"cases_with_any_branch_non_ok": 0}}
    p1 = tmp_path / "baseline.json"
    p2 = tmp_path / "candidate.json"
    p1.write_text(json.dumps(base), encoding="utf-8")
    p2.write_text(json.dumps(cand), encoding="utf-8")
    errs = release_train_gate_violations(p1, p2)
    assert any("mean_delta gate" in e for e in errs)


def test_release_gate_branch_missing_treated_as_zero(tmp_path: Path) -> None:
    """Omitted cases_with_any_branch_non_ok is treated as zero."""

    base = {"summary": {"mean_delta": 0.0, "cases_with_any_branch_non_ok": 0}}
    cand = {"summary": {"mean_delta": 0.0}}
    p1 = tmp_path / "baseline.json"
    p2 = tmp_path / "candidate.json"
    p1.write_text(json.dumps(base), encoding="utf-8")
    p2.write_text(json.dumps(cand), encoding="utf-8")
    assert not release_train_gate_violations(p1, p2)
