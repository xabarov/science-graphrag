"""Compare benchmark JSON reports: baseline vs current."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _as_case_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if "cases" in payload and isinstance(payload["cases"], list):
        return {
            str(case.get("case_id", f"case_{idx}")): case
            for idx, case in enumerate(payload["cases"])
            if isinstance(case, dict)
        }
    if "case" in payload and isinstance(payload["case"], dict):
        case = payload["case"]
        case_id = str(case.get("case_id", "single_case"))
        return {case_id: case}
    return {}


def _flatten(prefix: str, node: Any, out: dict[str, Any]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            nxt = f"{prefix}.{key}" if prefix else str(key)
            _flatten(nxt, value, out)
        return
    if isinstance(node, (list, tuple)):
        return
    out[prefix] = node


def _metric_scalars(case: dict[str, Any]) -> dict[str, Any]:
    metrics = case.get("metrics", {})
    flat: dict[str, Any] = {}
    if isinstance(metrics, dict):
        _flatten("", metrics, flat)
    return flat


def normalize_api_run_for_compare(
    run: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Build CLI-shaped report dict for :func:`compare_reports` from API/task_store run JSON.

    Keeps only cases with status ok and a dict ``result.metrics``. Other cases are listed as
    skipped with a short reason (for UI diagnostics).
    """
    skipped: list[dict[str, Any]] = []
    cases_out: list[dict[str, Any]] = []
    for row in run.get("cases") or []:
        if not isinstance(row, dict):
            continue
        cid = row.get("case_id")
        status = row.get("status")
        if status != "ok":
            skipped.append({"case_id": cid, "reason": str(status or "not_ok")})
            continue
        result = row.get("result")
        if not isinstance(result, dict):
            skipped.append({"case_id": cid, "reason": "no_result"})
            continue
        metrics = result.get("metrics")
        if not isinstance(metrics, dict):
            skipped.append({"case_id": cid, "reason": "no_metrics"})
            continue
        cases_out.append({"case_id": cid, "metrics": metrics})

    run_config = run.get("run_config") if isinstance(run.get("run_config"), dict) else {}
    run_metadata: dict[str, Any] = {
        "run_id": run.get("run_id"),
        "label": run.get("label"),
        "benchmark_family": run.get("benchmark_family"),
    }
    for key, val in sorted(run_config.items()):
        run_metadata[f"cfg_{key}"] = val

    return {"cases": cases_out, "run_metadata": run_metadata}, skipped


