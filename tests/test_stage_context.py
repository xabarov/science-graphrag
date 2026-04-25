from __future__ import annotations

from pathlib import Path

import pytest

from science_graphrag.ingestion.stage_context import IngestStage, stage
from science_graphrag.storage.db import get_engine, init_db, session_factory
from science_graphrag.storage.models_orm import IngestJobStageOrm


def _session_factory(tmp_path: Path):
    db_path = tmp_path / "stage_context.sqlite3"
    engine = get_engine(f"sqlite+pysqlite:///{db_path}")
    init_db(engine)
    return session_factory(engine)


def test_stage_context_success(tmp_path: Path) -> None:
    factory = _session_factory(tmp_path)

    with stage("job-success", IngestStage.EMBED, session_factory=factory) as st:
        st.metric("chunks", 42)

    with factory() as session:
        row = (
            session.query(IngestJobStageOrm)
            .filter(
                IngestJobStageOrm.job_id == "job-success",
                IngestJobStageOrm.stage == IngestStage.EMBED.value,
            )
            .one()
        )
        assert row.status == "completed"
        assert row.finished_at is not None
        assert '"chunks": 42' in (row.metrics_json or "")


def test_stage_context_failed(tmp_path: Path) -> None:
    factory = _session_factory(tmp_path)

    with pytest.raises(RuntimeError, match="boom"):
        with stage("job-failed", IngestStage.WRITE_GRAPH, session_factory=factory) as st:
            st.metric("attempt", 1)
            raise RuntimeError("boom")

    with factory() as session:
        row = (
            session.query(IngestJobStageOrm)
            .filter(
                IngestJobStageOrm.job_id == "job-failed",
                IngestJobStageOrm.stage == IngestStage.WRITE_GRAPH.value,
            )
            .one()
        )
        assert row.status == "failed"
        assert row.error == "boom"
        assert row.finished_at is not None


def test_stage_context_noop_without_job_id() -> None:
    with stage(None, IngestStage.PARSE_PDF, session_factory=None) as st:
        st.metric("source_suffix", ".pdf")
