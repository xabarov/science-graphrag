"""Postgres sha256 → document_id reuse and skip flag."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from science_graphrag.ingestion.pipeline import (
    SkippedDuplicateIngestError,
    _resolve_document_id_for_sha,
)
from science_graphrag.storage.db import init_db
from science_graphrag.storage.models_orm import DocumentRecord


@pytest.fixture
def sqlite_session():
    engine = create_engine("sqlite:///:memory:")
    init_db(engine)
    factory = sessionmaker(bind=engine)
    with factory() as session:
        yield session


def test_resolve_new_uuid_when_no_row(sqlite_session) -> None:
    sha = "a" * 64
    doc_id, reused = _resolve_document_id_for_sha(
        sqlite_session,
        sha,
        skip_existing_sha=False,
        force_new_document=False,
    )
    assert uuid.UUID(doc_id)
    assert reused is False


def test_resolve_reuses_when_sha_exists(sqlite_session) -> None:
    sha = "b" * 64
    fixed_id = str(uuid.uuid4())
    sqlite_session.add(
        DocumentRecord(
            id=fixed_id,
            sha256=sha,
            source_path="/old/path.pdf",
            mime_type="application/pdf",
        ),
    )
    sqlite_session.commit()
    doc_id, reused = _resolve_document_id_for_sha(
        sqlite_session,
        sha,
        skip_existing_sha=False,
        force_new_document=False,
    )
    assert doc_id == fixed_id
    assert reused is True


def test_resolve_skip_raises(sqlite_session) -> None:
    sha = "c" * 64
    fixed_id = str(uuid.uuid4())
    sqlite_session.add(
        DocumentRecord(
            id=fixed_id,
            sha256=sha,
            source_path="/x.pdf",
            mime_type="application/pdf",
        ),
    )
    sqlite_session.commit()
    with pytest.raises(SkippedDuplicateIngestError) as exc_info:
        _resolve_document_id_for_sha(
            sqlite_session,
            sha,
            skip_existing_sha=True,
            force_new_document=False,
        )
    assert exc_info.value.document_id == fixed_id
    assert exc_info.value.sha256 == sha


def test_force_new_document_ignores_table(sqlite_session) -> None:
    sha = "d" * 64
    sqlite_session.add(
        DocumentRecord(
            id=str(uuid.uuid4()),
            sha256=sha,
            source_path="/x.pdf",
            mime_type="application/pdf",
        ),
    )
    sqlite_session.commit()
    existing_id = sqlite_session.execute(select(DocumentRecord.id)).scalar_one()
    doc_id, reused = _resolve_document_id_for_sha(
        sqlite_session,
        sha,
        skip_existing_sha=False,
        force_new_document=True,
    )
    assert doc_id != existing_id
    assert reused is False
