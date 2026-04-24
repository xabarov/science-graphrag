#!/usr/bin/env python3
"""
Sync Wave M quality_thresholds on all layer1 ``nightly_heavy`` gold fixtures.

Updates ``quality_thresholds`` in each ``tests/fixtures/benchmarks/layer1/<case>/gold.json``
listed under ``nightly_heavy`` in ``case_tiers.json`` to the canonical merge-safe / nightly profile:

- min_sample_arxiv_f1 = 0.85
- min_authorship_names_f1 = 0.7
- require_reference_count_ok = false
- reference_count_range_factor = 0.3  (accept count in [0.7, 1.3] * expected_count band semantics)
- require_abstract_prefix = false
- min_abstract_prefix_containment = 0.7

Usage:
  python scripts/sync_layer1_thresholds.py --dry-run   # print planned changes only
  python scripts/sync_layer1_thresholds.py --apply     # write files
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LAYER1_ROOT = REPO_ROOT / "tests" / "fixtures" / "benchmarks" / "layer1"
TIERS_PATH = LAYER1_ROOT / "case_tiers.json"

CANONICAL_THRESHOLDS: dict[str, object] = {
    "min_authorship_names_f1": 0.7,
    "min_sample_arxiv_f1": 0.85,
    "require_reference_count_ok": False,
    "reference_count_range_factor": 0.3,
    "require_abstract_prefix": False,
    "min_abstract_prefix_containment": 0.7,
}


def _load_nightly_heavy() -> list[str]:
    raw = json.loads(TIERS_PATH.read_text(encoding="utf-8"))
    nh = raw.get("nightly_heavy")
    if not isinstance(nh, list):
        raise SystemExit("case_tiers.json missing nightly_heavy list")
    return [str(x).strip() for x in nh if str(x).strip()]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--apply", action="store_true", help="Write gold.json files (default is dry-run)")
    args = p.parse_args()
    dry_run = not args.apply

    case_ids = _load_nightly_heavy()
    changed = 0
    examined = 0
    for cid in case_ids:
        gold_path = LAYER1_ROOT / cid / "gold.json"
        if not gold_path.is_file():
            print(f"skip missing: {gold_path}")
            continue
        examined += 1
        data = json.loads(gold_path.read_text(encoding="utf-8"))
        prev = data.get("quality_thresholds")
        if not isinstance(prev, dict):
            prev = {}
        new_thr = dict(CANONICAL_THRESHOLDS)
        if new_thr == prev:
            continue
        data["quality_thresholds"] = new_thr
        desc = data.get("description")
        if isinstance(desc, str) and "sync_layer1_thresholds" not in desc:
            data["description"] = desc.rstrip() + " [thresholds via scripts/sync_layer1_thresholds.py]"
        blob = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        if dry_run:
            print(f"would update: {gold_path.relative_to(REPO_ROOT)}")
        else:
            gold_path.write_text(blob, encoding="utf-8")
            print(f"updated: {gold_path.relative_to(REPO_ROOT)}")
        changed += 1

    print(f"examined={examined} changed={changed} dry_run={dry_run}")


if __name__ == "__main__":
    main()
