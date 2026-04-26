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
