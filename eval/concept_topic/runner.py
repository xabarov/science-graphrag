"""CLI + library runner for concept / ResearchTopic benchmark cases (Wave N, advisory)."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from time import perf_counter
from typing import Any

import typer

from eval.bench_common import run_single_case_json_outputs, run_suite_cli_flow
from eval.concept_topic.harness_extract import extract_concepts_topics_anchor_harness
from eval.concept_topic.metrics import score_concept_topic_extraction
from science_graphrag.config import Settings, get_settings


def extract_concepts_topics_production_stub(
    _article: str, _gold: dict[str, Any]
) -> dict[str, Any]:
    """Placeholder until production LLM extractor exists."""

    return {"concepts": [], "topics": []}


def _load_case_tiers(fixtures_root: Path) -> dict[str, list[str]] | None:
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


def _article_path_resolves(case_dir: Path, gold: dict[str, Any]) -> bool:
    ap = gold.get("article_path")
    if not ap:
        return False
    p = (case_dir / str(ap)).resolve()
    return p.is_file()


def discover_concept_topic_case_dirs(
    fixtures_root: Path,
    *,
    tier: str = "concept_topic_merge_contract",
) -> list[Path]:
    """Subdirectories containing ``gold.json`` and either ``article.md`` or resolvable ``article_path``."""

    if not fixtures_root.is_dir():
        return []
    tiers: dict[str, list[str]] | None = _load_case_tiers(fixtures_root)
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
            continue
        if meta.get("skip_in_suite_cli"):
            continue
        has_local_article = (child / "article.md").is_file()
        if not has_local_article and not _article_path_resolves(child, meta):
            continue
        cid = child.name
        if allowed is not None and cid not in allowed:
            continue
        out.append(child)
    return out


def load_article_for_concept_topic_case(case_dir: Path, gold: dict[str, Any]) -> str:
    """Prefer ``article.md`` in case dir; else resolve ``gold['article_path']`` relative to case dir."""

    local = case_dir / "article.md"
    if local.is_file():
        return local.read_text(encoding="utf-8")
    ap = gold.get("article_path")
    if ap:
        path = (case_dir / str(ap)).resolve()
        return path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"No article.md or article_path in {case_dir}")


def run_concept_topic_case(
    case_dir: Path | str,
    *,
    settings: Settings | None = None,
    extract_fn: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run concept/topic extraction for one fixture directory."""

    root = Path(case_dir)
    gold = json.loads((root / "gold.json").read_text(encoding="utf-8"))
    article = load_article_for_concept_topic_case(root, gold)
    s = settings or get_settings()
    fn = extract_fn or extract_concepts_topics_anchor_harness

    started = perf_counter()
    preds = fn(article, gold)
    elapsed = perf_counter() - started
    metrics = score_concept_topic_extraction(preds, gold)
    return {
        "case_id": root.name,
        "metrics": metrics,
        "predictions": preds,
        "wall_clock_seconds": round(elapsed, 3),
        "extractor": getattr(fn, "__name__", str(fn)),
        "extraction_llm_enabled": s.extraction_llm_enabled,
    }


def _report_passed(report: dict[str, Any]) -> bool:
    return bool((report.get("metrics") or {}).get("passed"))


def _summarize(report: dict[str, Any]) -> str:
    cid = report.get("case_id")
    m = report.get("metrics") or {}
    passed = bool(m.get("passed"))
    status = "PASS" if passed else "FAIL"
    return f"## {cid} — {status}\n\n```json\n{json.dumps(m, indent=2)}\n```\n"


def _run_concept_topic_suite(
    path: Path,
    tier: str,
    *,
    settings: Settings,
    run_one: Callable[[Path], dict[str, Any]],
    json_out: Path | None,
    md_out: Path | None,
) -> None:
    tiers_map: dict[str, list[str]] | None = _load_case_tiers(path)
    if tier != "all":
        if tiers_map is None:
            typer.echo(f"No case_tiers.json under {path}", err=True)
            raise typer.Exit(code=1)
        tiers_valid: dict[str, list[str]] = tiers_map
        if tier not in tiers_valid:
            names = ", ".join(sorted(tiers_valid))
            typer.echo(f"Unknown --tier {tier!r}; defined tiers: all, {names}", err=True)
            raise typer.Exit(code=1)
    cases = discover_concept_topic_case_dirs(path, tier=tier)
    if not cases:
        typer.echo(f"No concept/topic cases found under {path}", err=True)
        raise typer.Exit(code=1)
    payload = run_suite_cli_flow(
        title="Concept / ResearchTopic benchmark suite",
        cases=cases,
        settings=settings,
        run_one=run_one,
        summarize=_summarize,
        json_out=json_out,
        md_out=md_out,
        summary_from_reports=lambda reports: {
            "all_passed": all(_report_passed(r) for r in reports),
            "concept_topic_eval": True,
        },
    )
    if not bool(payload.get("summary", {}).get("all_passed", True)):
        raise typer.Exit(code=1)


def _cli(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    path: Path = typer.Argument(
        ...,
        exists=True,
        readable=True,
        help="Case directory or suite root containing case subdirectories",
    ),
    suite: bool = typer.Option(False, "--suite", help="Run all cases under PATH"),
    tier: str = typer.Option(
        "concept_topic_merge_contract",
        "--tier",
        help="Suite tier from case_tiers.json (e.g. concept_topic_merge_contract, concept_topic_mini).",
    ),
    extractor: str = typer.Option(
        "harness",
        "--extractor",
        help='Extractor: "harness" (anchor phrases), "production" (stub; returns empty).',
    ),
    json_out: Path | None = typer.Option(None, "--json-out", help="Write JSON report path"),
    md_out: Path | None = typer.Option(None, "--md-out", help="Write Markdown summary path"),
) -> None:
    settings = get_settings()
    ext = str(extractor or "harness").strip().lower()
    if ext in {"harness", "anchor", "anchor_harness"}:
        extract_fn: Callable[[str, dict[str, Any]], dict[str, Any]] = (
            extract_concepts_topics_anchor_harness
        )
    elif ext in {"production", "prod", "ingestion"}:
        extract_fn = extract_concepts_topics_production_stub
    else:
        typer.echo(f"Unknown --extractor {extractor!r}; use harness or production.", err=True)
        raise typer.Exit(code=1)

    def _run_one(c: Path) -> dict[str, Any]:
        return run_concept_topic_case(c, settings=settings, extract_fn=extract_fn)

    if suite:
        _run_concept_topic_suite(
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
    if not _report_passed(report):
        raise typer.Exit(code=1)


def main() -> None:
    """CLI entry for ``science-graphrag-concept-topic-benchmark``."""

    typer.run(_cli)


if __name__ == "__main__":
    main()
