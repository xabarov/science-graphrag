"""In-process ingest dispatcher facade."""

from __future__ import annotations

import threading
from pathlib import Path
from tempfile import gettempdir
from typing import Any

from fastapi import HTTPException

from science_graphrag.api.ingest_event_bus import BUS
from science_graphrag.config import Settings

from .dto import IngestJobRecord, job_record_to_view, now_iso
from .registry import _registry
from .worker import (
    SUPPORTED_SUFFIXES,
    _append_log,
    _refresh_parent_job,
    _run_batch_thread,
    _run_ingest_thread,
)

BATCH_MAX_FILES = 200
__all__ = [
    "BATCH_MAX_FILES",
    "SUPPORTED_SUFFIXES",
    "_append_log",
    "_refresh_parent_job",
    "IngestDispatcher",
    "job_to_dict",
    "start_batch_ingest_job",
    "start_ingest_job",
]


class IngestDispatcher:
    def enqueue(self, job_id: str) -> None:
        # Wave W: replace with Dramatiq actor.enqueue(ingest_document_actor, job_id)
        _ = job_id


def start_batch_ingest_job(
    *,
    workspace_id: str,
    files: list[tuple[str, bytes]],
    settings: Settings,
) -> IngestJobRecord:
    if not files:
        raise HTTPException(status_code=400, detail="no_files")
    if len(files) > BATCH_MAX_FILES:
        raise HTTPException(
            status_code=400,
            detail={"error": "too_many_files", "max": BATCH_MAX_FILES, "got": len(files)},
        )
    BUS.cleanup_old_events(ttl_hours=24)
    registry = _registry(settings)
    parent = registry.create_job(workspace_id, f"batch ({len(files)} files)", kind="batch_parent")
    registry._update(
        parent.job_id, progress_total=len(files), message=f"Queued {len(files)} file(s)"
    )  # noqa: SLF001
    child_paths: list[tuple[str, Path]] = []
    for name, data in files:
        if not data:
            continue
        suffix = Path(name or "doc").suffix.lower()
        if suffix not in SUPPORTED_SUFFIXES:
            continue
        child = registry.create_job(
            workspace_id,
            (name or "upload").strip() or "upload",
            kind="batch_child",
            parent_job_id=parent.job_id,
        )
        safe = f"ingest-{child.job_id}{suffix}"
        temp_path = Path(gettempdir()) / safe
        temp_path.write_bytes(data)
        child_paths.append((child.job_id, temp_path))
        _append_log(child.job_id, f"Part of batch {parent.job_id}")
    if not child_paths:
        registry._update(  # noqa: SLF001
            parent.job_id,
            status="failed",
            error="no_valid_files",
            message="No supported files in batch",
            finished_at=now_iso(),
        )
        raise HTTPException(status_code=400, detail="no_supported_files_in_batch")
    registry._update(
        parent.job_id, child_job_ids=[child_id for child_id, _ in child_paths]
    )  # noqa: SLF001
    threading.Thread(
        target=_run_batch_thread,
        args=(parent.job_id, child_paths, settings),
        name=f"batch-{parent.job_id}",
        daemon=True,
    ).start()
    return parent


def start_ingest_job(
    *,
    workspace_id: str,
    filename: str,
    file_bytes: bytes,
    settings: Settings,
) -> IngestJobRecord:
    if not file_bytes:
        raise HTTPException(status_code=400, detail="empty_file")
    suffix = Path(filename or "upload").suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=f"unsupported_type_allowed:{','.join(sorted(SUPPORTED_SUFFIXES))}",
        )
    BUS.cleanup_old_events(ttl_hours=24)
    rec = _registry(settings).create_job(workspace_id, filename)
    safe_name = f"ingest-{rec.job_id}{suffix}"
    temp_path = Path(gettempdir()) / safe_name
    temp_path.write_bytes(file_bytes)
    _append_log(rec.job_id, f"Saved {len(file_bytes)} bytes → {temp_path.name}")
    thread = threading.Thread(
        target=_run_ingest_thread,
        args=(rec.job_id, temp_path, settings),
        name=f"ingest-{rec.job_id}",
        daemon=True,
    )
    thread.start()
    return rec


def job_to_dict(rec: IngestJobRecord) -> dict[str, Any]:
    out = job_record_to_view(rec).model_dump()
    if rec.kind == "batch_parent":
        child_jobs: list[dict[str, Any]] = []
        for child_id in rec.child_job_ids:
            child = _registry().get(child_id)
            if child:
                child_jobs.append(job_to_dict(child))
        out["child_jobs"] = child_jobs
    return out
