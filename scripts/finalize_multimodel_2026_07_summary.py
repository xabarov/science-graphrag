#!/usr/bin/env python3
"""Merge per-model multimodel JSONs under out-dir into one summary.json (3 rows).

Used after a partial run (e.g. Mistral L1/L2+claims done separately; DeepSeek/Kimi via
run_multimodel_benchmark.py). Idempotent: rebuilds summary from on-disk artifacts.

Usage (repo root)::

  .venv/bin/python scripts/finalize_multimodel_2026_07_summary.py \\
    --out-dir eval/results/multimodel-2026-07 \\
    --models mistralai/mistral-small-3.2-24b-instruct,deepseek/deepseek-v3.2,moonshotai/kimi-k2.6
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import typer

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_rmb() -> Any:
    # Register in sys.modules before exec_module: @dataclass needs a resolvable
    # __module__ for string-annotation / KW_ONLY handling in Python 3.12+.
    path = _REPO_ROOT / "scripts" / "run_multimodel_benchmark.py"
    name = "run_multimodel_benchmark"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def main(
    out_dir: Path = typer.Option(
        _REPO_ROOT / "eval/results/multimodel-2026-07",
        "--out-dir",
        exists=False,
        file_okay=False,
        dir_okay=True,
        writable=True,
        resolve_path=True,
    ),
    models: str = typer.Option(
        "mistralai/mistral-small-3.2-24b-instruct,deepseek/deepseek-v3.2,moonshotai/kimi-k2.6",
        "--models",
    ),
    layer1_tier: str = typer.Option("nightly_heavy", "--layer1-tier"),
    layer2_tier: str = typer.Option("nightly_semantic", "--layer2-tier"),
    claims_pilot_tier: str = typer.Option("claims_pilot_v2", "--claims-pilot-tier"),
    claims_holdout_tier: str = typer.Option("claims_holdout_v1", "--claims-holdout-tier"),
) -> None:
    rmb = _load_rmb()
    model_list = [m.strip() for m in models.split(",") if m.strip()]
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for model in model_list:
        slug = rmb._slug_model(model)
        sub = out_dir / slug
        paths = rmb._Paths(
            layer1=sub / f"layer1-{layer1_tier}.json",
            layer2=sub / f"layer2-{layer2_tier}.json",
            claims_pilot=sub / f"claims-paraphrase-{claims_pilot_tier}.json",
            claims_holdout=sub / f"claims-paraphrase-{claims_holdout_tier}.json",
        )
        row: dict[str, Any] = {
            "model": model,
            "slug": slug,
            "layer1_returncode": None,
            "layer2_returncode": None,
            "claims_pilot_returncode": None,
            "claims_holdout_returncode": None,
        }
        if paths.layer1.is_file():
            art = rmb._read_json(paths.layer1)
            row["layer1_failed_count"] = rmb._layer1_failed_count(art)
            row["extraction_llm_model"] = (art.get("run_metadata") or {}).get(
                "extraction_llm_model"
            )
        if paths.layer2.is_file():
            art2 = rmb._read_json(paths.layer2)
            row["layer2_failed_count"] = rmb._layer2_failed_count(art2)
        if paths.claims_pilot.is_file():
            ap = rmb._read_json(paths.claims_pilot)
            row["claims_pilot_mean_recall"] = rmb._mean_paraphrase_recall(ap, "pilot")
        if paths.claims_holdout.is_file():
            ah = rmb._read_json(paths.claims_holdout)
            row["claims_holdout_mean_recall"] = rmb._mean_paraphrase_recall(ah, "holdout")
        rows.append(row)

    summary = {
        "models": model_list,
        "rows": rows,
        "note": "Merged via scripts/finalize_multimodel_2026_07_summary.py from on-disk JSONs.",
    }
    out_json = out_dir / "summary.json"
    out_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    typer.echo(f"Wrote {out_json}")


if __name__ == "__main__":
    typer.run(main)
