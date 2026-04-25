from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class DocumentRecord(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    source_path: Mapped[str] = mapped_column(Text)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    work_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )


class IngestionRunRecord(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), index=True)
    status: Mapped[str] = mapped_column(String(32), default="running")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class IngestJobRecordOrm(Base):
    __tablename__ = "ingest_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(String(36), index=True, unique=True)
    workspace_id: Mapped[str] = mapped_column(String(128), index=True)
    filename: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    message: Mapped[str] = mapped_column(Text, default="")
    progress_current: Mapped[int] = mapped_column(default=0)
    progress_total: Mapped[int] = mapped_column(default=100)
    logs: Mapped[str] = mapped_column(Text, default="")
    work_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    document_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    skipped_duplicate: Mapped[bool] = mapped_column(default=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    phoenix_trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    kind: Mapped[str] = mapped_column(String(32), default="single")
    parent_job_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    child_job_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def child_job_ids(self) -> list[str]:
        raw = (self.child_job_ids_json or "").strip() or "[]"
        try:
            data = json.loads(raw)
        except Exception:
            return []
        if not isinstance(data, list):
            return []
        return [str(x) for x in data if x]

    @child_job_ids.setter
    def child_job_ids(self, value: list[str] | None) -> None:
        self.child_job_ids_json = json.dumps(
            [str(x) for x in (value or []) if x], ensure_ascii=True
        )


class IngestJobStageOrm(Base):
    __tablename__ = "ingest_job_stages"
    __table_args__ = (UniqueConstraint("job_id", "stage", name="uq_ingest_job_stage"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(String(36), index=True)
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="running")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metrics_json: Mapped[str] = mapped_column(Text, default="{}")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class IngestJobEventOrm(Base):
    __tablename__ = "ingest_job_events"
    __table_args__ = (UniqueConstraint("job_id", "seq", name="uq_ingest_job_event_seq"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(String(36), index=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )


class DedupJobRecordOrm(Base):
    __tablename__ = "dedup_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(String(36), index=True, unique=True)
    workspace_id: Mapped[str] = mapped_column(String(128), index=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    message: Mapped[str] = mapped_column(Text, default="")
    conflicts_inserted: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkDedupConflict(Base):
    """Postgres queue for near-duplicate Work pairs (Wave L)."""

    __tablename__ = "work_dedup_conflicts"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "fingerprint",
            name="uq_work_dedup_workspace_fingerprint",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(String(128), index=True)
    work_id_a: Mapped[str] = mapped_column(String(256), index=True)
    work_id_b: Mapped[str] = mapped_column(String(256), index=True)
    similarity_score: Mapped[float] = mapped_column(Float, default=0.0)
    check_mode: Mapped[str] = mapped_column(String(32), default="embedding")
    llm_same_work: Mapped[bool | None] = mapped_column(nullable=True)
    llm_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    keep_work_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkDedupMergeLog(Base):
    """Audit log after a successful canonical work merge."""

    __tablename__ = "work_dedup_merge_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(String(128), index=True)
    keep_work_id: Mapped[str] = mapped_column(String(256), index=True)
    drop_work_id: Mapped[str] = mapped_column(String(256), index=True)
    conflict_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )


class AuthorDedupConflict(Base):
    """Postgres queue for near-duplicate Author nodes (Wave L2)."""

    __tablename__ = "author_dedup_conflicts"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "fingerprint",
            name="uq_author_dedup_workspace_fingerprint",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(String(128), index=True)
    author_id_a: Mapped[str] = mapped_column(String(256), index=True)
    author_id_b: Mapped[str] = mapped_column(String(256), index=True)
    similarity_score: Mapped[float] = mapped_column(Float, default=0.0)
    check_mode: Mapped[str] = mapped_column(String(32), default="embedding")
    llm_same_author: Mapped[bool | None] = mapped_column(nullable=True)
    llm_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    keep_author_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EntityDedupConflict(Base):
    """Unified Postgres review queue for all entity types (Wave T)."""

    __tablename__ = "entity_dedup_conflicts"
    __table_args__ = (
        UniqueConstraint("entity_type", "fingerprint", name="uq_entity_dedup_type_fingerprint"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_type: Mapped[str] = mapped_column(String(32), index=True)
    entity_id_a: Mapped[str] = mapped_column(String(256), index=True)
    entity_id_b: Mapped[str] = mapped_column(String(256), index=True)
    similarity_score: Mapped[float] = mapped_column(Float, default=0.0)
    check_mode: Mapped[str] = mapped_column(String(32), default="embedding")
    llm_same_entity: Mapped[bool | None] = mapped_column(nullable=True)
    llm_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    keep_entity_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    workspace_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
