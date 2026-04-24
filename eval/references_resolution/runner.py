"""CLI + library runner for references_resolution benchmark (v1 harness, advisory)."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from time import perf_counter
from typing import Any

import typer

from eval.bench_common import run_single_case_json_outputs, run_suite_cli_flow
from eval.references_resolution.graph_resolver import graph_resolve_predictions
from eval.references_resolution.metrics import score_references_resolution
from science_graphrag.config import Settings, get_settings
from science_graphrag.storage.neo4j_store import Neo4jGraphStore


def _load_refs_case_tiers(fixtures_root: Path) -> dict[str, list[str]] | None:
    path = fixtures_root / "case_tiers.json"
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return None
    if not isinstance(raw, dict):
        return None
    out: dict[str, list[str]] = {}
    for key, val in raw.items():
        if isinstance(val, list):
            out[str(key)] = [str(x) for x in val]
    return out or None


def discover_references_resolution_case_dirs(
    fixtures_root: Path,
    *,
    tier: str = "refs_merge_contract",
) -> list[Path]:
    """Subdirectories containing ``gold.json``."""

    if not fixtures_root.is_dir():
        return []
    tiers: dict[str, list[str]] | None = _load_refs_case_tiers(fixtures_root)
    allowed: set[str] | None
    if tier == "all":
        allowed = None
    elif tiers is not None:
        tier_ids = tiers.get(tier)
        if tier_ids is None:
            return []
        allowed = set(tier_ids)
    else:
        allowed = None

    out: list[Path] = []
    for child in sorted(fixtures_root.iterdir()):
        if not child.is_dir():
            continue
        gold_path = child / "gold.json"
        if not gold_path.is_file():
            continue
        try:
            meta = json.loads(gold_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            meta = {}
        if meta.get("skip_in_suite_cli"):
            continue
        cid = child.name
        if allowed is not None and cid not in allowed:
            continue
        out.append(child)
    return out


def default_resolve_predictions_graph_stub(
    _unused_case_dir: Path,
    gold: dict[str, Any],
) -> list[dict[str, Any]]:
    """Prefer ``graph_stub_predictions`` (placeholder Neo4j lane); else synthetic harness."""

    gp = gold.get("graph_stub_predictions")
    if isinstance(gp, list):
        return [dict(x) for x in gp if isinstance(x, dict)]
    return default_resolve_predictions(_unused_case_dir, gold)


def default_resolve_predictions(
    _unused_case_dir: Path,
    gold: dict[str, Any],
) -> list[dict[str, Any]]:
    """Load deterministic predictions for CI harness runs.

    Priority:
    1. ``gold['synthetic_predictions']`` when present (list of dicts).
    2. Empty list.
    """

    sp = gold.get("synthetic_predictions")
    if isinstance(sp, list):
        return [dict(x) for x in sp if isinstance(x, dict)]
    return []


def resolve_predictions_use_expected(
    _unused_case_dir: Path,
    gold: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return gold expected rows as predictions (smoke / golden path)."""

    rows = gold.get("expected_resolutions")
    if not isinstance(rows, list):
        return []
    return [dict(x) for x in rows if isinstance(x, dict)]


