#!/usr/bin/env python3
# pylint: disable=duplicate-code
"""Build a zip of S3 object bodies (+ optional local benchmark summary) for incident export.

Examples::

  .venv/bin/python scripts/export_evidence_bundle.py \\
    --key science-diagnostics/od/foo.json --output /tmp/evidence.zip
  .venv/bin/python scripts/export_evidence_bundle.py \\
    --run-id <uuid> --include-benchmark-summary --output evidence.zip
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from science_graphrag.artifacts.run_layout import default_benchmark_runs_dir
from science_graphrag.storage.benchmark_object_keys import benchmark_run_full_object_key
from science_graphrag.storage.cli_preflight import settings_or_exit_for_object_storage_cli
from science_graphrag.storage.evidence_bundle import build_evidence_zip_bytes
from science_graphrag.storage.s3_client import build_s3_client, clear_s3_client_cache


def main() -> int:
    """Build a zip from S3 keys and optional local summary files."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--key",
        dest="keys",
        action="append",
        default=[],
        help="S3 object key (repeatable).",
    )
    parser.add_argument(
        "--keys-file",
        type=Path,
        default=None,
        help="Text file with one S3 key per line (optional).",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Add benchmark full.json key for this run id (uses s3_benchmark_runs_key_prefix).",
    )
    parser.add_argument(
        "--include-benchmark-summary",
        action="store_true",
        help="If --run-id is set, also pack local <run_id>.summary.json when present.",
    )
    parser.add_argument(
        "--history-dir",
        type=Path,
        default=None,
        help="Benchmark runs directory for --include-benchmark-summary.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output .zip path.",
    )
    args = parser.parse_args()

    try:
        settings, err = settings_or_exit_for_object_storage_cli()
        if err is not None:
            return err
        assert settings is not None

        keys = [k.strip() for k in args.keys if k and k.strip()]
        if args.keys_file is not None:
            try:
                for line in Path(args.keys_file).read_text(encoding="utf-8").splitlines():
                    s = line.strip()
                    if s and not s.startswith("#"):
                        keys.append(s)
            except OSError as exc:
                print(f"error: keys file: {exc}", file=sys.stderr)
                return 1

        if args.run_id:
            rid = args.run_id.strip()
            prefix = (settings.s3_benchmark_runs_key_prefix or "science-benchmarks").strip()
            keys.append(benchmark_run_full_object_key(rid, prefix=prefix))

        if not keys:
            print("error: no keys (--key, --keys-file, or --run-id)", file=sys.stderr)
            return 1

        extras: list[tuple[str, Path]] = []
        if args.run_id and args.include_benchmark_summary:
            hist = args.history_dir or default_benchmark_runs_dir()
            sp = hist / f"{args.run_id.strip()}.summary.json"
            if sp.is_file():
                extras.append((f"summaries/{args.run_id.strip()}.summary.json", sp))

        client = build_s3_client(settings)
        bucket = (settings.s3_bucket or "").strip()
        try:
            blob = build_evidence_zip_bytes(client, bucket, keys, extra_files=extras or None)
        except Exception as exc:  # noqa: BLE001 — boto ClientError
            print(f"error: bundle failed: {exc}", file=sys.stderr)
            return 1

        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(blob)
        print(
            json.dumps(
                {"output": str(out.resolve()), "bytes": len(blob), "keys": keys},
                indent=2,
            )
        )
        return 0
    finally:
        clear_s3_client_cache()


if __name__ == "__main__":
    raise SystemExit(main())
