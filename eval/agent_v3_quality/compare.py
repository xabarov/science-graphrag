"""Compare two v3 quality judge JSON artifacts (snapshot vs snapshot)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer


def compare_reports(baseline_path: Path, candidate_path: Path) -> dict[str, Any]:
    """Load two judge JSON artifacts and compute summary field deltas."""

    a = json.loads(baseline_path.read_text(encoding="utf-8"))
    b = json.loads(candidate_path.read_text(encoding="utf-8"))
    sa = a.get("summary") or {}
    sb = b.get("summary") or {}
    keys = (
        "mean_weighted_score_baseline",
        "mean_weighted_score_candidate",
        "mean_delta",
        "pairwise_candidate_win_rate",
        "pairwise_baseline_win_rate",
        "pairwise_tie_rate",
        "hard_fail_count_baseline",
        "hard_fail_count_candidate",
    )
    deltas: dict[str, Any] = {}
    for k in keys:
        va, vb = sa.get(k), sb.get(k)
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
            deltas[k] = round(float(vb) - float(va), 4)
        else:
            deltas[k] = {"before": va, "after": vb}
    return {
        "review_version": a.get("review_version"),
        "baseline_artifact": str(baseline_path),
        "candidate_artifact": str(candidate_path),
        "deltas": deltas,
        "case_count_before": sa.get("case_count"),
        "case_count_after": sb.get("case_count"),
    }


def compare_to_markdown(report: dict[str, Any]) -> str:
    """Render ``compare_reports`` output as Markdown."""

    lines = [
        "# Agent v3 quality judge — compare",
        "",
        f"- baseline: `{report.get('baseline_artifact')}`",
        f"- candidate: `{report.get('candidate_artifact')}`",
        "",
        "## Summary deltas",
        "",
    ]
    for k, v in (report.get("deltas") or {}).items():
        lines.append(f"- **{k}**: `{v}`")
    lines.append("")
    return "\n".join(lines)


def _compare_cmd(
    baseline: Path = typer.Argument(..., exists=True, readable=True),
    candidate: Path = typer.Argument(..., exists=True, readable=True),
    json_out: Path | None = typer.Option(None, "--json-out"),
    md_out: Path | None = typer.Option(None, "--md-out"),
) -> None:
    """Typer handler for ``science-graphrag-agent-v3-quality-compare``."""

    report = compare_reports(baseline, candidate)
    text = compare_to_markdown(report)
    typer.echo(text)
    if json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    if md_out:
        md_out.parent.mkdir(parents=True, exist_ok=True)
        md_out.write_text(text, encoding="utf-8")


def main() -> None:
    """Console entrypoint for snapshot diff CLI."""

    typer.run(_compare_cmd)


if __name__ == "__main__":
    main()
