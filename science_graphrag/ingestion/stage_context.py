from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Callable, Iterator

from science_graphrag.observability.phoenix_tracer import chain_span
from science_graphrag.storage.models_orm import IngestJobStageOrm


class IngestStage(str, Enum):
    PARSE_PDF = "parse_pdf"
    EXTRACT_META = "extract_meta"
    ENRICH_OPENALEX = "enrich_openalex"
    ENRICH_ROR = "enrich_ror"
    RESOLVE_REFERENCES = "resolve_references"
    WRITE_GRAPH = "write_graph"
    CHUNK = "chunk"
    EXTRACT_CLAIMS = "extract_claims"
    EMBED = "embed"
    ATTACH_WORKSPACE = "attach_workspace"


@dataclass
class StageHandle:
    stage: IngestStage
    metrics: dict[str, Any] = field(default_factory=dict)

    def metric(self, key: str, value: Any) -> None:
        if not key:
            return
        self.metrics[str(key)] = value


StageEventPublisher = Callable[[IngestStage, str, dict[str, Any], str | None], None]


def _upsert_stage_row(
    *,
    session_factory: Callable[[], Any],
    job_id: str,
    stage_value: IngestStage,
    status: str,
    finished_at: datetime | None = None,
    metrics: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    with session_factory() as session:
        row = (
            session.query(IngestJobStageOrm)
            .filter(
                IngestJobStageOrm.job_id == job_id,
                IngestJobStageOrm.stage == stage_value.value,
            )
            .first()
        )
        now = datetime.now(UTC)
        if row is None:
            row = IngestJobStageOrm(
                job_id=job_id,
                stage=stage_value.value,
                started_at=now,
            )
            session.add(row)
        row.status = status
        if finished_at is not None:
            row.finished_at = finished_at
        if metrics is not None:
            row.metrics_json = json.dumps(metrics, ensure_ascii=True, default=str)
        if error:
            row.error = error
        session.commit()


@contextmanager
def stage(
    job_id: str | None,
    stage_name: IngestStage,
    session_factory: Callable[[], Any] | None = None,
    publisher: StageEventPublisher | None = None,
) -> Iterator[StageHandle]:
    handle = StageHandle(stage=stage_name)
    if not job_id or session_factory is None:
        with chain_span(f"ingest.{stage_name.value}"):
            yield handle
        return

    _upsert_stage_row(
        session_factory=session_factory,
        job_id=job_id,
        stage_value=stage_name,
        status="running",
    )
    if publisher is not None:
        publisher(stage_name, "running", {}, None)
    with chain_span(f"ingest.{stage_name.value}"):
        try:
            yield handle
        except Exception as exc:
            error_text = str(exc)
            _upsert_stage_row(
                session_factory=session_factory,
                job_id=job_id,
                stage_value=stage_name,
                status="failed",
                finished_at=datetime.now(UTC),
                metrics=handle.metrics,
                error=error_text,
            )
            if publisher is not None:
                publisher(stage_name, "failed", dict(handle.metrics), error_text)
            raise
        _upsert_stage_row(
            session_factory=session_factory,
            job_id=job_id,
            stage_value=stage_name,
            status="completed",
            finished_at=datetime.now(UTC),
            metrics=handle.metrics,
        )
        if publisher is not None:
            publisher(stage_name, "completed", dict(handle.metrics), None)
