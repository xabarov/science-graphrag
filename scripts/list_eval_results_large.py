#!/usr/bin/env python3
"""List files under eval/results/ larger than a threshold (operator hygiene)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from science_graphrag.artifacts.benchmark_paths import REPO_ROOT


def main() -> int:
    """CLI entry for listing large files under eval/results (or --root)."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Directory to scan (default: <repo>/eval/results).",
    )
    parser.add_argument(
        "--min-mb",
        type=float,
        default=1.0,
        help="Minimum file size in megabytes (default: 1).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON array instead of human lines.",
    )
    args = parser.parse_args()

    root = Path(args.root) if args.root is not None else REPO_ROOT / "eval" / "results"
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 1
    min_bytes = max(0.0, float(args.min_mb)) * 1024 * 1024
    rows: list[dict[str, int | str]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        try:
            sz = path.stat().st_size
        except OSError:
            continue
        if sz < min_bytes:
            continue
        rel = path.relative_to(root)
        rows.append({"path": str(rel), "bytes": sz})

    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    for r in rows:
        mb = int(r["bytes"]) / (1024 * 1024)
        print(f"{mb:.2f} MiB\t{r['path']}")
    print(f"# count={len(rows)} root={root}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
