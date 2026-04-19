#!/usr/bin/env python3
"""
Run layer-1 extraction with the teacher LLM and write gold_teacher.json per case.

Uses the same extraction stages as production (`extract_stages_llm_first`).
Defaults: DeepSeek via OpenRouter-style env/CLI; else benchmark_teacher_* then extraction_llm_*.

Example:
  .venv/bin/python scripts/generate_teacher_layer1_gold.py \\
    --fixtures-root tests/fixtures/benchmarks/layer1 \\
    --out-root eval/teacher_gold/layer1 \\
    --tier nightly_heavy \\
    --model deepseek/deepseek-v3.2

Or set SCIENCE_GRAPHRAG_BENCHMARK_TEACHER_LLM_API_KEY / _BASE_URL / _MODEL in .env.

Provenance / when to run vs extractor triage: see ``eval/README.md`` section *Teacher-gold remediation*.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from teacher_llm_settings import teacher_extraction_settings

from eval.bench_common import discover_layer1_case_dirs
from eval.layer1.runner import run_layer1_extraction_only
from eval.layer1.spec import Layer1GoldSpec
from eval.layer1.teacher_gold import (
    layer1_spec_from_teacher_drafts,
    teacher_run_manifest,
    write_teacher_gold_bundle,
)
from science_graphrag.config import get_settings


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate teacher layer-1 gold JSON files.")
    p.add_argument(
        "--fixtures-root",
        type=Path,
        default=ROOT / "tests/fixtures/benchmarks/layer1",
        help="Layer-1 benchmark root",
    )
    p.add_argument(
        "--out-root",
        type=Path,
        default=ROOT / "eval/teacher_gold/layer1",
        help="Output directory (one subdir per case_id)",
    )
    p.add_argument("--tier", type=str, default=None, help="Filter by case_tiers.json tier")
    p.add_argument(
        "--no-inherit-graph",
        action="store_true",
        help="Do not copy graph_expectations from curated gold.json",
    )
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--api-key", type=str, default=None)
    p.add_argument("--base-url", type=str, default=None)
    p.add_argument("--model", type=str, default=None)
    return p.parse_args()


def main() -> int:
    """Generate teacher gold files and a suite manifest under ``--out-root``."""

    args = _parse_args()
    base = get_settings()
    settings = teacher_extraction_settings(base, args)
    if not settings.extraction_llm_api_key:
        print(
            "error: no API key (use --api-key or "
            "SCIENCE_GRAPHRAG_BENCHMARK_TEACHER_LLM_API_KEY / MAIN_LLM_API_KEY)",
            file=sys.stderr,
        )
        return 1

    cases = discover_layer1_case_dirs(args.fixtures_root, tier=args.tier)
    if not cases:
        print("no cases found", file=sys.stderr)
        return 1

    if args.dry_run:
        for c in cases:
            print(f"would process {c.name}")
        return 0

    done: list[str] = []
    for case_dir in cases:
        curated = Layer1GoldSpec.load(case_dir / "gold.json")
        inherit = None if args.no_inherit_graph else curated
        work, authorships, references, diag = run_layer1_extraction_only(
            case_dir, settings=settings
        )
        spec = layer1_spec_from_teacher_drafts(
            curated.case_id,
            work,
            authorships,
            references,
            inherit_graph_from=inherit,
            teacher_model=settings.extraction_llm_model,
            teacher_base_url=settings.extraction_llm_base_url,
            include_student_thresholds=True,
        )
        out_dir = args.out_root / case_dir.name
        out_path = out_dir / "gold_teacher.json"
        write_teacher_gold_bundle(out_path, spec, manifest=None)
        done.append(curated.case_id)
        srcs = f"{diag.metadata_source}/{diag.authorships_source}/{diag.references_source}"
        print(f"wrote {out_path} ({srcs})")

    manifest = teacher_run_manifest(
        teacher_model=settings.extraction_llm_model,
        teacher_base_url=settings.extraction_llm_base_url,
        cases=done,
        extraction_llm_enabled=True,
    )
    args.out_root.mkdir(parents=True, exist_ok=True)
    (args.out_root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
