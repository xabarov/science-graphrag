"""Advisory judge for Wave S idea-assist benchmark."""

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


def run_idea_judge(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("cases") or []
    judged = []
    for row in rows:
        metrics = row.get("metrics") or {}
        score = float(metrics.get("mean_rubric_score") or 0.0)
        judged.append(
            {
                "case_id": row.get("case_id"),
                "weighted_score": score,
                "passed": score >= 4.0,
            }
        )
    mean = sum(float(r["weighted_score"]) for r in judged) / len(judged) if judged else None
    settings = get_settings()
    return {
        "run_metadata": {
            **benchmark_run_metadata(settings),
            "judge_prompt_fingerprint": judge_prompt_fingerprint(),
            "judge_schema_version": "idea_assist_judge_v1",
            "idea_assist_artifact": str(path),
        },
        "summary": {
            "case_count": len(judged),
            "mean_weighted_score": mean,
            "all_passed": all(bool(x.get("passed")) for x in judged) if judged else True,
            "idea_assist_judge_eval": True,
        },
        "cases": judged,
    }


def _cli(
    idea_assist_json: Path = typer.Argument(..., exists=True, readable=True),
    json_out: Path | None = typer.Option(None, "--json-out"),
) -> None:
    payload = run_idea_judge(idea_assist_json)
    txt = json.dumps(payload, indent=2, ensure_ascii=False)
    typer.echo(txt)
    if json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(txt + "\n", encoding="utf-8")


def main() -> None:
    typer.run(_cli)
