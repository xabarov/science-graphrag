"""Phase 4: list and delete S3 objects by age; optional benchmark summary cleanup."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator


@dataclass(frozen=True)
class GCObjectInfo:
    """One object candidate for garbage collection."""

    key: str
    last_modified: datetime
    size: int


def iter_objects_older_than(
    client: Any,
    bucket: str,
    prefix: str,
    *,
    older_than_days: float,
) -> Iterator[GCObjectInfo]:
    """Yield objects under ``prefix`` whose LastModified is older than the cutoff."""

    if not (bucket or "").strip():
        raise ValueError("bucket name is required")
    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    pref = (prefix or "").strip()
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=pref):
        for obj in page.get("Contents") or []:
            key = str(obj.get("Key") or "")
            if not key:
                continue
            lm = obj.get("LastModified")
            if not isinstance(lm, datetime):
                continue
            if lm.tzinfo is None:
                lm = lm.replace(tzinfo=timezone.utc)
            if lm >= cutoff:
                continue
            size = int(obj.get("Size") or 0)
            yield GCObjectInfo(key=key, last_modified=lm, size=size)


def delete_object_keys(client: Any, bucket: str, keys: list[str]) -> list[dict[str, Any]]:
    """
    Delete up to 1000 keys per batch (S3 limit).

    Returns ``Errors`` entries from ``delete_objects`` responses (empty if all OK).
    """

    if not (bucket or "").strip():
        raise ValueError("bucket name is required")
    errors: list[dict[str, Any]] = []
    batch: list[dict[str, str]] = []
    for key in keys:
        batch.append({"Key": key})
        if len(batch) >= 1000:
            resp = client.delete_objects(
                Bucket=bucket,
                Delete={"Objects": batch, "Quiet": True},
            )
            errors.extend(resp.get("Errors") or [])
            batch = []
    if batch:
        resp = client.delete_objects(
            Bucket=bucket,
            Delete={"Objects": batch, "Quiet": True},
        )
        errors.extend(resp.get("Errors") or [])
    return errors


def fix_summaries_after_benchmark_key_delete(
    history_dir: Path,
    deleted_keys: set[str],
) -> int:
    """
    Clear ``full_run_object_key`` / ``full_run_json_bytes`` in local summaries when the
    remote object was removed.
    """

    if not deleted_keys:
        return 0
    hist = Path(history_dir)
    if not hist.is_dir():
        return 0
    updated = 0
    for path in sorted(hist.glob("*.summary.json")):
        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (OSError, json.JSONDecodeError, TypeError):
            continue
        if not isinstance(data, dict):
            continue
        key = data.get("full_run_object_key")
        if not isinstance(key, str) or key.strip() not in deleted_keys:
            continue
        data["full_run_object_key"] = None
        data["full_run_json_bytes"] = None
        path.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")
        updated += 1
    return updated
