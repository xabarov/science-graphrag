"""CLI: offline checks for entity dedup gold packs (authors / institutions / venues / methods / datasets)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer

from eval.bench_common import benchmark_run_metadata, run_single_case_json_outputs, run_suite_cli_flow
from science_graphrag.config import Settings, get_settings


def _records_by_id(gold: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = gold.get("records")
    if not isinstance(rows, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if isinstance(row, dict):
            eid = str(row.get("entity_id") or "").strip()
            if eid:
                out[eid] = row
    return out


def _cluster_entity_sets(gold: dict[str, Any]) -> list[frozenset[str]]:
    clusters = gold.get("clusters")
    if not isinstance(clusters, list):
        return []
    out: list[frozenset[str]] = []
    for c in clusters:
        if not isinstance(c, dict):
            continue
        ids = [str(x).strip() for x in (c.get("entity_ids") or []) if str(x).strip()]
        if len(ids) >= 2:
            out.append(frozenset(ids))
    return out


def _negative_pair_separated(
    pair: dict[str, Any],
    *,
    cluster_sets: list[frozenset[str]],
    by_id: dict[str, dict[str, Any]],
) -> bool:
    ids = [str(x).strip() for x in (pair.get("entity_ids") or []) if str(x).strip()]
    if len(ids) != 2:
        return False
    a, b = ids[0], ids[1]
    for cl in cluster_sets:
        if a in cl and b in cl:
            return False
    return True


def score_entity_dedup_gold(case_dir: Path, *, settings: Settings | None = None) -> dict[str, Any]:
    root = Path(case_dir)
    s = settings or get_settings()
    try:
        gold = json.loads((root / "gold.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        return {
            "case_id": root.name,
            "metrics": {"passed": False, "error": str(exc)},
            "run_metadata": benchmark_run_metadata(s),
        }
    if not isinstance(gold, dict):
        return {
            "case_id": root.name,
            "metrics": {"passed": False, "error": "gold_not_object"},
            "run_metadata": benchmark_run_metadata(s),
        }
    by_id = _records_by_id(gold)
    cluster_sets = _cluster_entity_sets(gold)
    errors: list[str] = []
    for cl in cluster_sets:
        for eid in cl:
            if eid not in by_id:
                errors.append(f"missing_record:{eid}")
    negs = gold.get("negative_pairs")
    if isinstance(negs, list):
        for pair in negs:
            if not isinstance(pair, dict):
                continue
            if not _negative_pair_separated(pair, cluster_sets=cluster_sets, by_id=by_id):
                errors.append(f"negative_not_separated:{pair.get('pair_id')}")
    passed = not errors and bool(cluster_sets)
    return {
        "case_id": root.name,
        "entity_type": str(gold.get("entity_type") or "unknown"),
        "metrics": {
            "passed": passed,
            "cluster_count": len(cluster_sets),
            "errors": errors[:20],
            "eval_mode": "offline_gold_structure",
        },
        "run_metadata": benchmark_run_metadata(s),
    }


def discover_dedup_case_dirs(root: Path) -> list[Path]:
    return [p for p in sorted(root.iterdir()) if p.is_dir() and (p / "gold.json").is_file()]


def _summarize(report: dict[str, Any]) -> str:
    cid = report.get("case_id")
    passed = bool((report.get("metrics") or {}).get("passed"))
    status = "PASS" if passed else "FAIL"
    return f"## {cid} — {status}\n\n```json\n{json.dumps(report.get('metrics'), indent=2)}\n```\n"


def _cli(
    path: Path = typer.Argument(..., exists=True, readable=True),
    suite: bool = typer.Option(False, "--suite"),
    json_out: Path | None = typer.Option(None, "--json-out"),
    md_out: Path | None = typer.Option(None, "--md-out"),
) -> None:
    settings = get_settings()

    def _run_one(c: Path) -> dict[str, Any]:
        return score_entity_dedup_gold(c, settings=settings)

    if suite:
        cases = discover_dedup_case_dirs(path)
        if not cases:
            typer.echo(f"No dedup gold cases under {path}", err=True)
            raise typer.Exit(code=1)
        payload = run_suite_cli_flow(
            title="Entity dedup gold benchmark (BT11 offline)",
            cases=cases,
            settings=settings,
            run_one=_run_one,
            summarize=_summarize,
            json_out=json_out,
            md_out=md_out,
            summary_from_reports=lambda reports: {
                "all_passed": all(bool((r.get("metrics") or {}).get("passed")) for r in reports),
                "entity_dedup_gold_eval": True,
            },
        )
        if not bool(payload.get("summary", {}).get("all_passed", True)):
            raise typer.Exit(code=1)
        return

    report = _run_one(path)
    run_single_case_json_outputs(
        report=report,
        settings=settings,
        summarize=_summarize,
        json_out=json_out,
        md_out=md_out,
    )
    if not bool((report.get("metrics") or {}).get("passed")):
        raise typer.Exit(code=1)


def main() -> None:
    typer.run(_cli)


if __name__ == "__main__":
    main()
