"""Phase 4: retention classification and S3 object tags / metadata for lifecycle + GC."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from urllib.parse import urlencode


class RetentionClass(str, Enum):
    """Coarse lifecycle bucket for object-storage artifacts (roadmap Phase 4)."""

    EPHEMERAL_DIAGNOSTIC = "ephemeral_diagnostic"
    BENCHMARK_FULL_RUN = "benchmark_full_run"
    PROMOTED_REVIEW = "promoted_review"


def _utc_iso_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")


def s3_put_object_retention_kwargs(
    retention_class: RetentionClass,
    *,
    diagnostic_kind: str | None = None,
    run_id: str | None = None,
    retention_hint_days: int | None = None,
) -> dict[str, Any]:
    """
    Extra keyword arguments for boto3 ``put_object`` (Tagging + Metadata).

    Tag keys are kept short and alphanumeric-ish for MinIO/S3 compatibility.
    """
    tags: dict[str, str] = {
        "retention_class": retention_class.value,
        "written_at": _utc_iso_compact(),
    }
    if diagnostic_kind:
        tags["diagnostic_kind"] = diagnostic_kind[:64]
    if run_id:
        tags["run_id"] = run_id.strip()[:128]
    if retention_hint_days is not None and retention_hint_days > 0:
        tags["retention_hint_days"] = str(int(retention_hint_days))

    tagging = urlencode(tags)
    meta: dict[str, str] = {
        "retention-class": retention_class.value,
        "written-at": tags["written_at"],
    }
    if diagnostic_kind:
        meta["diagnostic-kind"] = diagnostic_kind[:64]
    if run_id:
        meta["run-id"] = run_id.strip()[:128]
    if retention_hint_days is not None and retention_hint_days > 0:
        meta["retention-hint-days"] = str(int(retention_hint_days))

    return {"Tagging": tagging, "Metadata": meta}
