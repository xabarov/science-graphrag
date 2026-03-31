#!/usr/bin/env python3
"""
Update layer-1 gold.json work_metadata from a benchmark JSON suite report.

Use after an LLM benchmark run when gold titles/abstract_prefix drift from PDF→MD
but LLM extraction is the contract you want to measure.

Usage:
  .venv/bin/python scripts/sync_layer1_gold_from_report.py \\
    eval/results/baseline-llm-layer1-nightly-heavy-suite.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def _abstract_prefix(abstract: str, max_len: int = 72) -> str:
    one = re.sub(r"\s+", " ", abstract.replace("\n", " ").strip())
    return one[:max_len]


def main() -> int:
    """CLI entry: patch gold files from a layer-1 benchmark suite JSON."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report_json", type=Path)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print changes only",
    )
    args = parser.parse_args()
    data = json.loads(args.report_json.read_text(encoding="utf-8"))
    cases = data.get("cases") or []
    root = Path(__file__).resolve().parents[1]
    changed = 0
    for case in cases:
        case_id = case.get("case_id")
        pred = case.get("predicted") or {}
        wm = pred.get("work_metadata") or {}
        title = wm.get("title")
        abstract = wm.get("abstract") or ""
        if not case_id or not title:
            continue
        gold_path = root / "tests/fixtures/benchmarks/layer1" / case_id / "gold.json"
        if not gold_path.is_file():
            print(f"skip missing {gold_path}", file=sys.stderr)
            continue
        g = json.loads(gold_path.read_text(encoding="utf-8"))
        wmeta = g.setdefault("work_metadata", {})
        old_title = wmeta.get("title")
        old_prefix = wmeta.get("abstract_prefix")
        new_prefix = _abstract_prefix(abstract) if abstract.strip() else old_prefix
        if old_title == title and old_prefix == new_prefix:
            continue
        print(f"{case_id}: title {old_title!r} -> {title!r}")
        if new_prefix != old_prefix:
            print(f"  abstract_prefix -> {new_prefix!r}")
        wmeta["title"] = title
        if new_prefix is not None:
            wmeta["abstract_prefix"] = new_prefix
        if not args.dry_run:
            gold_path.write_text(
                json.dumps(g, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            changed += 1
    print(f"updated {changed} gold files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
