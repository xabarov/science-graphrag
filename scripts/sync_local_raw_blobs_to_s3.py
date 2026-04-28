#!/usr/bin/env python3
"""
Upload an existing local ``blob_root/raw`` tree into S3/MinIO (content-addressed blobs).

Prerequisites:
  - Valid ``SCIENCE_GRAPHRAG_S3_*`` credentials and bucket in the environment
    (S3/MinIO is mandatory for the application; same bucket as ingest queue/artifacts).
  - Bucket exists or will be created via ``ensure_bucket_exists``.

Layout: local ``{blob_root}/raw/ab/sha256`` → S3 key ``blobs/raw/ab/sha256`` (see
``science_graphrag.storage.object_keys.raw_blob_object_key``).

Rollout order (recommended):
  1. ``scripts/sync_local_artifacts_to_s3.py`` (ingest artifacts).
  2. This script for raw blobs.
  3. ``scripts/sync_benchmark_runs_to_s3.py`` if you have local full benchmark JSON.
  4. Deploy / enable workers with the same bucket.

Usage (from repo root, venv active)::

  .venv/bin/python scripts/sync_local_raw_blobs_to_s3.py --dry-run
  .venv/bin/python scripts/sync_local_raw_blobs_to_s3.py
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions only; do not upload.",
    )
    parser.add_argument(
        "--blob-root",
        type=Path,
        default=None,
        help="Override local root (default: Settings.blob_root).",
    )
    args = parser.parse_args()

    from science_graphrag.config import Settings
    from science_graphrag.storage.object_keys import raw_blob_object_key
    from science_graphrag.storage.s3_client import build_s3_client, ensure_bucket_exists

    settings = Settings()
    client = build_s3_client(settings)
    ensure_bucket_exists(settings, client=client)
    bucket = settings.s3_bucket

    root = Path(args.blob_root or settings.blob_root).resolve() / "raw"
    if not root.is_dir():
        print(f"error: raw blob directory missing or not a directory: {root}", file=sys.stderr)
        return 1

    uploaded = 0
    skipped = 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        parts = rel.parts
        if len(parts) != 2 or ".." in parts:
            skipped += 1
            continue
        prefix2, name = parts[0], parts[1]
        if len(prefix2) != 2 or not _SHA256_RE.match(name):
            skipped += 1
            continue
        sha = name.lower()
        if prefix2.lower() != sha[:2]:
            print(f"warn: skip path/sha mismatch: {path}", file=sys.stderr)
            skipped += 1
            continue
        key = raw_blob_object_key(sha)
        if args.dry_run:
            print(f"would put s3://{bucket}/{key} <- {path}")
        else:
            client.upload_file(str(path), bucket, key)
            print(f"put s3://{bucket}/{key}")
        uploaded += 1

    print(
        f"done: {uploaded} file(s) uploaded"
        f"{f', {skipped} skipped' if skipped else ''}"
        f"{' (dry-run)' if args.dry_run else ''}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
