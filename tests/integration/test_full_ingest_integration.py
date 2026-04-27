"""Live stack checks (Neo4j + Qdrant + Postgres); opt-in via service availability."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from science_graphrag.config import Settings, get_settings
from science_graphrag.ingestion.embeddings import resolve_embedder, resolve_embedding_dim
from science_graphrag.ingestion.pipeline import ingest_document, run_ingest_batch_cli
from science_graphrag.storage.db import init_db
from science_graphrag.storage.models_orm import DocumentRecord
from science_graphrag.storage.neo4j_store import Neo4jGraphStore


def _isolated_offline_ingest_settings(tmp_path: Path, *, suffix: str) -> Settings:
    """
    Settings for live ingest integration without touching shared Qdrant embedding collections.

    Ingest writes chunk vectors to ``qdrant_collection`` and work-summary vectors to
    ``qdrant_work_embeddings_collection``. If only the chunk collection is unique but work
    vectors still target the default ``work_embeddings``, a pre-existing collection may have
    been created for OpenRouter (e.g. 1024) while offline ingest uses hash vectors (384) —
    Qdrant then rejects upserts with a dim mismatch.

    Constructing ``Settings(extraction_llm_api_key=None, ...)`` is unreliable here because
    pydantic-settings merges init, then ``.env``, then process env (see
    ``settings_customise_sources`` in ``science_graphrag/config.py``), so explicit constructor
    kwargs can be overwritten.
    ``get_settings().model_copy(update=...)`` keeps Neo4j/Qdrant/Postgres URLs from the operator
    environment while forcing offline embeddings and per-run Qdrant collection names.
    """

    root = tmp_path / "data"
    safe = "".join(c for c in suffix if c.isalnum()) or uuid.uuid4().hex[:12]
    base = get_settings()
    return base.model_copy(
        update={
            "extraction_llm_api_key": None,
            "benchmark_teacher_llm_api_key": None,
            "openrouter_embedding_model": None,
            "embedding_model": None,
            "extraction_llm_enabled": False,
            "artifact_root": root / "artifacts",
            "blob_root": root / "blobs",
            "qdrant_collection": f"itest-{safe}-chunks",
            "qdrant_work_embeddings_collection": f"itest-{safe}-work",
            "qdrant_claims_collection": f"itest-{safe}-claims",
            "qdrant_author_embeddings_collection": f"itest-{safe}-author",
            "reuse_cached_markdown": False,
        },
    )


def test_isolated_offline_ingest_settings_hash_embeddings_and_unique_qdrant_collections(
    tmp_path: Path,
) -> None:
    """Regression guard: integration ingest must not share prod-like Qdrant collection names."""

    suf = uuid.uuid4().hex[:12]
    settings = _isolated_offline_ingest_settings(tmp_path, suffix=suf)
    assert settings.qdrant_collection == f"itest-{suf}-chunks"
    assert settings.qdrant_work_embeddings_collection == f"itest-{suf}-work"
    assert settings.qdrant_claims_collection == f"itest-{suf}-claims"
    assert settings.qdrant_author_embeddings_collection == f"itest-{suf}-author"
    assert resolve_embedding_dim(settings=settings) == 384
    assert resolve_embedder(settings).dim == 384


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
    """Ingest creates a :Work in Neo4j and does not introduce dedup violations for that work."""
    if not _services_available():
        pytest.skip("Neo4j or Qdrant not reachable (integration)")

    suf = uuid.uuid4().hex[:12]
    settings = _isolated_offline_ingest_settings(tmp_path, suffix=suf)
    client = QdrantClient(url=settings.qdrant_url, check_compatibility=False)
    try:
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
        # Integration environment can contain historical violations from prior runs.
        # This test only fails when the newly ingested work participates in a violation.
        violations_for_new_work = [
            v for v in violations if work_id in {str(x) for x in (v.get("work_ids") or [])}
        ]
        assert (
            not violations_for_new_work
        ), f"new work entered dedup violations: {violations_for_new_work}"
    finally:
        for name in (
            settings.qdrant_collection,
            settings.qdrant_work_embeddings_collection,
        ):
            try:
                client.delete_collection(collection_name=name)
            except Exception:  # noqa: BLE001
                pass
        client.close()


@pytest.mark.integration
def test_full_ingest_qdrant_chunk_payload_contract(tmp_path: Path) -> None:
    """Chunk points must carry retrieval/provenance payload keys after ingest."""
    if not _services_available():
        pytest.skip("Neo4j or Qdrant not reachable (integration)")

    suf = f"payload{uuid.uuid4().hex[:12]}"
    settings = _isolated_offline_ingest_settings(tmp_path, suffix=suf)
    coll = settings.qdrant_collection
    md_path = tmp_path / "qdrant_payload.md"
    md_path.write_text(
        "\n".join(
            [
                "# Qdrant Payload Title",
                "",
                "## Abstract",
                "",
                "Chunk payload contract check.",
                "",
                "## References",
                "",
                "[1] B. Author. Example. Science 2021. 10.1000/payload.",
                "",
            ],
        ),
        encoding="utf-8",
    )

    doc_id, work_id = ingest_document(md_path, settings=settings, session=None)
    client = QdrantClient(url=settings.qdrant_url, check_compatibility=False)
    try:
        flt = Filter(
            must=[FieldCondition(key="document_id", match=MatchValue(value=doc_id))],
        )
        records, _ = client.scroll(
            collection_name=coll,
            scroll_filter=flt,
            limit=64,
            with_payload=True,
            with_vectors=False,
        )
        assert records, "expected at least one chunk point in Qdrant"
        for rec in records:
            payload = rec.payload or {}
            fp = payload.get("chunk_fingerprint")
            assert fp and isinstance(fp, str) and len(fp) == 64
            assert isinstance(payload.get("section_path"), str)
            so = payload.get("start_offset")
            eo = payload.get("end_offset")
            assert isinstance(so, int) and isinstance(eo, int) and so < eo
            assert payload.get("chunk_kind")
            assert payload.get("document_id") == doc_id
            assert payload.get("work_id") == work_id
            assert isinstance(payload.get("text"), str) and payload.get("text")
    finally:
        for name in (
            coll,
            settings.qdrant_work_embeddings_collection,
        ):
            try:
                client.delete_collection(collection_name=name)
            except Exception:  # noqa: BLE001
                pass


@pytest.mark.integration
def test_ingest_persists_document_to_postgres(tmp_path: Path) -> None:
    """Ingest with a DB session persists ``DocumentRecord`` to Postgres."""
    if not _full_stack_available():
        pytest.skip("Neo4j, Qdrant, or Postgres not reachable (integration)")

    settings = _isolated_offline_ingest_settings(tmp_path, suffix=uuid.uuid4().hex[:12])
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
    """Batch CLI ingest persists two markdown files with distinct document ids."""
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

    settings = _isolated_offline_ingest_settings(tmp_path, suffix=f"corpus{uuid.uuid4().hex[:12]}")
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    init_db(engine)

    q_client = QdrantClient(url=settings.qdrant_url, check_compatibility=False)
    try:
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
    finally:
        for name in (
            settings.qdrant_collection,
            settings.qdrant_work_embeddings_collection,
        ):
            try:
                q_client.delete_collection(collection_name=name)
            except Exception:  # noqa: BLE001
                pass
        q_client.close()
