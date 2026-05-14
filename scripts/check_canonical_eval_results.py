#!/usr/bin/env python3
"""Lightweight guard: flag suspicious strings in committed eval JSON under eval/results/.

R8 hygiene — see docs/analysis/benchmark-artifact-hygiene-policy-2026-05-13.md

Default mode flags likely **secrets** only (many historical artifacts legitimately embed
repo-relative or machine paths; use ``--strict-paths`` when tightening canonical JSON).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

_SECRET_LIKE = re.compile(
    r"(BEGIN (RSA |OPENSSH )?PRIVATE KEY|"
    r"sk-[a-zA-Z0-9]{20,}|"
    r"api_key\s*[:=]\s*[\"'][^\"']{8,}[\"']|"
    r"Bearer\s+[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+)",
    re.IGNORECASE,
)

_ABSOLUTE_PATH = re.compile(r"(/home/[^/]+/|/Users/[^/]+/|\\\\Users\\\\[^\\\\]+\\\\)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "eval" / "results",
        help="Directory to scan (default: repo eval/results)",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=2_000_000,
        help="Skip files larger than this many bytes",
    )
    parser.add_argument(
        "--strict-paths",
        action="store_true",
        help="Also fail on absolute home-style paths (noisy on legacy artifacts)",
    )
    args = parser.parse_args()
    root: Path = args.root
    if not root.is_dir():
        print(f"Not a directory: {root}", file=sys.stderr)
        return 1

    bad: dict[str, list[str]] = defaultdict(list)
    for path in sorted(root.glob("*.json")):
        if path.stat().st_size > args.max_bytes:
            continue
        pkey = str(path)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            bad[pkey].append(f"read_error:{exc}")
            continue
        if _SECRET_LIKE.search(text):
            bad[pkey].append("secret_like_pattern")
        if args.strict_paths and _ABSOLUTE_PATH.search(text):
            bad[pkey].append("absolute_path_pattern")
        try:
            json.loads(text)
        except json.JSONDecodeError as exc:
            bad[pkey].append(f"invalid_json:{exc}")

    if bad:
        print("check_canonical_eval_results: FAILED", file=sys.stderr)
        for pkey in sorted(bad):
            reasons = "; ".join(bad[pkey])
            print(f"  {pkey}: {reasons}", file=sys.stderr)
        return 1
    print("check_canonical_eval_results: OK", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
