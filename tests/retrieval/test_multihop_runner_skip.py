"""BT3: multihop suite exits 2 without ``--allow-skip-on-infra`` when API is down."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_multihop_suite_writes_skip_and_exits_2_without_allow_skip() -> None:
    """Health failure without ``--allow-skip-on-infra`` must exit 2 and emit a skip JSON."""
    results = REPO_ROOT / "eval" / "results"
    results.mkdir(parents=True, exist_ok=True)
    before = set(results.glob("multihop-skipped-*.json"))
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "eval.retrieval.multihop_runner",
            str(REPO_ROOT / "tests/fixtures/benchmarks/retrieval/multihop_v2"),
            "--suite",
            "--tier",
            "multihop_v2_pilot",
            "--api-base-url",
            "http://127.0.0.1:59997",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    after = set(results.glob("multihop-skipped-*.json"))
    new = sorted(after - before, key=lambda p: p.stat().st_mtime, reverse=True)
    try:
        assert proc.returncode == 2, proc.stdout + proc.stderr
        assert new, "expected a new multihop-skipped-*.json artifact"
    finally:
        for p in new:
            p.unlink(missing_ok=True)


def test_multihop_suite_exits_0_with_allow_skip_on_infra() -> None:
    """With ``--allow-skip-on-infra``, unhealthy API must exit 0 after writing skip JSON."""
    results = REPO_ROOT / "eval" / "results"
    before = set(results.glob("multihop-skipped-*.json"))
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "eval.retrieval.multihop_runner",
            str(REPO_ROOT / "tests/fixtures/benchmarks/retrieval/multihop_v2"),
            "--suite",
            "--tier",
            "multihop_v2_pilot",
            "--api-base-url",
            "http://127.0.0.1:59998",
            "--allow-skip-on-infra",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    after = set(results.glob("multihop-skipped-*.json"))
    new = sorted(after - before, key=lambda p: p.stat().st_mtime, reverse=True)
    try:
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert new, "expected a new multihop-skipped-*.json artifact"
    finally:
        for p in new:
            p.unlink(missing_ok=True)
