from __future__ import annotations

from pathlib import Path

from eval.chat_agent.subagent_runtime_fork_vs_coordinator_bench import run_benchmark


def test_subagent_runtime_bench_writes_artifacts(tmp_path: Path) -> None:
    jp, mp = run_benchmark(repo_root=tmp_path)
    assert jp.is_file() and mp.is_file()
    data = jp.read_text(encoding="utf-8")
    assert "lane_fork_v3" in data
    assert "coordinator_stub" in data
