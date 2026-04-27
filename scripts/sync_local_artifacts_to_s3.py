#!/usr/bin/env python3
"""
Upload an existing local ``artifact_root`` tree into S3/MinIO (Phase 2 ingest artifacts).

Prerequisites:
  - ``SCIENCE_GRAPHRAG_OBJECT_STORAGE_ENABLED=true`` and valid S3 settings in the environment.
  - Bucket exists (``science-graphrag`` API lifespan or ``ensure_bucket_exists`` equivalent).

Rollout order (recommended):
  1. Run this script with ``--dry-run``, review keys.
  2. Run without ``--dry-run`` to upload.
  3. Enable object storage on all API/worker instances so reads/writes use the same bucket.

Usage (from repo root, venv active)::

  .venv/bin/python scripts/sync_local_artifacts_to_s3.py --dry-run
  .venv/bin/python scripts/sync_local_artifacts_to_s3.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions only; do not upload.",
    )
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=None,
        help="Override local root (default: Settings.artifact_root).",
    )
    args = parser.parse_args()

    from science_graphrag.config import Settings
    from science_graphrag.storage.object_keys import ingest_artifact_object_key
    from science_graphrag.storage.s3_client import build_s3_client, ensure_bucket_exists

    settings = Settings()
    if not settings.object_storage_enabled:
        print(
            "error: SCIENCE_GRAPHRAG_OBJECT_STORAGE_ENABLED must be true for S3 upload.",
            file=sys.stderr,
        )
        return 1

    root = Path(args.artifact_root or settings.artifact_root).resolve()
    if not root.is_dir():
        print(f"error: artifact root is not a directory: {root}", file=sys.stderr)
        return 1

    prefix = settings.s3_artifact_key_prefix.strip().strip("/")
    client = build_s3_client(settings)
    ensure_bucket_exists(settings, client=client)
    bucket = settings.s3_bucket

    uploaded = 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        if ".." in rel.parts:
            continue
        key = ingest_artifact_object_key(rel, prefix=prefix)
        if args.dry_run:
            print(f"would put s3://{bucket}/{key} <- {path}")
        else:
            client.upload_file(str(path), bucket, key)
            print(f"put s3://{bucket}/{key}")
        uploaded += 1

    print(f"done: {uploaded} file(s){' (dry-run)' if args.dry_run else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
