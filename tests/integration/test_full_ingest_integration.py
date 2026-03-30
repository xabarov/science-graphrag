"""Live stack checks (Neo4j + Qdrant); opt-in via service availability."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from neo4j import GraphDatabase
from qdrant_client import QdrantClient

from science_graphrag.config import Settings, get_settings
from science_graphrag.ingestion.pipeline import ingest_document
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
