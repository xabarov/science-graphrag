"""Synthetic fork vs coordinator-stub lane artifact for ADR B0 / rollout decisions.

This does **not** run live LLM traffic. It emits JSON + Markdown under ``eval/results/``
so operators can plug in real ``agent_trace_review`` exports later while keeping a stable
schema for CI/docs links.
"""

from __future__ import annotations

import json
from pathlib import Path


def _synthetic_case(*, lane: str) -> dict[str, object]:
    """Two lanes on the same logical scenario shape (latency + cache + missing counts)."""
    return {
        "case_id": f"synthetic-subagent-bench-{lane}",
        "duration_ms": 1180 if lane == "fork_v3_enhanced" else 1320,
        "run_metadata": {
            "run_kind": "supervisor_specialists_v3",
            "graph_id": "supervisor_graph_v3",
            "subagent_observability_lane": lane,
            "subagent_runs": [
                {
                    "subagent_id": "retrieval_agent",
                    "terminal_state": "succeeded",
                    "latency_ms": 400,
                },
                {
                    "subagent_id": "writer_agent",
                    "terminal_state": "succeeded",
                    "latency_ms": 600,
                },
            ],
            "subagent_task_notifications": (
                [
                    {"task_id": "t-ret", "subagent_id": "retrieval_agent", "status": "completed"},
                    {"task_id": "t-wri", "subagent_id": "writer_agent", "status": "completed"},
                ]
                if lane == "fork_v3_enhanced"
                else []
            ),
            "thread_insight_audit": {
                "side_llm_cache_read_ratio": 0.82 if lane == "fork_v3_enhanced" else 0.41,
                "forked": True,
            },
        },
    }


def run_benchmark(*, repo_root: Path | None = None) -> tuple[Path, Path]:
    root = repo_root or Path(__file__).resolve().parents[2]
    out_dir = root / "eval" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    fork = _synthetic_case(lane="fork_v3_enhanced")
    coord = _synthetic_case(lane="coordinator_stub")
    payload = {
        "schema_version": 1,
        "lane_fork_v3": fork,
        "lane_coordinator_stub": coord,
        "interpretation": {
            "latency_delta_ms": int(coord["duration_ms"]) - int(fork["duration_ms"]),
            "missing_notifications_coordinator_stub": 2,
            "note": "coordinator_stub lane intentionally drops task_notifications to model observability gap.",
        },
    }
    json_path = out_dir / "subagent-runtime-fork-vs-coordinator-bench.json"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_lines = [
        "# Subagent runtime benchmark (synthetic lanes)",
        "",
        "| Metric | fork_v3_enhanced | coordinator_stub |",
        "|--------|------------------|-------------------|",
        f"| duration_ms | {fork['duration_ms']} | {coord['duration_ms']} |",
        "| side_llm_cache_read_ratio (audit) | 0.82 | 0.41 |",
        "| subagent_task_notifications | 2 | 0 (missing) |",
        "",
        "Replace ``lane_*`` blocks with exports from ``scripts/live_check/agent_trace_review.py`` "
        "for production acceptance.",
    ]
    md_path = out_dir / "subagent-runtime-fork-vs-coordinator-bench.md"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> None:
    jp, mp = run_benchmark()
    print(f"wrote {jp}")
    print(f"wrote {mp}")


if __name__ == "__main__":
    main()
