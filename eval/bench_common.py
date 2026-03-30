"""Shared helpers for multi-case benchmark suites."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import typer

from science_graphrag.config import Settings, get_settings
from science_graphrag.ingestion.llm.stage_extraction import extraction_layer1_prompt_fingerprint


def _tier_case_ids(fixtures_root: Path, tier: str) -> set[str] | None:
    """Return allowed ``case_id`` directory names for ``tier``, or None if no manifest."""

    manifest = fixtures_root / "case_tiers.json"
    if not manifest.is_file():
        return None
    data = json.loads(manifest.read_text(encoding="utf-8"))
    ids = data.get(tier)
    if ids is None:
        return None
    return {str(x) for x in ids}


def discover_layer1_case_dirs(
    fixtures_root: Path,
    *,
    tier: str | None = None,
) -> list[Path]:
    """Subdirectories of ``fixtures_root`` that contain ``article.md`` and ``gold.json``."""

    if not fixtures_root.is_dir():
        return []
    found: list[Path] = []
    for child in sorted(fixtures_root.iterdir()):
        if not child.is_dir():
            continue
        if (child / "article.md").is_file() and (child / "gold.json").is_file():
            found.append(child)
    if tier:
        allowed = _tier_case_ids(fixtures_root, tier)
        if allowed is not None:
            found = [p for p in found if p.name in allowed]
    return found


def benchmark_run_metadata(settings: Settings | None = None) -> dict[str, Any]:
    """Model + prompt fingerprint for reproducible benchmark reports."""

    s = settings or get_settings()
    return {
        "extraction_llm_enabled": s.extraction_llm_enabled,
        "extraction_llm_model": s.extraction_llm_model,
        "extraction_llm_base_url": s.extraction_llm_base_url,
        "layer1_prompt_fingerprint": extraction_layer1_prompt_fingerprint(),
    }


def suite_summary_counts(case_reports: list[dict[str, Any]]) -> dict[str, Any]:
    """Minimal cross-case counters for JSON suite reports."""

    return {
        "case_count": len(case_reports),
        "case_ids": [r.get("case_id") for r in case_reports],
    }


def run_suite_cli_flow(
    *,
    title: str,
    cases: list[Path],
    settings: Settings,
    run_one: Callable[[Path], dict[str, Any]],
    summarize: Callable[[dict[str, Any]], str],
    json_out: Path | None,
    md_out: Path | None,
) -> None:
    """Echo Markdown, optionally write JSON/Markdown suite artifacts (Typer CLI)."""

    reports = [run_one(case_path) for case_path in cases]
    payload: dict[str, Any] = {
        "run_metadata": benchmark_run_metadata(settings),
        "summary": suite_summary_counts(reports),
        "cases": reports,
    }
    md_body = "\n\n---\n\n".join(summarize(r) for r in reports)
    md_full = (
        f"# {title}\n\n"
        f"Cases: {len(reports)}\n\n"
        f"Model: {payload['run_metadata']['extraction_llm_model']}\n"
        f"Prompt fingerprint: {payload['run_metadata']['layer1_prompt_fingerprint']}\n\n" + md_body
    )
    typer.echo(md_full)
    if json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        typer.echo(f"Wrote JSON suite report to {json_out}", err=True)
    if md_out:
        md_out.parent.mkdir(parents=True, exist_ok=True)
        md_out.write_text(md_full, encoding="utf-8")
        typer.echo(f"Wrote Markdown suite summary to {md_out}", err=True)


def run_single_case_json_outputs(
    *,
    report: dict[str, Any],
    settings: Settings,
    summarize: Callable[[dict[str, Any]], str],
    json_out: Path | None,
    md_out: Path | None,
) -> None:
    """Write optional JSON (wrapped) / Markdown for one benchmark case."""

    typer.echo(summarize(report))
    if json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        wrapped = {"run_metadata": benchmark_run_metadata(settings), "case": report}
        json_out.write_text(json.dumps(wrapped, indent=2, ensure_ascii=False), encoding="utf-8")
        typer.echo(f"Wrote JSON report to {json_out}", err=True)
    if md_out:
        md_out.parent.mkdir(parents=True, exist_ok=True)
        md_out.write_text(summarize(report), encoding="utf-8")
        typer.echo(f"Wrote Markdown summary to {md_out}", err=True)
