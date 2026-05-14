"""Batch parent orchestration for ingest jobs (no single-document pipeline logic)."""

from __future__ import annotations

from pathlib import Path

from science_graphrag.api.ingest.dto import now_iso
from science_graphrag.config import Settings, get_settings
from science_graphrag.ingestion.jobs.ingest_job_bus import publish_ingest_job_event
from science_graphrag.ingestion.jobs.registry import get_ingest_job_registry
from science_graphrag.ingestion.jobs.single_document_ingest import execute_single_ingest


def run_ingest_thread(job_id: str, temp_path: Path, settings: Settings) -> None:
    """Run single-document ingest then delete the temp upload path."""
    try:
        execute_single_ingest(job_id, temp_path, settings)
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass


def refresh_parent_job(parent_id: str, *, settings: Settings | None = None) -> None:
    """Recompute batch_parent status/progress from child rows and emit bus events."""
    registry = get_ingest_job_registry(settings or get_settings())
    parent = registry.get(parent_id)
    if not parent or parent.kind != "batch_parent":
        return
    children = [cid for cid in parent.child_job_ids if cid]
    if not children:
        return
    statuses = []
    for child_id in children:
        child = registry.get(child_id)
        if child:
            statuses.append(child.status)
    failed = sum(1 for status in statuses if status == "failed")
    done = sum(1 for status in statuses if status in ("completed", "failed"))
    total = len(children)
    pct = int(100 * done / total) if total else 100
    if done < total:
        message = f"Batch running ({done}/{total})"
        status = "running"
    elif failed == total:
        message = f"Batch failed ({failed}/{total})"
        status = "failed"
    elif failed:
        ok = total - failed
        message = f"Batch finished: {ok} ok, {failed} failed (of {total})"
        status = "completed"
    else:
        message = f"Batch completed ({total} file(s))"
        status = "completed"
    registry.update_job(
        parent_id,
        status=status,
        message=message,
        progress_current=pct,
        progress_total=100,
        finished_at=now_iso() if done == total else parent.finished_at,
    )
    publish_ingest_job_event(
        job_id=parent_id,
        parent_job_id=None,
        kind="batch_progress",
        payload={
            "job_id": parent_id,
            "status": status,
            "message": message,
            "progress_current": pct,
            "progress_total": 100,
            "done_children": done,
            "total_children": total,
        },
    )
    if done == total:
        publish_ingest_job_event(
            job_id=parent_id,
            parent_job_id=None,
            kind="terminal",
            payload={"job_id": parent_id, "status": status, "finished_at": now_iso()},
        )


def run_batch_thread(
    parent_id: str, child_paths: list[tuple[str, Path]], settings: Settings
) -> None:
    """Process batch children sequentially; refresh parent progress and unlink temp files."""
    registry = get_ingest_job_registry(settings)
    parent = registry.get(parent_id)
    if not parent:
        for _, path in child_paths:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        return
    registry.update_job(
        parent_id,
        status="running",
        message=f"Processing {len(child_paths)} file(s)…",
        progress_current=0,
        progress_total=100,
    )
    try:
        for child_id, path in child_paths:
            execute_single_ingest(child_id, path, settings)
            refresh_parent_job(parent_id, settings=settings)
    finally:
        for _, path in child_paths:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        refresh_parent_job(parent_id, settings=settings)
