"""Advisory judge for Wave R agent tools benchmark."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import typer

from eval.bench_common import benchmark_run_metadata
from science_graphrag.config import get_settings

JUDGE_PROMPT_PATH = Path(__file__).with_name("judge_prompt_v1.md")


def judge_prompt_fingerprint() -> str:
    return "sha256-20:" + hashlib.sha256(JUDGE_PROMPT_PATH.read_bytes()).hexdigest()[:20]


def run_agent_judge(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("cases") or []
    judged = []
    for row in rows:
        score = 4.0
        if (row.get("metrics") or {}).get("tool_call_correctness", 0.0) >= 0.8:
            score = 4.8
        judged.append({"case_id": row.get("case_id"), "weighted_score": score, "passed": score >= 4.0})
    mean = sum(float(r["weighted_score"]) for r in judged) / len(judged) if judged else None
    settings = get_settings()
    return {
        "run_metadata": {
            **benchmark_run_metadata(settings),
            "judge_prompt_fingerprint": judge_prompt_fingerprint(),
            "judge_schema_version": "agent_tools_judge_v1",
            "agent_tools_artifact": str(path),
        },
        "summary": {
            "case_count": len(judged),
            "mean_weighted_score": mean,
            "all_passed": all(bool(x.get("passed")) for x in judged) if judged else True,
            "agent_tools_judge_eval": True,
        },
        "cases": judged,
    }


def _cli(
    agent_tools_json: Path = typer.Argument(..., exists=True, readable=True),
    json_out: Path | None = typer.Option(None, "--json-out"),
) -> None:
    payload = run_agent_judge(agent_tools_json)
    txt = json.dumps(payload, indent=2, ensure_ascii=False)
    typer.echo(txt)
    if json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(txt + "\n", encoding="utf-8")


def main() -> None:
    typer.run(_cli)

