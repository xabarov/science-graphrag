#!/usr/bin/env python3
"""Run Layer-1, Layer-2, and claims paraphrase benchmarks for multiple LLMs and aggregate.

Sets MAIN_LLM_MODEL (and mirrors to extraction) per model slug, invokes console scripts
via subprocess, writes JSON per model, and a summary table JSON.

Usage (from repo root, with API keys in env / .env)::

  .venv/bin/python scripts/run_multimodel_benchmark.py \\
    --models model-a,model-b,model-c \\
    --out-dir eval/results/multimodel
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import typer

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _slug_model(model: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9._-]+", "_", model.strip()).strip("_")
    return s or "model"


def _read_json(p: Path) -> dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def _layer1_failed_count(artifact: dict[str, Any]) -> int:
    n = 0
    for c in artifact.get("cases") or []:
        m = c.get("metrics") if isinstance(c, dict) else None
        if not isinstance(m, dict):
            continue
        contract = m.get("contract")
        if isinstance(contract, dict) and not bool(contract.get("passed", True)):
            n += 1
    return n


def _layer2_failed_count(artifact: dict[str, Any]) -> int:
    n = 0
    for c in artifact.get("cases") or []:
        m = c.get("metrics") if isinstance(c, dict) else None
        if not isinstance(m, dict):
            continue
        if "passed" in m and not bool(m.get("passed", True)):
            n += 1
    return n


def _mean_paraphrase_recall(artifact: dict[str, Any], split: str) -> float | None:
    """``split`` is ``pilot`` or ``holdout`` based on case_id or tier in artifact."""

    by_case: list[float] = []
    for c in artifact.get("cases") or []:
        cid = str(c.get("case_id") or "")
        m = c.get("metrics") if isinstance(c, dict) else None
        if not isinstance(m, dict):
            continue
        is_holdout = "holdout" in cid.lower()
        if split == "holdout" and not is_holdout:
            continue
        if split == "pilot" and is_holdout:
            continue
        r = m.get("claim_recall")
        if isinstance(r, (int, float)):
            by_case.append(float(r))
    if not by_case:
        return None
    return sum(by_case) / len(by_case)


@dataclass
class _Paths:
    layer1: Path
    layer2: Path
    claims_pilot: Path
    claims_holdout: Path


def main(  # pylint: disable=too-many-locals,too-many-arguments,too-many-positional-arguments
    models: str = typer.Option(
        ...,
        "--models",
        help="Comma-separated OpenRouter model ids (3 recommended).",
    ),
    out_dir: Path = typer.Option(
        _REPO_ROOT / "eval/results/multimodel",
        "--out-dir",
        help="Output directory for per-model JSON and summary.",
    ),
    layer1_tier: str = typer.Option("nightly_heavy", "--layer1-tier"),
    layer2_tier: str = typer.Option("nightly_semantic", "--layer2-tier"),
    claims_pilot_tier: str = typer.Option("claims_pilot_v2", "--claims-pilot-tier"),
    claims_holdout_tier: str = typer.Option("claims_holdout_v1", "--claims-holdout-tier"),
    layer1_root: Path = typer.Option(
        _REPO_ROOT / "tests/fixtures/benchmarks/layer1",
        "--layer1-root",
    ),
    layer2_root: Path = typer.Option(
        _REPO_ROOT / "tests/fixtures/benchmarks/layer2",
        "--layer2-root",
    ),
    claims_root: Path = typer.Option(
        _REPO_ROOT / "tests/fixtures/benchmarks/claims",
        "--claims-root",
    ),
) -> None:
    """Run multi-model L1, L2, and claims paraphrase benchmarks; write ``summary.json``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    model_list = [m.strip() for m in models.split(",") if m.strip()]
    if len(model_list) < 1:
        typer.echo("Pass at least one model in --models", err=True)
        raise typer.Exit(code=1)

    venv_bin = _REPO_ROOT / ".venv" / "bin"
    l1_cmd = (
        venv_bin / "science-graphrag-layer1-benchmark"
        if (venv_bin / "science-graphrag-layer1-benchmark").is_file()
        else None
    )
    l2_cmd = (
        venv_bin / "science-graphrag-layer2-benchmark"
        if (venv_bin / "science-graphrag-layer2-benchmark").is_file()
        else None
    )
    cl_cmd = (
        venv_bin / "science-graphrag-claims-paraphrase-benchmark"
        if (venv_bin / "science-graphrag-claims-paraphrase-benchmark").is_file()
        else None
    )
    if l1_cmd is None or l2_cmd is None or cl_cmd is None:
        typer.echo(
            "Install package in venv: pip install -e . (console scripts not found).",
            err=True,
        )
        raise typer.Exit(code=1)

    rows: list[dict[str, Any]] = []
    for model in model_list:
        slug = _slug_model(model)
        sub = out_dir / slug
        sub.mkdir(parents=True, exist_ok=True)
        sub_env = {**os.environ, "MAIN_LLM_MODEL": model}
        if (
            not sub_env.get("MAIN_LLM_API_KEY")
            and not sub_env.get("OPENROUTER_API_KEY")
            and not sub_env.get("API_KEY")
        ):
            typer.echo(
                "Warning: MAIN_LLM_API_KEY / OPENROUTER_API_KEY / API_KEY not set; runs may fail.",
                err=True,
            )

        paths = _Paths(
            layer1=sub / f"layer1-{layer1_tier}.json",
            layer2=sub / f"layer2-{layer2_tier}.json",
            claims_pilot=sub / f"claims-paraphrase-{claims_pilot_tier}.json",
            claims_holdout=sub / f"claims-paraphrase-{claims_holdout_tier}.json",
        )

        def _run(argv: list[str]) -> int:
            r = subprocess.run(
                argv,
                cwd=str(_REPO_ROOT),
                env=sub_env,
                check=False,
            )
            return int(r.returncode)

        l1 = _run(
            [
                str(l1_cmd),
                str(layer1_root),
                "--suite",
                "--tier",
                layer1_tier,
                "--threshold-profile",
                "reporting_skip_f1_gates",
                "--json-out",
                str(paths.layer1),
            ],
        )
        l2 = _run(
            [
                str(l2_cmd),
                str(layer2_root),
                "--suite",
                "--tier",
                layer2_tier,
                "--json-out",
                str(paths.layer2),
            ],
        )
        cp = _run(
            [
                str(cl_cmd),
                str(claims_root),
                "--suite",
                "--tier",
                claims_pilot_tier,
                "--json-out",
                str(paths.claims_pilot),
            ],
        )
        ch = _run(
            [
                str(cl_cmd),
                str(claims_root),
                "--suite",
                "--tier",
                claims_holdout_tier,
                "--json-out",
                str(paths.claims_holdout),
            ],
        )

        row: dict[str, Any] = {
            "model": model,
            "slug": slug,
            "layer1_returncode": l1,
            "layer2_returncode": l2,
            "claims_pilot_returncode": cp,
            "claims_holdout_returncode": ch,
        }
        if paths.layer1.is_file():
            art = _read_json(paths.layer1)
            row["layer1_failed_count"] = _layer1_failed_count(art)
            row["extraction_llm_model"] = (art.get("run_metadata") or {}).get(
                "extraction_llm_model"
            )
        if paths.layer2.is_file():
            art2 = _read_json(paths.layer2)
            row["layer2_failed_count"] = _layer2_failed_count(art2)
        if paths.claims_pilot.is_file():
            ap = _read_json(paths.claims_pilot)
            row["claims_pilot_mean_recall"] = _mean_paraphrase_recall(ap, "pilot")
        if paths.claims_holdout.is_file():
            ah = _read_json(paths.claims_holdout)
            row["claims_holdout_mean_recall"] = _mean_paraphrase_recall(ah, "holdout")

        rows.append(row)

    summary = {
        "models": model_list,
        "rows": rows,
        "note": "Per-model JSONs live next to this file under <slug>/.",
    }
    out_json = out_dir / "summary.json"
    out_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    typer.echo(f"Wrote {out_json}")


if __name__ == "__main__":
    typer.run(main)
