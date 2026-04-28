#!/usr/bin/env python3
"""Upload local ``data/benchmark_runs/<run_id>.json`` to S3 and annotate ``*.summary.json``.

Requires valid ``SCIENCE_GRAPHRAG_S3_*`` credentials (same bucket/prefix as the API).

Dry-run prints planned keys without writing.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from science_graphrag.artifacts.run_layout import default_benchmark_runs_dir
from science_graphrag.config import Settings
from science_graphrag.storage.benchmark_object_keys import benchmark_run_full_object_key
from science_graphrag.storage.benchmark_run_persistence import S3BenchmarkRunPersistence
from science_graphrag.storage.s3_client import build_s3_client, ensure_bucket_exists


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--history-dir",
        type=Path,
        default=None,
        help="Override benchmark run directory (default: repo data/benchmark_runs).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions only; do not upload or modify summaries.",
    )
    args = parser.parse_args()

    settings = Settings()

    hist = args.history_dir or default_benchmark_runs_dir()
    if not hist.is_dir():
        print(f"error: history dir missing: {hist}", file=sys.stderr)
        return 1

    prefix = (settings.s3_benchmark_runs_key_prefix or "science-benchmarks").strip()
    store: S3BenchmarkRunPersistence | None = None
    if not args.dry_run:
        client = build_s3_client(settings)
        ensure_bucket_exists(settings, client=client)
        hint = int(getattr(settings, "object_storage_benchmark_full_retention_days", 0) or 0)
        store = S3BenchmarkRunPersistence(
            client,
            settings.s3_bucket,
            prefix,
            retention_hint_days=hint if hint > 0 else None,
        )

    uploaded = 0
    for path in sorted(hist.glob("*.json")):
        if path.name.endswith(".summary.json"):
            continue
        run_id = path.stem
        try:
            text = path.read_text(encoding="utf-8")
            payload = json.loads(text)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"skip {path}: {exc}", file=sys.stderr)
            continue
        rid = str(payload.get("run_id") or run_id)
        if args.dry_run:
            key = benchmark_run_full_object_key(rid, prefix=prefix)
            print(f"would_upload rid={rid} key={key} bytes={len(text.encode('utf-8'))}")
            continue
        assert store is not None
        key = store.put_full_json(rid, text)
        if not key:
            print(f"error: put_full_json returned empty key for {rid}", file=sys.stderr)
            return 1
        summary_path = hist / f"{rid}.summary.json"
        if summary_path.is_file():
            try:
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                summary = None
            if isinstance(summary, dict):
                summary["full_run_object_key"] = key
                summary["full_run_json_bytes"] = len(text.encode("utf-8"))
                summary_path.write_text(
                    json.dumps(summary, indent=2, default=str) + "\n",
                    encoding="utf-8",
                )
        uploaded += 1
        print(f"uploaded rid={rid} key={key}")

    print(json.dumps({"uploaded": uploaded, "dry_run": args.dry_run}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
