"""Integration-style coverage for resume after embed failure (no layer1 Work churn)."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from science_graphrag.embeddings.errors import EmbeddingProviderUnavailableError
from science_graphrag.ingestion.checkpoint import parse_checkpoint, serialize_checkpoint
from science_graphrag.ingestion.resume_ingest import resume_document_ingest_stages
from science_graphrag.storage.db import init_db
from science_graphrag.storage.models_orm import DocumentRecord, IngestionRunRecord


class _LocalArtifactRoot:
    """Minimal store for resume harness (only paths used by resume ingest)."""

    def __init__(self, root: Path) -> None:
        self._root = root

    @property
    def root(self) -> Path:
        return self._root

    def exists(self, rel: Path) -> bool:
        return (self._root / rel).is_file()

    def read_text(self, rel: Path, encoding: str = "utf-8") -> str:
        return (self._root / rel).read_text(encoding=encoding)


class _NeoResumeHarness:
    """Tracks accidental layer1 writes — resume must not create duplicate Works."""

    def __init__(self) -> None:
        self.upsert_work_layer1_calls = 0

    def ensure_schema(self) -> None:
        return None

    def close(self) -> None:
        return None

    def detach_delete_claims_for_work(self, *_a: Any, **_kw: Any) -> None:
        return None

    def upsert_claims_with_evidence(self, *_a: Any, **_kw: Any) -> None:
        return None

    def upsert_work_layer1(self, *_a: Any, **_kw: Any) -> None:
        self.upsert_work_layer1_calls += 1


@pytest.fixture
def sqlite_session():
    engine = create_engine("sqlite:///:memory:")
    init_db(engine)
    factory = sessionmaker(bind=engine)
    with factory() as session:
        yield session


def test_resume_claims_embed_after_embed_failure_no_layer1_upsert(
    sqlite_session, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import science_graphrag.ingestion.resume_ingest as resume_mod
    from science_graphrag.config import Settings

    doc_id = str(uuid.uuid4())
    work_id = str(uuid.uuid4())
    norm_rel = Path("ingestion") / doc_id / "normalized.md"
    norm_path = tmp_path / norm_rel
    norm_path.parent.mkdir(parents=True, exist_ok=True)
    norm_path.write_text(
        "# Resume harness doc\n\n## Abstract\n\nShort body for chunking.\n",
        encoding="utf-8",
    )

    sqlite_session.add(
        DocumentRecord(
            id=doc_id,
            sha256="f" * 64,
            source_path="/fixture/resume.pdf",
            mime_type="application/pdf",
            work_id=work_id,
            ingest_checkpoint_json=serialize_checkpoint(parse_checkpoint(None)),
        ),
    )
    sqlite_session.commit()

    monkeypatch.setattr(
        resume_mod,
        "build_artifact_store",
        lambda _settings: _LocalArtifactRoot(tmp_path),
    )

    neo_harness = _NeoResumeHarness()

    def _neo_factory(*_a: Any, **_kw: Any) -> _NeoResumeHarness:
        return neo_harness

    monkeypatch.setattr(resume_mod, "Neo4jGraphStore", _neo_factory)

    monkeypatch.setattr(
        resume_mod,
        "run_extract_claims_stage",
        lambda **_kw: [],
    )

    embed_attempts = {"count": 0}

    def _fake_embed_phase(**_kwargs: Any) -> None:
        embed_attempts["count"] += 1
        if embed_attempts["count"] == 1:
            raise EmbeddingProviderUnavailableError("simulated embed outage")

    monkeypatch.setattr(resume_mod, "run_ingest_embed_qdrant_phase", _fake_embed_phase)

    settings = Settings(
        database_url="sqlite:///:memory:",
        neo4j_uri="bolt://unused",
        neo4j_user="u",
        neo4j_password="p",
        claims_extraction_enabled=True,
        extraction_llm_enabled=True,
    )

    with pytest.raises(EmbeddingProviderUnavailableError):
        resume_document_ingest_stages(
            document_id=doc_id,
            stages_csv="embed",
            settings=settings,
            session=sqlite_session,
        )

    assert embed_attempts["count"] == 1
    assert neo_harness.upsert_work_layer1_calls == 0

    row = sqlite_session.get(DocumentRecord, doc_id)
    assert row is not None
    ck_after_fail = parse_checkpoint(row.ingest_checkpoint_json)
    embed_stage = (ck_after_fail.get("stages") or {}).get("embed") or {}
    assert embed_stage.get("status") == "failed_retryable"

    failed_runs = sqlite_session.scalars(
        select(IngestionRunRecord).where(IngestionRunRecord.document_id == doc_id),
    ).all()
    assert any(r.status.startswith("failed") for r in failed_runs)

    out_work_id = resume_document_ingest_stages(
        document_id=doc_id,
        stages_csv="claims,embed",
        settings=settings,
        session=sqlite_session,
    )

    assert out_work_id == work_id
    assert embed_attempts["count"] == 2
    assert neo_harness.upsert_work_layer1_calls == 0

    sqlite_session.refresh(row)
    ck_done = parse_checkpoint(row.ingest_checkpoint_json)
    stages = ck_done.get("stages") or {}
    assert stages.get("extract_claims", {}).get("status") == "completed"
    assert stages.get("embed", {}).get("status") == "completed"
