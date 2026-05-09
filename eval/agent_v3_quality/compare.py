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
        "cases_with_any_branch_non_ok",
        "all_passed",
    )
    deltas: dict[str, Any] = {}
    for k in keys:
        va, vb = sa.get(k), sb.get(k)
        if isinstance(va, bool) or isinstance(vb, bool):
            deltas[k] = {"before": va, "after": vb}
        elif isinstance(va, (int, float)) and isinstance(vb, (int, float)):
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


def release_train_gate_violations(
    baseline_path: Path,
    candidate_path: Path,
    *,
    mean_delta_margin: float = 0.10,
    max_branch_non_ok: int = 0,
) -> list[str]:
    """Wave D release-train checks (advisory; not merge ``decision_gate``).

    - Candidate ``mean_delta`` must not fall below ``baseline_mean_delta - mean_delta_margin``.
      Both values must be numeric; otherwise a single error is recorded (no silent pass).
    - Candidate ``cases_with_any_branch_non_ok`` must be <= ``max_branch_non_ok``.
      A missing field is treated as ``0``; non-numeric values are an error.
    """

    base = json.loads(baseline_path.read_text(encoding="utf-8"))
    cand = json.loads(candidate_path.read_text(encoding="utf-8"))
    sa = base.get("summary") or {}
    sb = cand.get("summary") or {}
    errors: list[str] = []

    b_md = sa.get("mean_delta")
    c_md = sb.get("mean_delta")
    b_ok = isinstance(b_md, (int, float))
    c_ok = isinstance(c_md, (int, float))
    if b_ok and c_ok:
        floor = float(b_md) - float(mean_delta_margin)
        if float(c_md) < floor:
            errors.append(
                "mean_delta regression: candidate "
                f"{c_md} < baseline {b_md} - {mean_delta_margin} (floor {floor})",
            )
    else:
        errors.append(
            "mean_delta gate: need numeric summary.mean_delta on baseline "
            f"and candidate (baseline={b_md!r}, candidate={c_md!r})",
        )

    branch_raw = sb.get("cases_with_any_branch_non_ok")
    if branch_raw is None:
        branch_n = 0
    elif isinstance(branch_raw, (int, float)):
        branch_n = int(branch_raw)
    else:
        errors.append(
            f"candidate cases_with_any_branch_non_ok is not numeric: {branch_raw!r}",
        )
        branch_n = 0
    if branch_n > int(max_branch_non_ok):
        errors.append(
            "candidate cases_with_any_branch_non_ok="
            f"{branch_n} exceeds max allowed {max_branch_non_ok}",
        )
    return errors


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
    release_train_gate: bool = typer.Option(
        False,
        "--release-train-gate",
        help=(
            "Exit 1 if candidate regresses mean_delta vs baseline or "
            "branch_non_ok exceeds cap (Wave D)."
        ),
    ),
    gate_mean_delta_margin: float = typer.Option(
        0.10,
        "--gate-mean-delta-margin",
        help="With --release-train-gate: candidate mean_delta >= baseline - margin.",
    ),
    gate_max_branch_non_ok: int = typer.Option(
        0,
        "--gate-max-branch-non-ok",
        help="With --release-train-gate: max candidate cases_with_any_branch_non_ok.",
    ),
) -> None:
    """Typer handler for ``science-graphrag-agent-v3-quality-compare``."""

    report = compare_reports(baseline, candidate)
    gate_errors: list[str] = []
    if release_train_gate:
        gate_errors = release_train_gate_violations(
            baseline,
            candidate,
            mean_delta_margin=gate_mean_delta_margin,
            max_branch_non_ok=gate_max_branch_non_ok,
        )
        report["release_train_gate"] = {
            "enabled": True,
            "mean_delta_margin": gate_mean_delta_margin,
            "max_branch_non_ok": gate_max_branch_non_ok,
            "errors": gate_errors,
            "ok": not gate_errors,
        }

    text = compare_to_markdown(report)
    if gate_errors:
        text += "\n## Release-train gate\n\n"
        for err in gate_errors:
            text += f"- FAIL: {err}\n"
    typer.echo(text)
    if json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    if md_out:
        md_out.parent.mkdir(parents=True, exist_ok=True)
        md_out.write_text(text, encoding="utf-8")
    if release_train_gate and gate_errors:
        typer.echo("\n".join(gate_errors), err=True)
        raise typer.Exit(code=1)


def main() -> None:
    """Console entrypoint for snapshot diff CLI."""

    typer.run(_compare_cmd)


if __name__ == "__main__":
    main()
