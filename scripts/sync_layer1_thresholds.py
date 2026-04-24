#!/usr/bin/env python3
"""
Merge Wave M ``quality_thresholds`` into layer-1 benchmark ``gold.json`` files.

Reads ``tests/fixtures/benchmarks/layer1/case_tiers.json`` and updates per-case
``quality_thresholds`` with backbone tightening defaults (see Wave M roadmap).

Usage (repo root):

  .venv/bin/python scripts/sync_layer1_thresholds.py --dry-run --tier nightly_heavy
  .venv/bin/python scripts/sync_layer1_thresholds.py --tier merge_safe
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CASE_TIERS = ROOT / "tests/fixtures/benchmarks/layer1/case_tiers.json"
LAYER1_ROOT = ROOT / "tests/fixtures/benchmarks/layer1"

# Wave M defaults embedded in gold for transparency in benchmark JSON reports.
WAVE_M_QUALITY_THRESHOLDS: dict[str, Any] = {
    "require_reference_count_ok": False,
    "reference_count_range_factor": 0.3,
    "min_authorship_names_f1": 0.7,
    "min_sample_arxiv_f1": 0.85,
    "require_abstract_prefix": False,
    "min_abstract_prefix_containment": 0.7,
}


def _tier_case_ids(tier: str, tiers: dict[str, Any]) -> list[str]:
    if tier == "all":
        out: set[str] = set()
        for key, val in tiers.items():
            if key == "description" or not isinstance(val, list):
                continue
            out.update(str(x) for x in val)
        return sorted(out)
    raw = tiers.get(tier)
    if not isinstance(raw, list):
        return []
    return [str(x) for x in raw]


def _merge_thresholds(existing: dict[str, Any] | None) -> dict[str, Any]:
    merged = dict(existing or {})
    merged.update(WAVE_M_QUALITY_THRESHOLDS)
    return merged


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tier",
        choices=["nightly_heavy", "merge_safe", "all"],
        default="nightly_heavy",
        help="Which tier from case_tiers.json to update (default: nightly_heavy).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print paths that would change without writing files.",
    )
    args = parser.parse_args()

    tiers = json.loads(CASE_TIERS.read_text(encoding="utf-8"))
    case_ids = _tier_case_ids(args.tier, tiers)
    if not case_ids:
        print(f"No case ids for tier {args.tier!r}", flush=True)
        return 1

    changed = 0
    for cid in case_ids:
        path = LAYER1_ROOT / cid / "gold.json"
        if not path.is_file():
            print(f"skip missing {path}", flush=True)
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        before = json.dumps(data.get("quality_thresholds"), sort_keys=True)
        data["quality_thresholds"] = _merge_thresholds(
            data.get("quality_thresholds") if isinstance(data.get("quality_thresholds"), dict) else None,
        )
        after = json.dumps(data["quality_thresholds"], sort_keys=True)
        if before == after:
            print(f"unchanged {cid}", flush=True)
            continue
        print(f"update {cid}", flush=True)
        changed += 1
        if not args.dry_run:
            path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

    print(f"done: {changed} file(s) {'would be ' if args.dry_run else ''}updated", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
