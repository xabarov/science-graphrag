#!/usr/bin/env python3
# pylint: disable=duplicate-code
"""List or delete S3/MinIO objects older than N days under a prefix (Phase 4 GC).

Uses LastModified from list_objects_v2. For benchmark full.json deletions, optionally
clears ``full_run_object_key`` in local ``*.summary.json`` under ``data/benchmark_runs``.

Requires SCIENCE_GRAPHRAG_OBJECT_STORAGE_ENABLED and credentials. Use ``--dry-run`` first.

Examples::

  .venv/bin/python scripts/gc_object_storage.py \\
    --prefix science-diagnostics/ --older-than-days 45 --dry-run
  .venv/bin/python scripts/gc_object_storage.py \\
    --prefix science-benchmarks/ --key-suffix full.json \\
    --older-than-days 120 --execute --fix-benchmark-summaries
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from science_graphrag.artifacts.run_layout import default_benchmark_runs_dir
from science_graphrag.storage.cli_preflight import settings_or_exit_for_object_storage_cli
from science_graphrag.storage.object_storage_gc import (
    delete_object_keys,
    fix_summaries_after_benchmark_key_delete,
    iter_objects_older_than,
)
from science_graphrag.storage.s3_client import build_s3_client, clear_s3_client_cache


def main() -> int:
    """Parse argv and run GC list or delete."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--prefix",
        type=str,
        default="science-diagnostics/",
        help="S3 key prefix (trailing slash recommended).",
    )
    parser.add_argument(
        "--older-than-days",
        type=float,
        default=30.0,
        help="Delete objects with LastModified older than this many days.",
    )
    parser.add_argument(
        "--key-suffix",
        type=str,
        default="",
        help="If set, only consider keys ending with this substring (e.g. full.json).",
    )
    parser.add_argument(
        "--max-keys",
        type=int,
        default=0,
        help="If >0, stop after considering this many deletable keys (safety cap).",
    )
    mx = parser.add_mutually_exclusive_group(required=True)
    mx.add_argument(
        "--dry-run",
        action="store_true",
        help="Print keys only; do not delete.",
    )
    mx.add_argument(
        "--execute",
        action="store_true",
        help="Perform delete_objects on matched keys.",
    )
    parser.add_argument(
        "--fix-benchmark-summaries",
        action="store_true",
        help=(
            "After delete, clear full_run_object_key in local *.summary.json when it "
            "matches a deleted key (default history dir: data/benchmark_runs)."
        ),
    )
    parser.add_argument(
        "--history-dir",
        type=Path,
        default=None,
        help="Override benchmark runs dir for --fix-benchmark-summaries.",
    )
    args = parser.parse_args()

    try:
        settings, err = settings_or_exit_for_object_storage_cli()
        if err is not None:
            return err

        client = build_s3_client(settings)
        bucket = (settings.s3_bucket or "").strip()
        suffix = (args.key_suffix or "").strip()
        keys: list[str] = []
        for info in iter_objects_older_than(
            client,
            bucket,
            args.prefix,
            older_than_days=float(args.older_than_days),
        ):
            if suffix and not info.key.endswith(suffix):
                continue
            keys.append(info.key)
            if args.max_keys and len(keys) >= int(args.max_keys):
                break

        if args.dry_run:
            print(json.dumps({"dry_run": True, "count": len(keys), "keys": keys}, indent=2))
            return 0

        if keys:
            del_errors = delete_object_keys(client, bucket, keys)
            if del_errors:
                print(json.dumps({"delete_errors": del_errors}, indent=2), file=sys.stderr)
                return 2
        fixed = 0
        if args.fix_benchmark_summaries and keys:
            hist = args.history_dir or default_benchmark_runs_dir()
            fixed = fix_summaries_after_benchmark_key_delete(hist, set(keys))
        print(json.dumps({"deleted": len(keys), "summaries_fixed": fixed}, indent=2))
        return 0
    finally:
        clear_s3_client_cache()


if __name__ == "__main__":
    raise SystemExit(main())
