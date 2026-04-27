"""Neo4j schema setup: constraints and indexes."""

from __future__ import annotations

import logging

from science_graphrag.storage.neo4j.client import _Neo4jClient

LOGGER = logging.getLogger(__name__)


def ensure_schema(client: _Neo4jClient) -> None:
    """Apply all constraints and indexes (idempotent)."""
    stmts = [
        "CREATE CONSTRAINT work_id_unique IF NOT EXISTS FOR (w:Work) REQUIRE w.id IS UNIQUE",
        "CREATE CONSTRAINT author_id_unique IF NOT EXISTS FOR (a:Author) REQUIRE a.id IS UNIQUE",
        (
            "CREATE CONSTRAINT authorship_id_unique IF NOT EXISTS "
            "FOR (x:Authorship) REQUIRE x.id IS UNIQUE"
        ),
        (
            "CREATE CONSTRAINT institution_id_unique IF NOT EXISTS "
            "FOR (i:Institution) REQUIRE i.id IS UNIQUE"
        ),
        "CREATE CONSTRAINT venue_id_unique IF NOT EXISTS FOR (v:Venue) REQUIRE v.id IS UNIQUE",
        "CREATE CONSTRAINT method_id_unique IF NOT EXISTS FOR (m:Method) REQUIRE m.id IS UNIQUE",
        (
            "CREATE CONSTRAINT method_evidence_id_unique IF NOT EXISTS "
            "FOR (e:MethodEvidence) REQUIRE e.id IS UNIQUE"
        ),
        "CREATE CONSTRAINT dataset_id_unique IF NOT EXISTS FOR (d:Dataset) REQUIRE d.id IS UNIQUE",
        (
            "CREATE CONSTRAINT workspace_id_unique IF NOT EXISTS "
            "FOR (ws:Workspace) REQUIRE ws.id IS UNIQUE"
        ),
        "CREATE CONSTRAINT claim_id_unique IF NOT EXISTS FOR (c:Claim) REQUIRE c.id IS UNIQUE",
        (
            "CREATE CONSTRAINT evidence_id_unique IF NOT EXISTS "
            "FOR (e:Evidence) REQUIRE e.id IS UNIQUE"
        ),
        "CREATE INDEX claim_type_idx IF NOT EXISTS FOR (c:Claim) ON (c.claim_type)",
        "CREATE INDEX claim_polarity_idx IF NOT EXISTS FOR (c:Claim) ON (c.polarity)",
        (
            "CREATE INDEX evidence_chunk_fp_idx IF NOT EXISTS "
            "FOR (e:Evidence) ON (e.chunk_fingerprint)"
        ),
        (
            "CREATE FULLTEXT INDEX claim_normalized_fulltext IF NOT EXISTS "
            "FOR (n:Claim) ON EACH [n.normalized_text]"
        ),
        "CREATE INDEX work_year IF NOT EXISTS FOR (w:Work) ON (w.publication_year)",
        "CREATE INDEX work_fingerprint IF NOT EXISTS FOR (w:Work) ON (w.fingerprint)",
        "CREATE INDEX work_normalized_title IF NOT EXISTS FOR (w:Work) ON (w.normalized_title)",
        "CREATE INDEX work_doi IF NOT EXISTS FOR (w:Work) ON (w.doi)",
        "CREATE INDEX work_arxiv_id IF NOT EXISTS FOR (w:Work) ON (w.arxiv_id)",
        (
            "CREATE INDEX author_normalized_name IF NOT EXISTS "
            "FOR (a:Author) ON (a.normalized_name)"
        ),
        (
            "CREATE INDEX institution_normalized_name IF NOT EXISTS "
            "FOR (i:Institution) ON (i.normalized_name)"
        ),
        "CREATE INDEX institution_ror_id IF NOT EXISTS FOR (i:Institution) ON (i.ror_id)",
        "CREATE INDEX venue_issn IF NOT EXISTS FOR (v:Venue) ON (v.issn)",
        "CREATE INDEX method_normalized IF NOT EXISTS FOR (m:Method) ON (m.normalized_name)",
        "CREATE INDEX dataset_normalized IF NOT EXISTS FOR (d:Dataset) ON (d.normalized_name)",
        (
            "CREATE INDEX work_year_type IF NOT EXISTS "
            "FOR (w:Work) ON (w.publication_year, w.work_type)"
        ),
        (
            "CREATE FULLTEXT INDEX works_title_abstract IF NOT EXISTS "
            "FOR (n:Work) ON EACH [n.title, n.abstract]"
        ),
        "CREATE FULLTEXT INDEX methods_text IF NOT EXISTS FOR (n:Method) ON EACH [n.name]",
        "CREATE FULLTEXT INDEX datasets_text IF NOT EXISTS FOR (n:Dataset) ON EACH [n.name]",
        (
            "CREATE FULLTEXT INDEX authors_text IF NOT EXISTS "
            "FOR (n:Author) ON EACH [n.full_name, n.normalized_name]"
        ),
        (
            "CREATE FULLTEXT INDEX institutions_text IF NOT EXISTS "
            "FOR (n:Institution) ON EACH [n.name, n.normalized_name]"
        ),
    ]
    with client.session() as session:
        for q in stmts:
            session.run(q)
        try:
            session.run(
                "CREATE VECTOR INDEX work_title_emb IF NOT EXISTS "
                "FOR (w:Work) ON (w.title_embedding) OPTIONS {indexConfig:{"
                "`vector.dimensions`: 384, `vector.similarity_function`: 'cosine'}}"
            )
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Skipping work_title_emb vector index creation: %s", exc)