def compare_reports(baseline: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    baseline_cases = _as_case_map(baseline)
    current_cases = _as_case_map(current)

    all_case_ids = sorted(set(baseline_cases) | set(current_cases))
    regressions: list[dict[str, Any]] = []
    improvements: list[dict[str, Any]] = []
    unchanged: list[dict[str, Any]] = []
    missing_in_current = sorted(set(baseline_cases) - set(current_cases))
    added_in_current = sorted(set(current_cases) - set(baseline_cases))

    for case_id in all_case_ids:
        b_case = baseline_cases.get(case_id)
        c_case = current_cases.get(case_id)
        if not b_case or not c_case:
            continue
        b_flat = _metric_scalars(b_case)
        c_flat = _metric_scalars(c_case)
        common = sorted(set(b_flat) & set(c_flat))
        for key in common:
            b_val = b_flat[key]
            c_val = c_flat[key]
            if isinstance(b_val, bool) and isinstance(c_val, bool):
                row = {
                    "case_id": case_id,
                    "metric": key,
                    "baseline": b_val,
                    "current": c_val,
                }
                if b_val and not c_val:
                    regressions.append(row)
                elif (not b_val) and c_val:
                    improvements.append(row)
                else:
                    unchanged.append(row)
            elif isinstance(b_val, (int, float)) and isinstance(c_val, (int, float)):
                row = {
                    "case_id": case_id,
                    "metric": key,
                    "baseline": float(b_val),
                    "current": float(c_val),
                    "delta": float(c_val) - float(b_val),
                }
                if c_val < b_val:
                    regressions.append(row)
                elif c_val > b_val:
                    improvements.append(row)
                else:
                    unchanged.append(row)
            elif b_val == c_val:
                unchanged.append(
                    {"case_id": case_id, "metric": key, "baseline": b_val, "current": c_val}
                )

    run_metadata_delta = {}
    b_meta = baseline.get("run_metadata", {})
    c_meta = current.get("run_metadata", {})
    if isinstance(b_meta, dict) and isinstance(c_meta, dict):
        keys = sorted(set(b_meta) | set(c_meta))
        run_metadata_delta = {
            key: {"baseline": b_meta.get(key), "current": c_meta.get(key)}
            for key in keys
            if b_meta.get(key) != c_meta.get(key)
        }

    return {
        "summary": {
            "baseline_cases": len(baseline_cases),
            "current_cases": len(current_cases),
            "missing_in_current": missing_in_current,
            "added_in_current": added_in_current,
            "regression_count": len(regressions),
            "improvement_count": len(improvements),
            "unchanged_count": len(unchanged),
        },
        "run_metadata_delta": run_metadata_delta,
        "regressions": regressions,
        "improvements": improvements,
        "unchanged": unchanged,
    }


def compare_result_to_markdown(
    result: dict[str, Any],
    *,
    baseline_label: str = "baseline",
    current_label: str = "current",
    max_issue_rows: int = 30,
) -> str:
    """Render a compare_reports-style dict as Markdown (no filesystem paths required)."""
    summary = result["summary"]
    lines = [
        "# Benchmark report compare",
        "",
        f"- baseline: {baseline_label}",
        f"- current: {current_label}",
        "",
        "## Summary",
        f"- baseline_cases: {summary['baseline_cases']}",
        f"- current_cases: {summary['current_cases']}",
        f"- missing_in_current: {summary['missing_in_current']}",
        f"- added_in_current: {summary['added_in_current']}",
        f"- regressions: {summary['regression_count']}",
        f"- improvements: {summary['improvement_count']}",
        f"- unchanged_metric_rows: {summary.get('unchanged_count', 0)}",
        "",
    ]
    meta_delta = result.get("run_metadata_delta") or {}
    if meta_delta:
        lines.extend(["## Run metadata changed", f"- {meta_delta}", ""])
    regressions = result.get("regressions") or []
    if regressions:
        lines.append("## Regressions")
        for row in regressions[:max_issue_rows]:
            lines.append(
                f"- {row['case_id']} :: {row['metric']} :: {row['baseline']} -> {row['current']}"
            )
        lines.append("")
    improvements = result.get("improvements") or []
    if improvements:
        lines.append("## Improvements")
        for row in improvements[:max_issue_rows]:
            lines.append(
                f"- {row['case_id']} :: {row['metric']} :: {row['baseline']} -> {row['current']}"
            )
        lines.append("")
    unchanged = result.get("unchanged") or []
    if unchanged:
        lines.append("## Unchanged (sample)")
        for row in unchanged[:max_issue_rows]:
            lines.append(
                f"- {row['case_id']} :: {row['metric']} :: {row['baseline']} == {row['current']}"
            )
        lines.append("")
    return "\n".join(lines)


def _markdown(result: dict[str, Any], baseline_path: Path, current_path: Path) -> str:
    return compare_result_to_markdown(
        result,
        baseline_label=str(baseline_path),
        current_label=str(current_path),
    )


def _cli(
    baseline: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    current: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    json_out: Path | None = typer.Option(None, "--json-out"),
    md_out: Path | None = typer.Option(None, "--md-out"),
) -> None:
    baseline_payload = _load(baseline)
    current_payload = _load(current)
    result = compare_reports(baseline_payload, current_payload)
    md = _markdown(result, baseline, current)
    typer.echo(md)

    if json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        typer.echo(f"Wrote JSON compare report to {json_out}", err=True)
    if md_out:
        md_out.parent.mkdir(parents=True, exist_ok=True)
        md_out.write_text(md, encoding="utf-8")
        typer.echo(f"Wrote Markdown compare summary to {md_out}", err=True)

    if result["summary"]["regression_count"] > 0:
        raise typer.Exit(code=1)


def main() -> None:
    typer.run(_cli)


if __name__ == "__main__":
    main()
