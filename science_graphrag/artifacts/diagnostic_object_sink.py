"""Write heavy diagnostic JSON/JSONL to local data dir or S3 (Phase 3 CLI / eval)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from science_graphrag.artifacts.benchmark_paths import REPO_ROOT
from science_graphrag.artifacts.retention import RetentionClass, s3_put_object_retention_kwargs
from science_graphrag.config import Settings
from science_graphrag.storage.benchmark_object_keys import od_diagnostics_object_key

DiagnosticKind = Literal["od", "chat_agent", "eval"]


def _s3_get_object_body_or_empty(client: Any, bucket: str, key: str) -> bytes:
    """Return object bytes, or empty when the key is missing (not other errors)."""
    from botocore.exceptions import ClientError  # pylint: disable=import-outside-toplevel

    try:
        resp = client.get_object(Bucket=bucket, Key=key)
        return resp["Body"].read()
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        if code in ("404", "NotFound", "NoSuchKey", "NoSuchBucket"):
            return b""
        raise


def default_local_diagnostics_dir(kind: DiagnosticKind = "od") -> Path:
    """Runtime diagnostics under ``data/diagnostics`` (not ``eval/results``)."""
    d = REPO_ROOT / "data" / "diagnostics" / str(kind)
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_diagnostic_bytes(
    filename: str,
    data: bytes,
    *,
    settings: Settings,
    kind: DiagnosticKind = "od",
    content_type: str | None = None,
    local_path: Path | None = None,
) -> dict[str, Any]:
    """
    Persist diagnostic payload.

    When ``diagnostics_object_storage`` and ``object_storage_enabled`` are true, uploads to S3
    under ``s3_diagnostics_key_prefix`` and returns ``{"storage": "s3", "key": ...}``.
    Otherwise writes to ``local_path`` or ``data/diagnostics/<kind>/<filename>``.
    """
    name = (
        ((local_path.name if local_path else filename) or "artifact.bin")
        .strip()
        .replace("\\", "/")
        .rsplit("/", maxsplit=1)[-1]
    )
    if settings.diagnostics_object_storage and settings.object_storage_enabled:
        from science_graphrag.storage.s3_client import (  # pylint: disable=import-outside-toplevel
            build_s3_client,
            ensure_bucket_exists,
        )

        client = build_s3_client(settings)
        ensure_bucket_exists(settings, client=client)
        prefix = (settings.s3_diagnostics_key_prefix or "science-diagnostics").strip()
        sub = str(kind)
        key = od_diagnostics_object_key(name, prefix=prefix, subdir=sub)
        extra: dict[str, Any] = {}
        if content_type:
            extra["ContentType"] = content_type
        hint = getattr(settings, "object_storage_diagnostics_retention_days", 0) or 0
        extra.update(
            s3_put_object_retention_kwargs(
                RetentionClass.EPHEMERAL_DIAGNOSTIC,
                diagnostic_kind=sub,
                retention_hint_days=int(hint) if hint > 0 else None,
            )
        )
        client.put_object(Bucket=settings.s3_bucket, Key=key, Body=data, **extra)
        return {"storage": "s3", "key": key, "bucket": settings.s3_bucket}

    path = local_path if local_path is not None else default_local_diagnostics_dir(kind) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {"storage": "local", "path": str(path.resolve())}


def write_diagnostic_json(
    filename: str,
    payload: Any,
    *,
    settings: Settings,
    kind: DiagnosticKind = "od",
    indent: int | None = 2,
    local_path: Path | None = None,
) -> dict[str, Any]:
    """JSON-encode ``payload`` and write via :func:`write_diagnostic_bytes`."""
    text = json.dumps(payload, indent=indent, default=str)
    if indent is not None:
        text += "\n"
    data = text.encode("utf-8")
    return write_diagnostic_bytes(
        filename,
        data,
        settings=settings,
        kind=kind,
        content_type="application/json",
        local_path=local_path,
    )


def _append_diagnostic_jsonl_s3(
    settings: Settings,
    *,
    kind: DiagnosticKind,
    leaf: str,
    line: str,
) -> dict[str, Any]:
    """Read-modify-write one JSONL object on S3 (small streams only)."""
    from science_graphrag.storage.s3_client import (  # pylint: disable=import-outside-toplevel
        build_s3_client,
        ensure_bucket_exists,
    )

    client = build_s3_client(settings)
    ensure_bucket_exists(settings, client=client)
    prefix = (settings.s3_diagnostics_key_prefix or "science-diagnostics").strip()
    key = od_diagnostics_object_key(leaf, prefix=prefix, subdir=str(kind))
    prev = _s3_get_object_body_or_empty(client, settings.s3_bucket, key)
    hint = getattr(settings, "object_storage_diagnostics_retention_days", 0) or 0
    extra = s3_put_object_retention_kwargs(
        RetentionClass.EPHEMERAL_DIAGNOSTIC,
        diagnostic_kind=str(kind),
        retention_hint_days=int(hint) if hint > 0 else None,
    )
    client.put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=prev + line.encode("utf-8"),
        ContentType="application/x-ndjson",
        **extra,
    )
    return {"storage": "s3", "key": key, "bucket": settings.s3_bucket}


def write_diagnostic_jsonl_line(
    filename: str,
    row: dict[str, Any],
    *,
    settings: Settings,
    kind: DiagnosticKind = "od",
    append: bool = True,
    local_path: Path | None = None,
) -> dict[str, Any]:
    """Append one JSONL line (local append; S3 rewrites whole object — avoid huge files)."""
    line = json.dumps(row, default=str) + "\n"
    if settings.diagnostics_object_storage and settings.object_storage_enabled:
        leaf = (local_path.name if local_path else filename) or "artifact.jsonl"
        return _append_diagnostic_jsonl_s3(settings, kind=kind, leaf=leaf, line=line)

    path = local_path if local_path is not None else default_local_diagnostics_dir(kind) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append and path.is_file() else "w"
    with path.open(mode, encoding="utf-8") as fh:
        fh.write(line)
    return {"storage": "local", "path": str(path.resolve())}
