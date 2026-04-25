"""CLI: multi-hop graph retrieval benchmark suite (Wave Q, advisory)."""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter
from typing import Any

import httpx
import typer

from eval.bench_common import (
    benchmark_run_metadata,
    run_single_case_json_outputs,
    run_suite_cli_flow,
)
from science_graphrag.config import Settings, get_settings


def _load_tiers(fixtures_root: Path) -> dict[str, list[str]] | None:
    p = fixtures_root / "case_tiers.json"
    if not p.is_file():
        return None
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return None
    out: dict[str, list[str]] = {}
    for k, v in raw.items():
        if isinstance(v, list):
            out[str(k)] = [str(x) for x in v]
    return out or None


def discover_multihop_cases(fixtures_root: Path, *, tier: str) -> list[Path]:
    tiers = _load_tiers(fixtures_root)
    allowed = set(tiers.get(tier) or []) if tiers else None
    out: list[Path] = []
    for child in sorted(fixtures_root.iterdir()):
        if not child.is_dir():
            continue
        if not (child / "question.json").is_file():
            continue
        if allowed is not None and child.name not in allowed:
            continue
        out.append(child)
    return out


def _extract_returned_work_ids(payload: dict[str, Any], *, center_work_id: str) -> list[str]:
    nodes = payload.get("nodes")
    if not isinstance(nodes, list):
        return []
    out: list[str] = []
    center = center_work_id.strip()
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id") or "").strip()
        node_type = str(node.get("type") or "").strip()
        if node_type != "Work" or not node_id:
            continue
        if node_id == center:
            continue
        out.append(node_id)
    return out


def score_multihop_case(
    expected_neighbor_work_ids: list[str],
    returned_neighbor_work_ids: list[str],
    *,
    min_precision: float,
    min_recall: float,
) -> dict[str, Any]:
    exp = {str(x).strip() for x in expected_neighbor_work_ids if str(x).strip()}
    ret = {str(x).strip() for x in returned_neighbor_work_ids if str(x).strip()}
    matched = sorted(exp & ret)
    precision = (len(matched) / len(ret)) if ret else (1.0 if not exp else 0.0)
    recall = (len(matched) / len(exp)) if exp else 1.0
    passed = precision + 1e-9 >= float(min_precision) and recall + 1e-9 >= float(min_recall)
    return {
        "passed": passed,
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "min_precision": float(min_precision),
        "min_recall": float(min_recall),
        "expected_count": len(exp),
        "returned_count": len(ret),
        "matched_work_ids": matched,
        "missing_work_ids": sorted(exp - ret),
        "unexpected_work_ids": sorted(ret - exp),
    }


def run_multihop_case(
    case_dir: Path | str,
    *,
    api_base_url: str,
    timeout_seconds: float,
    settings: Settings | None = None,
) -> dict[str, Any]:
    root = Path(case_dir)
    case = json.loads((root / "question.json").read_text(encoding="utf-8"))
    center_work_id = str(case.get("center_work_id") or "").strip()
    depth = int(case.get("depth") or 2)
    neighbor_limit = int(case.get("neighbor_limit") or 300)
    expected = [str(x) for x in (case.get("expected_neighbor_work_ids") or [])]
    min_precision = float(case.get("min_precision") or 0.7)
    min_recall = float(case.get("min_recall") or 0.5)
    query_hint = str(case.get("query_hint") or "")

    s = settings or get_settings()
    started = perf_counter()
    request_error: str | None = None
    graph_payload: dict[str, Any] = {}
    returned_ids: list[str] = []

    if not center_work_id:
        request_error = "center_work_id_required"
    else:
        try:
            with httpx.Client(timeout=timeout_seconds) as client:
                resp = client.get(
                    f"{api_base_url.rstrip('/')}/v1/works/{center_work_id}/graph",
                    params={"depth": depth, "neighbor_limit": neighbor_limit},
                )
                resp.raise_for_status()
                graph_payload = resp.json()
                if not isinstance(graph_payload, dict):
                    graph_payload = {}
        except Exception as exc:  # noqa: BLE001
            request_error = str(exc)

    if request_error is None:
        returned_ids = _extract_returned_work_ids(graph_payload, center_work_id=center_work_id)
    metrics = score_multihop_case(
        expected,
        returned_ids,
        min_precision=min_precision,
        min_recall=min_recall,
    )
    if request_error:
        metrics["passed"] = False
        metrics["request_error"] = request_error

    elapsed = perf_counter() - started
    return {
        "case_id": root.name,
        "query_hint": query_hint,
        "center_work_id": center_work_id,
        "depth": depth,
        "neighbor_limit": neighbor_limit,
        "metrics": metrics,
        "returned_neighbor_work_ids": returned_ids,
        "wall_clock_seconds": round(elapsed, 6),
        "run_metadata": benchmark_run_metadata(s),
    }


def _summarize(report: dict[str, Any]) -> str:
    cid = report.get("case_id")
    passed = bool((report.get("metrics") or {}).get("passed"))
    status = "PASS" if passed else "FAIL"
    return f"## {cid} — {status}\n\n```json\n{json.dumps(report.get('metrics'), indent=2)}\n```\n"


def _cli(
    path: Path = typer.Argument(
        ...,
        exists=True,
        readable=True,
        help="Suite root (directory containing case subdirs and case_tiers.json)",
    ),
    suite: bool = typer.Option(False, "--suite", help="Run all multihop cases for tier"),
    tier: str = typer.Option(
        "multihop_mini",
        "--tier",
        help="Tier key from case_tiers.json (default: multihop_mini).",
    ),
    api_base_url: str = typer.Option(
        "http://localhost:8000",
        "--api-base-url",
        help="Base URL for science-graphrag API.",
    ),
    timeout_seconds: float = typer.Option(20.0, "--timeout-seconds", help="Per-case HTTP timeout."),
    json_out: Path | None = typer.Option(None, "--json-out"),
    md_out: Path | None = typer.Option(None, "--md-out"),
) -> None:
    settings = get_settings()

    def _is_passed(report: dict[str, Any]) -> bool:
        return bool((report.get("metrics") or {}).get("passed"))

    def _run_one(c: Path) -> dict[str, Any]:
        return run_multihop_case(
            c,
            api_base_url=api_base_url,
            timeout_seconds=timeout_seconds,
            settings=settings,
        )

    if suite:
        cases = discover_multihop_cases(path, tier=tier)
        if not cases:
            typer.echo(f"No multihop cases under {path} for tier={tier!r}", err=True)
            raise typer.Exit(code=1)
        payload = run_suite_cli_flow(
            title="Multi-hop retrieval benchmark (advisory)",
            cases=cases,
            settings=settings,
            run_one=_run_one,
            summarize=_summarize,
            json_out=json_out,
            md_out=md_out,
            summary_from_reports=lambda reports: {
                "all_passed": all(_is_passed(r) for r in reports),
                "multihop_eval": True,
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
    if not _is_passed(report):
        raise typer.Exit(code=1)


def main() -> None:
    typer.run(_cli)


if __name__ == "__main__":
    main()
