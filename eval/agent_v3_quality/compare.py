"""Compare two v3 quality judge JSON artifacts (snapshot vs snapshot)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer


def _cost_gate_violations(
    baseline_doc: dict[str, Any],
    candidate_doc: dict[str, Any],
    *,
    max_candidate_latency_p95_ratio: float | None,
    max_candidate_tokens_total_ratio: float | None,
    max_latency_p95_ratio_regress: float | None,
    max_tokens_total_ratio_regress: float | None,
) -> list[str]:
    """Wave F1 advisory gates on ``summary.cost_delta``."""

    sa = baseline_doc.get("summary") or {}
    sb = candidate_doc.get("summary") or {}
    cda = sa.get("cost_delta") if isinstance(sa.get("cost_delta"), dict) else {}
    cdb = sb.get("cost_delta") if isinstance(sb.get("cost_delta"), dict) else {}
    errs: list[str] = []

    def _num(x: Any) -> float | None:
        if isinstance(x, (int, float)):
            return float(x)
        return None

    cr_lat = _num(cdb.get("latency_p95_ratio"))
    br_lat = _num(cda.get("latency_p95_ratio"))
    cr_tok = _num(cdb.get("tokens_total_ratio"))
    br_tok = _num(cda.get("tokens_total_ratio"))

    if max_candidate_latency_p95_ratio is not None and cr_lat is not None:
        if cr_lat > float(max_candidate_latency_p95_ratio) + 1e-9:
            errs.append(
                "cost_delta.latency_p95_ratio "
                f"{cr_lat} exceeds --max-latency-ratio "
                f"{max_candidate_latency_p95_ratio}",
            )
    if max_candidate_tokens_total_ratio is not None and cr_tok is not None:
        if cr_tok > float(max_candidate_tokens_total_ratio) + 1e-9:
            errs.append(
                "cost_delta.tokens_total_ratio "
                f"{cr_tok} exceeds --max-tokens-ratio "
                f"{max_candidate_tokens_total_ratio}",
            )

    if max_latency_p95_ratio_regress is not None and cr_lat is not None and br_lat is not None:
        if cr_lat > br_lat * float(max_latency_p95_ratio_regress) + 1e-9:
            errs.append(
                f"cost_delta.latency_p95_ratio regressed: candidate {cr_lat} > baseline "
                f"{br_lat} * {max_latency_p95_ratio_regress}",
            )
    if max_tokens_total_ratio_regress is not None and cr_tok is not None and br_tok is not None:
        if cr_tok > br_tok * float(max_tokens_total_ratio_regress) + 1e-9:
            errs.append(
                f"cost_delta.tokens_total_ratio regressed: candidate {cr_tok} > baseline "
                f"{br_tok} * {max_tokens_total_ratio_regress}",
            )
    return errs


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

    # Shallow cost_delta delta for markdown visibility
    cd_a = sa.get("cost_delta") if isinstance(sa.get("cost_delta"), dict) else None
    cd_b = sb.get("cost_delta") if isinstance(sb.get("cost_delta"), dict) else None
    if cd_a or cd_b:
        deltas["cost_delta"] = {"before": cd_a, "after": cd_b}

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
    max_latency_ratio: float | None = typer.Option(
        None,
        "--max-latency-ratio",
        help=(
            "Wave F1 advisory: exit 1 when candidate summary.cost_delta.latency_p95_ratio "
            "is strictly above this absolute cap."
        ),
    ),
    max_tokens_ratio: float | None = typer.Option(
        None,
        "--max-tokens-ratio",
        help=(
            "Wave F1 advisory: exit 1 when candidate summary.cost_delta.tokens_total_ratio "
            "is strictly above this absolute cap."
        ),
    ),
    max_latency_ratio_regress: float | None = typer.Option(
        None,
        "--max-latency-ratio-regress",
        help=(
            "Wave F1 advisory: exit 1 when candidate latency_p95_ratio > baseline_ratio * "
            "this multiplier (requires cost_delta on both artifacts)."
        ),
    ),
    max_tokens_ratio_regress: float | None = typer.Option(
        None,
        "--max-tokens-ratio-regress",
        help=(
            "Wave F1 advisory: exit 1 when candidate tokens_total_ratio > baseline_ratio * "
            "this multiplier (requires cost_delta on both artifacts)."
        ),
    ),
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

    base_doc = json.loads(baseline.read_text(encoding="utf-8"))
    cand_doc = json.loads(candidate.read_text(encoding="utf-8"))
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

    cost_errors = _cost_gate_violations(
        base_doc,
        cand_doc,
        max_candidate_latency_p95_ratio=max_latency_ratio,
        max_candidate_tokens_total_ratio=max_tokens_ratio,
        max_latency_p95_ratio_regress=max_latency_ratio_regress,
        max_tokens_total_ratio_regress=max_tokens_ratio_regress,
    )
    cost_any = any(
        x is not None
        for x in (
            max_latency_ratio,
            max_tokens_ratio,
            max_latency_ratio_regress,
            max_tokens_ratio_regress,
        )
    )
    if cost_any:
        report["cost_gate"] = {
            "enabled": True,
            "errors": cost_errors,
            "ok": not cost_errors,
        }

    text = compare_to_markdown(report)
    if gate_errors:
        text += "\n## Release-train gate\n\n"
        for err in gate_errors:
            text += f"- FAIL: {err}\n"
    if cost_errors:
        text += "\n## Cost gate (Wave F1)\n\n"
        for err in cost_errors:
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
    if cost_errors:
        typer.echo("\n".join(cost_errors), err=True)
        raise typer.Exit(code=1)


def main() -> None:
    """Console entrypoint for snapshot diff CLI."""

    typer.run(_compare_cmd)


if __name__ == "__main__":
    main()
