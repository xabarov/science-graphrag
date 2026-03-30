"""Live stack checks (Neo4j + Qdrant + Postgres); opt-in via service availability."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from science_graphrag.config import Settings, get_settings
from science_graphrag.ingestion.pipeline import ingest_document, run_ingest_batch_cli
from science_graphrag.storage.db import init_db
from science_graphrag.storage.models_orm import DocumentRecord
from science_graphrag.storage.neo4j_store import Neo4jGraphStore


def _services_available() -> bool:
    settings = get_settings()
    try:
        neo = Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
        neo.ensure_schema()
        neo.close()
    except Exception:  # noqa: BLE001
        return False
    try:
        client = QdrantClient(url=settings.qdrant_url, check_compatibility=False)
        client.get_collections()
    except Exception:  # noqa: BLE001
        return False
    return True


def _postgres_available() -> bool:
    settings = get_settings()
    try:
        engine = create_engine(settings.database_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
    except Exception:  # noqa: BLE001
        return False
    return True


def _full_stack_available() -> bool:
    return _services_available() and _postgres_available()


@pytest.mark.integration
def test_full_ingest_writes_work_node(tmp_path: Path) -> None:
    if not _services_available():
        pytest.skip("Neo4j or Qdrant not reachable (integration)")

    coll = f"itest-{uuid.uuid4().hex[:12]}"
    root = tmp_path / "data"
    settings = Settings(
        extraction_llm_api_key=None,
        extraction_llm_enabled=False,
        artifact_root=root / "artifacts",
        blob_root=root / "blobs",
        qdrant_collection=coll,
        reuse_cached_markdown=False,
    )
    md = tmp_path / "tiny_integration.md"
    md.write_text(
        "\n".join(
            [
                "# Tiny Integration Title",
                "",
                "## Abstract",
                "",
                "We validate ingest end-to-end.",
                "",
                "## References",
                "",
                "[1] A. Author. Sample. Nature 2020. 10.1000/182.",
                "",
            ],
        ),
        encoding="utf-8",
    )

    _doc_id, work_id = ingest_document(md, settings=settings, session=None)

    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    try:
        with driver.session() as session:
            row = session.run(
                "MATCH (w:Work {id: $id}) RETURN w.title AS t",
                id=work_id,
            ).single()
            assert row is not None
            assert row["t"] is not None
            neo_audit = Neo4jGraphStore(
                settings.neo4j_uri,
                settings.neo4j_user,
                settings.neo4j_password,
            )
            try:
                violations = neo_audit.find_work_dedup_violations()
            finally:
                neo_audit.close()
    finally:
        driver.close()

    assert isinstance(violations, list)
    assert not violations, f"unexpected Work dedup violations: {violations}"


def _integration_settings(tmp_path: Path, *, qdrant_suffix: str) -> Settings:
    root = tmp_path / "data"
    return Settings(
        extraction_llm_api_key=None,
        extraction_llm_enabled=False,
        artifact_root=root / "artifacts",
        blob_root=root / "blobs",
        qdrant_collection=f"itest-{qdrant_suffix}",
        reuse_cached_markdown=False,
    )


@pytest.mark.integration
def test_ingest_persists_document_to_postgres(tmp_path: Path) -> None:
    if not _full_stack_available():
        pytest.skip("Neo4j, Qdrant, or Postgres not reachable (integration)")

    settings = _integration_settings(tmp_path, qdrant_suffix=uuid.uuid4().hex[:12])
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    init_db(engine)
    factory = sessionmaker(bind=engine)

    md = tmp_path / "postgres_integration.md"
    md.write_text(
        "\n".join(
            [
                "# Postgres Integration Title",
                "",
                "## Abstract",
                "",
                "We validate SQL persistence.",
                "",
                "## References",
                "",
                "[1] A. Author. Sample. Nature 2020. 10.1000/182.",
                "",
            ],
        ),
        encoding="utf-8",
    )

    with factory() as db_session:
        with db_session.begin():
            doc_id, work_id = ingest_document(md, settings=settings, session=db_session)

    with factory() as read_session:
        row = read_session.execute(
            select(DocumentRecord).where(DocumentRecord.id == doc_id)
        ).scalar_one_or_none()

    assert row is not None
    assert row.sha256
    assert work_id


@pytest.mark.integration
def test_ingest_corpus_batch_two_files(tmp_path: Path) -> None:
    if not _full_stack_available():
        pytest.skip("Neo4j, Qdrant, or Postgres not reachable (integration)")

    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "one.md").write_text(
        "\n".join(
            [
                "# One",
                "## Abstract",
                "A.",
                "## References",
                "[1] Doe. Paper. 2019. 10.1000/one.",
            ],
        ),
        encoding="utf-8",
    )
    (corpus / "two.md").write_text(
        "\n".join(
            [
                "# Two",
                "## Abstract",
                "B.",
                "## References",
                "[1] Roe. Study. 2020. 10.1000/two.",
            ],
        ),
        encoding="utf-8",
    )

    root = tmp_path / "data"
    settings = Settings(
        extraction_llm_api_key=None,
        extraction_llm_enabled=False,
        artifact_root=root / "artifacts",
        blob_root=root / "blobs",
        qdrant_collection=f"itest-corpus-{uuid.uuid4().hex[:12]}",
        reuse_cached_markdown=False,
    )
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    init_db(engine)

    rows = run_ingest_batch_cli(corpus, continue_on_error=False, settings=settings)
    assert len(rows) == 2
    assert all(r.get("error") is None for r in rows)
    doc_ids = [r["document_id"] for r in rows]
    assert len(doc_ids) == 2
    assert len(set(doc_ids)) == 2

    factory = sessionmaker(bind=engine)
    with factory() as read_session:
        for did in doc_ids:
            row = read_session.execute(
                select(DocumentRecord).where(DocumentRecord.id == did)
            ).scalar_one_or_none()
            assert row is not None
