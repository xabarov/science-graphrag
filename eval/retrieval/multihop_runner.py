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
from eval.retrieval.stack_health import check_api_health, write_skip_artifact
from science_graphrag.config import Settings, get_settings

_REPO_ROOT = Path(__file__).resolve().parents[2]


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


def _load_multihop_case_dict(root: Path) -> dict[str, Any]:
    """Load v1 ``question.json`` or derive from multihop v2 ``gold.json`` + ``question.txt`` (ordered_chain)."""

    q_json = root / "question.json"
    if q_json.is_file():
        raw = json.loads(q_json.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            return raw
        raise TypeError("question.json must be an object")
    gold_path = root / "gold.json"
    if not gold_path.is_file():
        raise FileNotFoundError(f"no question.json or gold.json in {root}")
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    if not isinstance(gold, dict):
        raise TypeError("gold.json must be an object")
    if str(gold.get("expected_path_kind") or "") != "ordered_chain":
        raise ValueError(
            f"multihop case {root.name}: unsupported gold layout "
            "(only ordered_chain from gold without question.json; unordered_set pending)",
        )
    chain = [str(x).strip() for x in (gold.get("expected_chain_corpus_work_ids") or []) if str(x).strip()]
    if len(chain) < 2:
        raise ValueError(f"multihop case {root.name}: expected_chain_corpus_work_ids too short")
    qfile = str(gold.get("question_file") or "question.txt")
    q_path = root / qfile
    q_text = q_path.read_text(encoding="utf-8").strip() if q_path.is_file() else ""
    return {
        "center_work_id": chain[0],
        "expected_neighbor_work_ids": chain[1:],
        "depth": int(gold.get("depth") or 2),
        "neighbor_limit": int(gold.get("neighbor_limit") or 300),
        "min_precision": float(gold.get("min_precision") or 0.6),
        "min_recall": float(gold.get("min_recall") or 0.5),
        "query_hint": q_text[:500],
    }


def discover_multihop_cases(fixtures_root: Path, *, tier: str) -> list[Path]:
    tiers = _load_tiers(fixtures_root)
    allowed = set(tiers.get(tier) or []) if tiers else None
    out: list[Path] = []
    for child in sorted(fixtures_root.iterdir()):
        if not child.is_dir():
            continue
        has_q_json = (child / "question.json").is_file()
        has_q_txt = (child / "question.txt").is_file()
        if not has_q_json and not has_q_txt:
            continue
        gold_path = child / "gold.json"
        if gold_path.is_file():
            try:
                gmeta = json.loads(gold_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError, TypeError):
                gmeta = {}
            if not isinstance(gmeta, dict):
                gmeta = {}
            if str(gmeta.get("expected_path_kind") or "") == "unordered_set":
                continue
            if not has_q_json and str(gmeta.get("expected_path_kind") or "") != "ordered_chain":
                continue
        elif not has_q_json:
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
    try:
        case = _load_multihop_case_dict(root)
    except (OSError, json.JSONDecodeError, TypeError, ValueError, FileNotFoundError) as exc:
        s = settings or get_settings()
        return {
            "case_id": root.name,
            "query_hint": "",
            "center_work_id": "",
            "depth": 2,
            "neighbor_limit": 300,
            "metrics": {"passed": False, "request_error": str(exc)},
            "returned_neighbor_work_ids": [],
            "wall_clock_seconds": 0.0,
            "run_metadata": benchmark_run_metadata(s),
        }
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
        "multihop_v2_pilot",
        "--tier",
        help="Tier key from case_tiers.json (default: multihop_v2_pilot for multihop_v2 fixtures).",
    ),
    api_base_url: str = typer.Option(
        "http://127.0.0.1:8000",
        "--api-base-url",
        help="Base URL for science-graphrag API (used for /health and graph calls).",
    ),
    timeout_seconds: float = typer.Option(20.0, "--timeout-seconds", help="Per-case HTTP timeout."),
    allow_skip_on_infra: bool = typer.Option(
        False,
        "--allow-skip-on-infra",
        help="If API /health fails, write multihop-skipped-*.json and exit 0 (CI-friendly).",
    ),
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
        ok, detail = check_api_health(api_base_url)
        if not ok:
            skip_path = write_skip_artifact(
                _REPO_ROOT,
                stem="multihop-skipped",
                payload={
                    "reason": "api_health_failed",
                    "detail": detail,
                    "api_base_url": api_base_url,
                    "tier": tier,
                },
            )
            typer.echo(
                f"Multihop suite skipped: API not healthy ({detail}). Wrote {skip_path}",
                err=True,
            )
            raise typer.Exit(0 if allow_skip_on_infra else 2)
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
