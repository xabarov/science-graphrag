#!/usr/bin/env python3
# pylint: disable=duplicate-code
"""Promote a runtime JSON payload to a sanitized, reviewable file (Phase 4).

Loads from S3 (--s3-key), a local file (--local-file), or benchmark full JSON (--run-id).

Writes to --output. Optional --commit-path writes under the repo when paired with
``--i-confirm-git-write`` (safety interlock).

Examples::

  .venv/bin/python scripts/promote_object_for_review.py \\
    --s3-key science-diagnostics/od/foo.json --output /tmp/review.json
  .venv/bin/python scripts/promote_object_for_review.py \\
    --run-id <uuid> --output /tmp/run.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from botocore.exceptions import ClientError

from science_graphrag.artifacts.benchmark_paths import REPO_ROOT
from science_graphrag.artifacts.promotion import promoted_json_bytes
from science_graphrag.config import Settings
from science_graphrag.storage.benchmark_object_keys import benchmark_run_full_object_key
from science_graphrag.storage.benchmark_run_persistence import S3BenchmarkRunPersistence
from science_graphrag.storage.s3_client import build_s3_client, clear_s3_client_cache


def _load_json_payload(
    *,
    settings: Settings,
    s3_key: str | None,
    local_file: Path | None,
    run_id: str | None,
) -> tuple[Any, str, str | None]:
    """Return (payload, source_label, s3_key_for_meta)."""

    if sum(x is not None for x in (s3_key, local_file, run_id)) != 1:
        raise ValueError("exactly one of --s3-key, --local-file, --run-id is required")

    if local_file is not None:
        text = Path(local_file).read_text(encoding="utf-8")
        return json.loads(text), f"local:{local_file}", None

    client = build_s3_client(settings)
    bucket = (settings.s3_bucket or "").strip()
    if run_id is not None:
        prefix = (settings.s3_benchmark_runs_key_prefix or "science-benchmarks").strip()
        key = benchmark_run_full_object_key(run_id.strip(), prefix=prefix)
        store = S3BenchmarkRunPersistence(client, bucket, prefix)
        text = store.get_full_json(run_id.strip(), object_key=key)
        if text is None:
            raise FileNotFoundError(
                f"benchmark full json missing for run_id={run_id!r} key={key!r}"
            )
        return json.loads(text), f"benchmark_run:{run_id}", key

    assert s3_key is not None
    key = s3_key.strip()
    try:
        resp = client.get_object(Bucket=bucket, Key=key)
        body = resp["Body"].read().decode("utf-8")
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        if code in ("404", "NotFound", "NoSuchKey"):
            raise FileNotFoundError(f"s3 object not found: {key!r}") from exc
        raise
    return json.loads(body), f"s3:{key}", key


def main() -> int:
    """CLI entry: load JSON, sanitize, write promoted document."""
    parser = argparse.ArgumentParser(description=__doc__)
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--s3-key", type=str, default=None)
    src.add_argument("--local-file", type=Path, default=None)
    src.add_argument("--run-id", type=str, default=None)
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Primary output path for promoted JSON.",
    )
    parser.add_argument(
        "--commit-path",
        type=Path,
        default=None,
        help="If set with --i-confirm-git-write, also write this path (must stay under repo root).",
    )
    parser.add_argument(
        "--i-confirm-git-write",
        action="store_true",
        help="Acknowledge writing under the repository tree (required with --commit-path).",
    )
    parser.add_argument(
        "--max-output-bytes",
        type=int,
        default=524_288,
        help="Refuse if promoted UTF-8 JSON exceeds this size (default 512 KiB).",
    )
    args = parser.parse_args()

    try:
        settings = Settings()
        try:
            payload, source_label, meta_key = _load_json_payload(
                settings=settings,
                s3_key=args.s3_key,
                local_file=args.local_file,
                run_id=args.run_id,
            )
        except (ValueError, OSError, json.JSONDecodeError, FileNotFoundError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

        run_for_meta = args.run_id.strip() if args.run_id else None
        data = promoted_json_bytes(
            payload,
            source_label=source_label,
            s3_key=meta_key,
            run_id=run_for_meta,
        )
        if len(data) > int(args.max_output_bytes):
            lim = int(args.max_output_bytes)
            msg = f"error: promoted output {len(data)} bytes exceeds --max-output-bytes={lim}"
            print(msg, file=sys.stderr)
            return 1

        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)

        if args.commit_path is not None:
            if not args.i_confirm_git_write:
                print("error: --commit-path requires --i-confirm-git-write", file=sys.stderr)
                return 1
            repo_root = REPO_ROOT.resolve()
            commit = Path(args.commit_path).resolve()
            try:
                commit.relative_to(repo_root)
            except ValueError:
                print(
                    f"error: --commit-path {commit} is outside repository root {repo_root}",
                    file=sys.stderr,
                )
                return 1
            commit.parent.mkdir(parents=True, exist_ok=True)
            commit.write_bytes(data)

        print(
            json.dumps(
                {
                    "output": str(out.resolve()),
                    "commit_path": (
                        str(Path(args.commit_path).resolve()) if args.commit_path else None
                    ),
                    "bytes": len(data),
                },
                indent=2,
            )
        )
        return 0
    finally:
        clear_s3_client_cache()


if __name__ == "__main__":
    raise SystemExit(main())
