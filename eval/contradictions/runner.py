"""CLI: verify or materialize :CONTRADICTS edges for contradictions_v1 gold (BT12)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer

from eval.bench_common import (
    benchmark_run_metadata,
    run_single_case_json_outputs,
    run_suite_cli_flow,
)
from eval.retrieval.work_id_resolve import is_uuid_like, resolve_work_id_from_layer1_slug
from science_graphrag.config import Settings, get_settings
from science_graphrag.storage.neo4j_store import Neo4jGraphStore

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _resolve_work(repo: Path, ref: str, *, settings: Settings) -> str:
    r = str(ref).strip()
    if not r:
        return r
    if is_uuid_like(r):
        return r
    uid = resolve_work_id_from_layer1_slug(repo, r, settings=settings)
    return uid or r


def _load_pair_case(case_dir: Path) -> dict[str, Any]:
    gold = json.loads((case_dir / "gold.json").read_text(encoding="utf-8"))
    if not isinstance(gold, dict):
        raise TypeError("gold.json must be object")
    ca = gold.get("claim_a") or {}
    cb = gold.get("claim_b") or {}
    if not isinstance(ca, dict) or not isinstance(cb, dict):
        raise ValueError("claim_a / claim_b required")
    wa = str(ca.get("corpus_work_id") or "").strip()
    wb = str(cb.get("corpus_work_id") or "").strip()
    if not wa or not wb:
        raise ValueError("corpus_work_id required on claim_a / claim_b")
    subtype = str(gold.get("contradiction_type") or "unspecified").strip()
    return {"work_slug_a": wa, "work_slug_b": wb, "subtype": subtype, "raw": gold}


def run_contradiction_case(
    case_dir: Path | str,
    *,
    settings: Settings | None = None,
    materialize: bool = False,
) -> dict[str, Any]:
    root = Path(case_dir)
    s = settings or get_settings()
    try:
        spec = _load_pair_case(root)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        return {
            "case_id": root.name,
            "metrics": {"passed": False, "error": str(exc)},
            "run_metadata": benchmark_run_metadata(s),
        }
    wa = _resolve_work(_REPO_ROOT, spec["work_slug_a"], settings=s)
    wb = _resolve_work(_REPO_ROOT, spec["work_slug_b"], settings=s)
    neo = Neo4jGraphStore(s.neo4j_uri, s.neo4j_user, s.neo4j_password)
    passed = False
    err: str | None = None
    try:
        if materialize:
            gold = spec.get("raw") or {}
            ca = gold.get("claim_a") or {}
            cb = gold.get("claim_b") or {}
            if not isinstance(ca, dict):
                ca = {}
            if not isinstance(cb, dict):
                cb = {}
            neo.merge_work_contradicts(
                wa,
                wb,
                subtype=spec["subtype"],
                severity=str(gold.get("severity") or "nuanced"),
                rationale_short=str(gold.get("rationale") or ""),
                provenance="benchmark_materialize",
                claim_pair_fingerprint=str(gold.get("pair_id") or ""),
                claim_a_text=str(ca.get("claim_text") or ""),
                claim_b_text=str(cb.get("claim_text") or ""),
                quote_a=str(ca.get("evidence_quote") or ""),
                quote_b=str(cb.get("evidence_quote") or ""),
            )
        lo, hi = (wa, wb) if wa < wb else (wb, wa)
        with neo.session() as session:
            row = session.run(
                """
                MATCH (x:Work {id: $lo})-[r:CONTRADICTS]->(y:Work {id: $hi})
                RETURN count(r) AS c
                """,
                lo=lo,
                hi=hi,
            ).single()
        cnt = int(row["c"]) if row else 0
        passed = cnt >= 1
    except Exception as exc:  # noqa: BLE001
        err = str(exc)
    finally:
        neo.close()
    metrics: dict[str, Any] = {"passed": passed, "materialized": bool(materialize)}
    if err:
        metrics["passed"] = False
        metrics["error"] = err
    return {
        "case_id": root.name,
        "work_id_a": wa,
        "work_id_b": wb,
        "subtype": spec["subtype"],
        "metrics": metrics,
        "run_metadata": benchmark_run_metadata(s),
    }


def discover_contradiction_cases(root: Path) -> list[Path]:
    out: list[Path] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        if (child / "gold.json").is_file():
            out.append(child)
    return out


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
        help="Suite root (directory with pair_* subdirs)",
    ),
    suite: bool = typer.Option(False, "--suite"),
    materialize: bool = typer.Option(
        False,
        "--materialize",
        help="MERGE :CONTRADICTS edges before verification (operator / dev).",
    ),
    json_out: Path | None = typer.Option(None, "--json-out"),
    md_out: Path | None = typer.Option(None, "--md-out"),
) -> None:
    settings = get_settings()

    def _run_one(c: Path) -> dict[str, Any]:
        return run_contradiction_case(c, settings=settings, materialize=materialize)

    if suite:
        cases = discover_contradiction_cases(path)
        if not cases:
            typer.echo(f"No contradiction cases under {path}", err=True)
            raise typer.Exit(code=1)
        payload = run_suite_cli_flow(
            title="Contradictions benchmark (BT12)",
            cases=cases,
            settings=settings,
            run_one=_run_one,
            summarize=_summarize,
            json_out=json_out,
            md_out=md_out,
            summary_from_reports=lambda reports: {
                "all_passed": all(bool((r.get("metrics") or {}).get("passed")) for r in reports),
                "contradictions_eval": True,
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
