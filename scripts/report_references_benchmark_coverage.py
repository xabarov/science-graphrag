#!/usr/bin/env python3
"""Report which layer-1 fixtures include ``references_benchmark`` in ``gold.json``."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "benchmarks" / "layer1"


def main() -> int:
    """Print coverage summary; exit 1 if a tier lists cases without ``references_benchmark``."""
    tiers_path = FIXTURES / "case_tiers.json"
    tiers = json.loads(tiers_path.read_text(encoding="utf-8"))
    v1 = set(tiers.get("references_benchmark_v1", []))
    full = set(tiers.get("references_benchmark_full", []))

    case_dirs = sorted(p.name for p in FIXTURES.iterdir() if p.is_dir())
    with_rb: list[str] = []
    without: list[str] = []
    for cid in case_dirs:
        g = FIXTURES / cid / "gold.json"
        if not g.is_file():
            continue
        data = json.loads(g.read_text(encoding="utf-8"))
        if data.get("references_benchmark"):
            with_rb.append(cid)
        else:
            without.append(cid)

    print("references_benchmark coverage (layer1 gold.json)")
    print(f"  with block:    {len(with_rb)}")
    print(f"  without block: {len(without)}")
    if without:
        print("  missing:", ", ".join(without))
    print()
    print("tiers:")
    print(f"  references_benchmark_v1:   {len(v1)} cases")
    print(f"  references_benchmark_full: {len(full)} cases")
    missing_v1 = v1 - set(with_rb)
    missing_full = full - set(with_rb)
    if missing_v1:
        print(f"  ERROR: v1 tier missing gold: {sorted(missing_v1)}")
        return 1
    if missing_full:
        print(f"  ERROR: full tier missing gold: {sorted(missing_full)}")
        return 1
    print("  OK: all tier cases have references_benchmark")
    return 0


if __name__ == "__main__":
    sys.exit(main())