def run_references_resolution_case(
    case_dir: Path | str,
    *,
    settings: Settings | None = None,
    resolve_fn: Callable[[Path, dict[str, Any]], list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Run references resolution scoring for one fixture directory."""

    root = Path(case_dir)
    gold = json.loads((root / "gold.json").read_text(encoding="utf-8"))
    s = settings or get_settings()
    fn = resolve_fn or default_resolve_predictions

    started = perf_counter()
    preds = fn(root, gold)
    elapsed = perf_counter() - started
    metrics = score_references_resolution(preds, gold)
    return {
        "case_id": root.name,
        "metrics": metrics,
        "predictions": preds,
        "wall_clock_seconds": round(elapsed, 3),
        "resolver": getattr(fn, "__name__", str(fn)),
        "resolver_mode": getattr(fn, "_resolver_mode_label", None),
        "extraction_llm_enabled": s.extraction_llm_enabled,
    }


def _refs_report_passed(report: dict[str, Any]) -> bool:
    return bool((report.get("metrics") or {}).get("passed"))


def _summarize(report: dict[str, Any]) -> str:
    cid = report.get("case_id")
    passed = bool((report.get("metrics") or {}).get("passed"))
    status = "PASS" if passed else "FAIL"
    return f"## {cid} — {status}\n\n```json\n{json.dumps(report.get('metrics'), indent=2)}\n```\n"


def _run_refs_suite(  # pylint: disable=too-many-arguments
    path: Path,
    tier: str,
    *,
    settings: Settings,
    run_one: Callable[[Path], dict[str, Any]],
    json_out: Path | None,
    md_out: Path | None,
) -> None:
    tiers_map: dict[str, list[str]] | None = _load_refs_case_tiers(path)
    if tier != "all":
        if tiers_map is None:
            typer.echo(f"No case_tiers.json under {path}", err=True)
            raise typer.Exit(code=1)
        manifest: dict[str, list[str]] = tiers_map
        if manifest.get(tier) is None:
            names = ", ".join(sorted(manifest))
            typer.echo(f"Unknown --tier {tier!r}; defined tiers: all, {names}", err=True)
            raise typer.Exit(code=1)
    cases = discover_references_resolution_case_dirs(path, tier=tier)
    if not cases:
        typer.echo(f"No references_resolution cases found under {path}", err=True)
        raise typer.Exit(code=1)
    payload = run_suite_cli_flow(
        title="References resolution benchmark suite",
        cases=cases,
        settings=settings,
        run_one=run_one,
        summarize=_summarize,
        json_out=json_out,
        md_out=md_out,
        summary_from_reports=lambda reports: {
            "all_passed": all(_refs_report_passed(r) for r in reports),
            "references_resolution_eval": True,
        },
    )
    if not bool(payload.get("summary", {}).get("all_passed", True)):
        raise typer.Exit(code=1)


def _wrap_graph_resolver(settings: Settings) -> Callable[[Path, dict[str, Any]], list[dict[str, Any]]]:
    def _fn(_case_dir: Path, gold: dict[str, Any]) -> list[dict[str, Any]]:
        store = Neo4jGraphStore(
            settings.neo4j_uri,
            settings.neo4j_user,
            settings.neo4j_password,
        )
        try:
            return graph_resolve_predictions(gold, store)
        finally:
            store.close()

    _fn._resolver_mode_label = "graph"  # type: ignore[attr-defined]
    return _fn


def _cli(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    path: Path = typer.Argument(
        ...,
        exists=True,
        readable=True,
        help="Case directory or suite root containing case subdirectories",
    ),
    suite: bool = typer.Option(False, "--suite", help="Run all cases under PATH"),
    tier: str = typer.Option(
        "refs_merge_contract",
        "--tier",
        help="Suite tier from case_tiers.json (e.g. refs_merge_contract, refs_mini).",
    ),
    use_expected: bool = typer.Option(
        False,
        "--use-expected",
        help="Use gold expected_resolutions as predictions (golden-path smoke).",
    ),
    resolver: str = typer.Option(
        "synthetic",
        "--resolver",
        help="Prediction source: synthetic | graph_stub | graph (Neo4j; needs live stack).",
    ),
    graph_stub_lane: bool = typer.Option(
        False,
        "--graph-stub-lane",
        help="Deprecated: same as --resolver graph_stub.",
    ),
    json_out: Path | None = typer.Option(None, "--json-out", help="Write JSON report path"),
    md_out: Path | None = typer.Option(None, "--md-out", help="Write Markdown summary path"),
) -> None:
    settings = get_settings()
    eff_resolver = resolver.strip().lower() if resolver else "synthetic"
    if graph_stub_lane:
        if eff_resolver not in ("synthetic", "graph_stub"):
            typer.echo("Do not combine --graph-stub-lane with a different --resolver", err=True)
            raise typer.Exit(code=1)
        eff_resolver = "graph_stub"
    if eff_resolver not in ("synthetic", "graph_stub", "graph"):
        typer.echo(
            f"Unknown --resolver {eff_resolver!r}; expected synthetic|graph_stub|graph",
            err=True,
        )
        raise typer.Exit(code=1)
    resolve_fn: Callable[[Path, dict[str, Any]], list[dict[str, Any]]]
    if use_expected:
        resolve_fn = resolve_predictions_use_expected
        resolve_fn._resolver_mode_label = "use_expected"  # type: ignore[attr-defined]
    elif eff_resolver == "graph_stub":
        resolve_fn = default_resolve_predictions_graph_stub
        resolve_fn._resolver_mode_label = "graph_stub"  # type: ignore[attr-defined]
    elif eff_resolver == "graph":
        resolve_fn = _wrap_graph_resolver(settings)
    else:
        resolve_fn = default_resolve_predictions
        resolve_fn._resolver_mode_label = "synthetic"  # type: ignore[attr-defined]

    def _run_one(c: Path) -> dict[str, Any]:
        return run_references_resolution_case(c, settings=settings, resolve_fn=resolve_fn)

    if suite:
        _run_refs_suite(
            path,
            tier,
            settings=settings,
            run_one=_run_one,
            json_out=json_out,
            md_out=md_out,
        )
        return

    report = _run_one(path)
    run_single_case_json_outputs(
        report=report,
        settings=settings,
        summarize=_summarize,
        json_out=json_out,
        md_out=md_out,
    )
    if not _refs_report_passed(report):
        raise typer.Exit(code=1)


def main() -> None:
    """CLI entry for ``science-graphrag-references-resolution-benchmark``."""

    typer.run(_cli)


if __name__ == "__main__":
    main()
