#!/usr/bin/env python3
"""
Run semantic Method/Dataset extraction with the teacher LLM and write semantic_gold_teacher.json.

Reads each layer-2 case's semantic_gold.json for article_path and case_id, runs
``extract_semantic_method_dataset`` with teacher credentials (same resolution as
``generate_teacher_layer1_gold.py``), and writes expected_method/dataset names from the
teacher prediction (normalized) plus relaxed recall ratios for student evaluation.

Usage:
  .venv/bin/python scripts/generate_semantic_teacher_fixtures.py \\
    --fixtures-root tests/fixtures/benchmarks/layer2 \\
    --out-root eval/teacher_gold/layer2 \\
    --tier nightly_semantic

Provenance / when to run vs extractor triage: see ``eval/README.md`` section *Teacher-gold remediation*
(mirror commit message fields with layer-1 teacher refresh).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from teacher_llm_settings import teacher_extraction_settings

from eval.bench_common import discover_layer2_case_dirs
from eval.layer2.metrics import load_article_for_case
from eval.layer2.spec import SemanticGoldSpec
from science_graphrag.config import get_settings
from science_graphrag.ingestion.document_slices import strip_repeated_boilerplate
from science_graphrag.ingestion.llm.semantic_extraction import extract_semantic_method_dataset
from science_graphrag.ingestion.normalize import normalize_text
from science_graphrag.observability.phoenix_tracer import chain_span, init_tracer_provider


def _norm_name(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate teacher semantic gold JSON files.")
    p.add_argument(
        "--fixtures-root",
        type=Path,
        default=ROOT / "tests/fixtures/benchmarks/layer2",
    )
    p.add_argument(
        "--out-root",
        type=Path,
        default=ROOT / "eval/teacher_gold/layer2",
    )
    p.add_argument("--tier", type=str, default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--api-key", type=str, default=None)
    p.add_argument("--base-url", type=str, default=None)
    p.add_argument("--model", type=str, default=None)
    p.add_argument(
        "--confidence",
        type=float,
        default=0.35,
        help="Min confidence to include predicted method/dataset names in gold",
    )
    return p.parse_args()


def _names_from_pred(pred, conf: float) -> tuple[list[str], list[str]]:
    methods: list[str] = []
    seen_m: set[str] = set()
    for m in pred.methods:
        if m.confidence < conf:
            continue
        for label in [m.name, *m.aliases]:
            if not label or not str(label).strip():
                continue
            n = _norm_name(str(label))
            if n and n not in seen_m:
                seen_m.add(n)
                methods.append(n)
    datasets: list[str] = []
    seen_d: set[str] = set()
    for d in pred.datasets:
        if d.confidence < conf:
            continue
        for label in [d.name, *d.aliases]:
            if not label or not str(label).strip():
                continue
            n = _norm_name(str(label))
            if n and n not in seen_d:
                seen_d.add(n)
                datasets.append(n)
    return methods, datasets


def main() -> int:
    """Write ``semantic_gold_teacher.json`` per layer-2 case and a manifest."""

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

    cases = discover_layer2_case_dirs(args.fixtures_root, tier=args.tier)
    if not cases:
        print("no cases found", file=sys.stderr)
        return 1

    if args.dry_run:
        for c in cases:
            print(f"would process {c.name}")
        return 0

    init_tracer_provider()
    done: list[str] = []
    for case_dir in cases:
        base_gold = SemanticGoldSpec.load(case_dir / "semantic_gold.json")
        text = load_article_for_case(case_dir, base_gold)
        normalized = strip_repeated_boilerplate(normalize_text(text))
        with chain_span(
            "semantic_teacher_fixture",
            {"case_id": base_gold.case_id, "source": "generate_semantic_teacher"},
        ):
            pred = extract_semantic_method_dataset(
                normalized,
                settings,
                document_id=base_gold.case_id,
            )
        methods, datasets = _names_from_pred(pred, args.confidence)
        spec = {
            "case_id": base_gold.case_id,
            "schema_version": 1,
            "description": (
                f"Teacher semantic gold from model={settings.extraction_llm_model}; "
                f"see eval/teacher_gold/layer2/manifest.json"
            ),
            "article_path": base_gold.article_path,
            "min_method_names": 1 if methods else 0,
            "expected_method_names_normalized": methods,
            "expected_dataset_names_normalized": datasets,
            "allow_empty_when_no_llm": True,
            "min_method_recall_ratio": 0.4 if methods else None,
            "min_dataset_recall_ratio": 0.35 if datasets else None,
        }
        out_dir = args.out_root / case_dir.name
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "semantic_gold_teacher.json"
        out_path.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        done.append(base_gold.case_id)
        print(f"wrote {out_path} (methods={len(methods)} datasets={len(datasets)})")

    manifest = {
        "schema_version": 1,
        "teacher_model": settings.extraction_llm_model,
        "teacher_base_url": settings.extraction_llm_base_url,
        "case_ids": done,
    }
    args.out_root.mkdir(parents=True, exist_ok=True)
    (args.out_root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
