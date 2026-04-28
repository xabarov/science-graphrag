from __future__ import annotations

from science_graphrag.api.ingest.dto import IngestJobRecord, job_record_to_view


def test_ingest_job_view_from_orm() -> None:
    record = IngestJobRecord(
        job_id="job-1",
        workspace_id="ws-1",
        filename="paper.pdf",
        status="running",
        stages=[
            {
                "name": "parse_pdf",
                "status": "completed",
                "started_at": "2026-01-01T00:00:00+00:00",
                "finished_at": "2026-01-01T00:00:01+00:00",
                "duration_ms": 1000,
                "metrics": {"source_suffix": ".pdf"},
                "error": None,
            }
        ],
    )

    view = job_record_to_view(record)

    assert view.job_id == "job-1"
    assert view.workspace_id == "ws-1"
    assert view.ingest_phase == "preparing_document"
    assert view.active_stage == "parse_pdf"
    assert view.stages[0].name == "parse_pdf"
    assert view.stages[0].metrics["source_suffix"] == ".pdf"


def test_ingest_job_view_progress_pct_weighted() -> None:
    record = IngestJobRecord(
        job_id="job-2",
        workspace_id="ws-1",
        filename="paper.pdf",
        status="running",
        stages=[
            {
                "name": "a",
                "status": "completed",
                "expected_duration_ms": 1000,
            },
            {
                "name": "b",
                "status": "running",
                "expected_duration_ms": 1000,
            },
        ],
    )
    view = job_record_to_view(record)
    assert view.progress_pct is not None
    assert abs(float(view.progress_pct) - 0.75) < 1e-9


def test_running_stage_subprogress_full_counts_as_completed_weight() -> None:
    record = IngestJobRecord(
        job_id="job-3",
        workspace_id="ws-1",
        filename="paper.pdf",
        status="running",
        stages=[
            {
                "name": "parse_pdf",
                "status": "completed",
                "expected_duration_ms": 1000,
            },
            {
                "name": "extract_meta",
                "status": "running",
                "expected_duration_ms": 1000,
                "subprogress_current": 10,
                "subprogress_total": 10,
            },
        ],
    )
    view = job_record_to_view(record)
    assert view.progress_pct is not None
    assert abs(float(view.progress_pct) - 1.0) < 1e-9


def test_batch_parent_aggregate_progress_from_children() -> None:
    from science_graphrag.api.ingest.ingest_progress import apply_batch_parent_aggregates

    parent = {
        "kind": "batch_parent",
        "child_jobs": [
            {
                "status": "completed",
                "progress_pct": 1.0,
                "ingest_phase": "finalizing",
                "active_stage": "",
            },
            {
                "status": "running",
                "progress_pct": 0.5,
                "ingest_phase": "preparing_document",
                "active_stage": "parse_pdf",
                "detail_message": "pages 1/2",
                "filename": "b.pdf",
            },
        ],
    }
    apply_batch_parent_aggregates(parent)
    assert abs(float(parent["progress_pct"]) - 0.75) < 1e-9
    assert parent["ingest_phase"] == "preparing_document"
    assert parent["active_stage"] == "parse_pdf"


def test_progress_indeterminate_true_for_single_vl_batch_waiting() -> None:
    record = IngestJobRecord(
        job_id="j-vl",
        workspace_id="ws",
        filename="x.pdf",
        status="running",
        stages=[
            {
                "name": "parse_pdf",
                "status": "running",
                "expected_duration_ms": 1000,
                "subprogress_current": 0,
                "subprogress_total": 5,
                "metrics": {"vl_batch_total": 1},
            },
        ],
    )
    view = job_record_to_view(record)
    assert view.progress_indeterminate is True
    assert view.progress_pct is not None
    assert float(view.progress_pct) < 0.01


def test_progress_indeterminate_false_for_multi_vl_batch() -> None:
    record = IngestJobRecord(
        job_id="j-vl2",
        workspace_id="ws",
        filename="x.pdf",
        status="running",
        stages=[
            {
                "name": "parse_pdf",
                "status": "running",
                "expected_duration_ms": 1000,
                "subprogress_current": 2,
                "subprogress_total": 10,
                "metrics": {"vl_batch_total": 3},
            },
        ],
    )
    view = job_record_to_view(record)
    assert view.progress_indeterminate is False
