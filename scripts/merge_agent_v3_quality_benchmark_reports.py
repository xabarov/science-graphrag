#!/usr/bin/env python3
"""Merge single-case ``agent-v3-quality-judge-v1`` JSON reports into one suite artifact.

Use when the benchmark CLI was invoked once per ``--case`` (e.g. Wave D calibration
window) and you need a single JSON with combined ``cases`` + ``summarize_suite``.

Example (R5 Phase A / Phase C per-case outputs):

  .venv/bin/python scripts/merge_agent_v3_quality_benchmark_reports.py \\
    --inputs eval/results/r5-phase-a-part-mini_workspace_stats_01.json \\
            eval/results/r5-phase-a-part-mini_catalog_resolution_01.json \\
    --out-json eval/results/merged.json

Or glob:

  .venv/bin/python scripts/merge_agent_v3_quality_benchmark_reports.py \\
    --glob 'eval/results/r5-phase-c-multiseed-part-*-2026-05-13.json' \\
    --out-json eval/results/r5-phase-c-calibration-window-multiseed-mock-combined-2026-05-13.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from eval.agent_v3_quality.judge_metrics import cost_delta_from_cases, summarize_suite  # noqa: E402


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _merge_payloads(paths: list[Path]) -> dict[str, Any]:
    if not paths:
        raise ValueError("no input paths")
    payloads = [_load_json(p) for p in paths]
    rv = str(payloads[0].get("review_version") or "").strip()
    for p, pl in zip(paths, payloads, strict=True):
        if str(pl.get("review_version") or "").strip() != rv:
            raise ValueError(f"review_version mismatch: {p} vs first input")
    cases: list[dict[str, Any]] = []
    for pl in payloads:
        raw = pl.get("cases")
        if not isinstance(raw, list) or not raw:
            raise ValueError("each input must have non-empty cases[]")
        cases.extend(raw)
    base = dict(payloads[0])
    base["cases"] = cases
    summary = summarize_suite(cases)
    summary["cost_delta"] = cost_delta_from_cases(cases)
    base["summary"] = summary
    base["run_metadata"] = dict(base.get("run_metadata") or {})
    base["run_metadata"]["merge_source_reports"] = [str(p.relative_to(REPO_ROOT)) for p in paths]
    base["run_metadata"]["merged_case_count"] = len(cases)
    return base


def main() -> int:
    """CLI entry: merge reports and write ``--out-json``."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--inputs",
        nargs="+",
        type=Path,
        help="Explicit JSON paths (order preserved).",
    )
    parser.add_argument(
        "--glob",
        type=str,
        default=None,
        help="Glob relative to repo root (sorted).",
    )
    parser.add_argument(
        "--out-json",
        type=Path,
        required=True,
        help="Output merged JSON path.",
    )
    args = parser.parse_args()
    if bool(args.inputs) == bool(args.glob):
        parser.error("Specify exactly one of --inputs or --glob")

    if args.glob:
        paths = sorted(REPO_ROOT.glob(args.glob))
    else:
        paths = [(REPO_ROOT / p) if not p.is_absolute() else p for p in args.inputs]
    paths = [p for p in paths if p.is_file()]
    if not paths:
        parser.error("no files matched")

    out = _merge_payloads(paths)
    out_path = REPO_ROOT / args.out_json if not args.out_json.is_absolute() else args.out_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {out_path} ({len(out.get('cases') or [])} cases)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
