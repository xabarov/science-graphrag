"""SSE canonical extras on stage_progress (worker)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from science_graphrag.api.ingest.dto import IngestJobRecord
from science_graphrag.api.ingest.worker import _sse_progress_canonical_fields
from science_graphrag.config import Settings


def test_sse_progress_always_includes_progress_indeterminate_bool() -> None:
    """Enriched stage_progress must send false so clients clear a prior indeterminate state."""
    rec = IngestJobRecord(
        job_id="j-sse",
        workspace_id="ws",
        filename="a.pdf",
        status="running",
        stages=[
            {
                "name": "embed",
                "status": "running",
                "expected_duration_ms": 1000,
                "subprogress_current": 1,
                "subprogress_total": 4,
                "metrics": {},
            },
        ],
    )
    settings = MagicMock(spec=Settings)

    mock_reg = MagicMock()
    mock_reg.get_job.return_value = rec

    with patch("science_graphrag.api.ingest.worker._registry", return_value=mock_reg):
        out = _sse_progress_canonical_fields("j-sse", settings)

    assert "progress_indeterminate" in out
    assert out["progress_indeterminate"] is False
    assert out["ingest_phase"] == "preparing_search"
    assert out["active_stage"] == "embed"
