"""Runtime context and stage tracking for the ingestion pipeline."""

from __future__ import annotations

import json
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Iterator

from sqlalchemy.dialects.postgresql import insert as pg_insert

from science_graphrag.observability.phoenix_tracer import chain_span
from science_graphrag.storage.models_orm import IngestJobStageOrm
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.storage.qdrant_store import QdrantChunkStore
from science_graphrag.storage.raw_blob_store import RawBlobStorePort, build_raw_blob_store

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from science_graphrag.config import Settings


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


@dataclass
class IngestRunContext:
    """Shared runtime context for one ingest run."""

    settings: "Settings"
    source_path: Path
    session: "Session | None" = None
    job_id: str | None = None
    parent_job_id: str | None = None
    stage_session_factory: Callable[[], Any] | None = None
    stage_event_publisher: StageEventPublisher | None = None
    ingest_workspace_ids: list[str] = field(default_factory=list)

    _neo4j_store: Neo4jGraphStore | None = field(default=None, init=False, repr=False)
    _qdrant_store: QdrantChunkStore | None = field(default=None, init=False, repr=False)
    _blob_store: RawBlobStorePort | None = field(default=None, init=False, repr=False)
    phoenix_tracer: Any | None = None

    @property
    def neo4j_store(self) -> Neo4jGraphStore:
        if self._neo4j_store is None:
            self._neo4j_store = Neo4jGraphStore(
                self.settings.neo4j_uri,
                self.settings.neo4j_user,
                self.settings.neo4j_password,
            )
        return self._neo4j_store

    @property
    def qdrant_store(self) -> QdrantChunkStore:
        if self._qdrant_store is None:
            self._qdrant_store = QdrantChunkStore(
                self.settings.qdrant_url,
                self.settings.qdrant_collection,
                vector_dim=1,
            )
        return self._qdrant_store

    @property
    def blob_store(self) -> RawBlobStorePort:
        if self._blob_store is None:
            self._blob_store = build_raw_blob_store(self.settings)
        return self._blob_store

    @contextmanager
    def stage(self, stage_name: IngestStage) -> Iterator[StageHandle]:
        with stage(
            self.job_id,
            stage_name,
            session_factory=self.stage_session_factory,
            publisher=self.stage_event_publisher,
        ) as handle:
            yield handle

    def close(self) -> None:
        if self._neo4j_store is not None:
            self._neo4j_store.close()
            self._neo4j_store = None


def build_ingest_run_context(
    *,
    settings: "Settings",
    source_path: Path,
    session: "Session | None" = None,
    job_id: str | None = None,
    parent_job_id: str | None = None,
    stage_session_factory: Callable[[], Any] | None = None,
    stage_event_publisher: StageEventPublisher | None = None,
    ingest_workspace_ids: list[str] | None = None,
) -> IngestRunContext:
    return IngestRunContext(
        settings=settings,
        source_path=source_path,
        session=session,
        job_id=job_id,
        parent_job_id=parent_job_id,
        stage_session_factory=stage_session_factory,
        stage_event_publisher=stage_event_publisher,
        ingest_workspace_ids=list(ingest_workspace_ids or []),
    )


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
    now = datetime.now(UTC)
    metrics_json_str = json.dumps(metrics or {}, ensure_ascii=True, default=str)
    values: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "job_id": job_id,
        "stage": stage_value.value,
        "status": status,
        "started_at": now,
        "finished_at": finished_at,
        "metrics_json": metrics_json_str,
        "error": error or None,
    }
    update_set: dict[str, Any] = {"status": status}
    if finished_at is not None:
        update_set["finished_at"] = finished_at
    if metrics is not None:
        update_set["metrics_json"] = metrics_json_str
    if error:
        update_set["error"] = error

    stmt = (
        pg_insert(IngestJobStageOrm)
        .values(**values)
        .on_conflict_do_update(
            index_elements=["job_id", "stage"],
            set_=update_set,
        )
    )
    with session_factory() as session:
        session.execute(stmt)
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
