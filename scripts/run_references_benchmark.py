#!/usr/bin/env python3
"""Run reference localization/segmentation benchmark (levels A/B) across layer-1 fixtures."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import cast

import typer

from eval.references_harness.runner import Mode, run_suite, write_summary
from science_graphrag.config import get_settings

app = typer.Typer(add_completion=False, help="References benchmark harness (ref_gpt5.4_thoughts).")


def _tier_case_ids(tier_key: str) -> list[str]:
    path = Path("tests/fixtures/benchmarks/layer1/case_tiers.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get(tier_key, []))


@app.command()
def main(
    fixture_root: Path = typer.Option(Path("tests/fixtures/benchmarks/layer1")),
    output_dir: Path = typer.Option(Path("eval/results/refs_bench")),
    tier: str = typer.Option(
        "references_benchmark_v1",
        "--tier",
        help="Key in case_tiers.json (e.g. references_benchmark_v1, references_benchmark_full).",
    ),
    modes: str = typer.Option(
        "heuristic_full,heuristic_scope,heuristic_bib_gold",
        help=(
            "Comma-separated: heuristic_full, heuristic_scope, heuristic_bib_gold, "
            "scope_llm, batched_llm"
        ),
    ),
    case_arg: list[str] = typer.Option(
        [],
        "--case",
        help="Restrict to these case ids (repeatable); default: cases from --tier.",
    ),
) -> None:
    """Compare localization/segmentation modes; writes JSON under ``output_dir``."""
    case_ids = case_arg if case_arg else _tier_case_ids(tier)
    if not case_ids:
        raise typer.BadParameter(
            f"No cases: pass --case or add cases to {tier!r} in case_tiers.json",
        )

    parsed_modes = [m.strip() for m in modes.split(",") if m.strip()]
    for m in parsed_modes:
        if m not in (
            "heuristic_full",
            "heuristic_scope",
            "heuristic_bib_gold",
            "scope_llm",
            "batched_llm",
        ):
            raise typer.BadParameter(f"Unknown mode: {m}")

    settings = get_settings()
    t_cli = time.perf_counter()
    by_mode: dict[str, list[dict[str, object]]] = {}
    for mode_str in parsed_modes:
        by_mode[mode_str] = run_suite(
            fixture_root,
            case_ids,
            cast(Mode, mode_str),
            settings=settings,
        )

    cli_s = time.perf_counter() - t_cli
    write_summary(output_dir, by_mode, cli_wall_seconds=cli_s)
    typer.echo(f"Wrote summary to {output_dir / 'refs_bench_summary.json'}")
    typer.echo(f"CLI wall time (all modes, all cases): {cli_s:.1f}s")


if __name__ == "__main__":
    app()
