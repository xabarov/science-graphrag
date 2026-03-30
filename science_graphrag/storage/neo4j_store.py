from __future__ import annotations

from typing import Any

from neo4j import Driver, GraphDatabase

from science_graphrag.domain.authorship_ids import canonical_author_node_id
from science_graphrag.domain.models import AuthorshipDraft, WorkDraft


class Neo4jGraphStore:
    def __init__(self, uri: str, user: str, password: str) -> None:
        self._driver: Driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self._driver.close()

    def wipe_all(self) -> None:
        """Delete all nodes and relationships (dev / benchmark reset)."""
        with self._driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

    def ensure_schema(self) -> None:
        stmts = [
            (
                "CREATE CONSTRAINT work_id_unique IF NOT EXISTS "
                "FOR (w:Work) REQUIRE w.id IS UNIQUE"
            ),
            (
                "CREATE CONSTRAINT author_id_unique IF NOT EXISTS "
                "FOR (a:Author) REQUIRE a.id IS UNIQUE"
            ),
            (
                "CREATE CONSTRAINT authorship_id_unique IF NOT EXISTS "
                "FOR (x:Authorship) REQUIRE x.id IS UNIQUE"
            ),
            (
                "CREATE CONSTRAINT institution_id_unique IF NOT EXISTS "
                "FOR (i:Institution) REQUIRE i.id IS UNIQUE"
            ),
            (
                "CREATE CONSTRAINT venue_id_unique IF NOT EXISTS "
                "FOR (v:Venue) REQUIRE v.id IS UNIQUE"
            ),
        ]
        with self._driver.session() as session:
            for q in stmts:
                session.run(q)

    def find_work_id_by_doi(self, doi: str) -> str | None:
        q = "MATCH (w:Work {doi: $doi}) RETURN w.id AS id LIMIT 1"
        with self._driver.session() as session:
            rec = session.run(q, doi=doi).single()
            return rec["id"] if rec else None

    def find_work_id_by_fingerprint(self, fingerprint: str) -> str | None:
        q = "MATCH (w:Work {fingerprint: $fp}) RETURN w.id AS id LIMIT 1"
        with self._driver.session() as session:
            rec = session.run(q, fp=fingerprint).single()
            return rec["id"] if rec else None

    def find_work_id_by_arxiv(self, arxiv_id: str) -> str | None:
        q = "MATCH (w:Work {arxiv_id: $arxiv_id}) RETURN w.id AS id LIMIT 1"
        with self._driver.session() as session:
            rec = session.run(q, arxiv_id=arxiv_id).single()
            return rec["id"] if rec else None

    def upsert_work_layer1(
        self,
        work_id: str,
        draft: WorkDraft,
        authorships: list[AuthorshipDraft],
        venue_id: str | None,
        institution_nodes: list[tuple[str, str, list[str]]],
    ) -> None:
        """
        institution_nodes: tuples (institution_id, name, ror_id | None) aligned to authorship index.
        """
        props = {
            "id": work_id,
            "title": draft.title,
            "normalized_title": draft.normalized_title,
            "abstract": draft.abstract,
            "publication_year": draft.publication_year,
            "doi": draft.doi,
            "arxiv_id": draft.arxiv_id,
            "language": draft.language,
            "venue_name": draft.venue_name,
            "work_type": draft.work_type.value if draft.work_type else None,
            "openalex_id": draft.openalex_id,
            "fingerprint": draft.fingerprint,
            "ingestion_confidence": draft.ingestion_confidence,
        }
        props = {k: v for k, v in props.items() if v is not None}

        with self._driver.session() as session:
            session.execute_write(
                self._write_work_tx,
                props,
                authorships,
                venue_id,
                institution_nodes,
            )

    @staticmethod
    def _write_work_tx(
        tx,
        work_props: dict[str, Any],
        authorships: list[AuthorshipDraft],
        venue_id: str | None,
        institution_nodes: list[tuple[str, str, str | None]],
    ) -> None:
        tx.run(
            """
            MERGE (w:Work {id: $wid})
            SET w += $props
            """,
            wid=work_props["id"],
            props=work_props,
        )
        if venue_id:
            tx.run(
                """
                MATCH (w:Work {id: $wid})
                MERGE (v:Venue {id: $vid})
                SET v.name = $vname
                MERGE (w)-[:PUBLISHED_IN]->(v)
                """,
                wid=work_props["id"],
                vid=venue_id,
                vname=work_props.get("venue_name") or "Unknown venue",
            )

        # Clear old authorship pattern for idempotent re-run (MVP)
        tx.run(
            """
            MATCH (w:Work {id: $wid})-[:HAS_AUTHORSHIP]->(a:Authorship)
            DETACH DELETE a
            """,
            wid=work_props["id"],
        )

        for idx, ash in enumerate(authorships):
            aid = canonical_author_node_id(ash.author_raw_name)
            asid = work_props["id"] + f":ash:{ash.author_position}"
            tx.run(
                """
                MATCH (w:Work {id: $wid})
                MERGE (auth:Author {id: $aid})
                SET auth.full_name = $name
                MERGE (x:Authorship {id: $asid})
                SET x.author_position = $pos,
                    x.raw_affiliation = $rawaff,
                    x.extraction_confidence = $conf
                MERGE (w)-[:HAS_AUTHORSHIP]->(x)-[:OF_AUTHOR]->(auth)
                """,
                wid=work_props["id"],
                aid=aid,
                name=ash.author_raw_name,
                asid=asid,
                pos=ash.author_position,
                rawaff=(ash.raw_affiliations[0] if ash.raw_affiliations else ""),
                conf=0.5,
            )
            if idx < len(institution_nodes):
                iid, iname, ror = institution_nodes[idx]
                if iid and iname:
                    tx.run(
                        """
                        MATCH (x:Authorship {id: $asid})
                        MERGE (i:Institution {id: $iid})
                        SET i.name = $iname, i.ror_id = coalesce($ror, i.ror_id)
                        MERGE (x)-[:AFFILIATED_WITH]->(i)
                        """,
                        asid=asid,
                        iid=iid,
                        iname=iname,
                        ror=ror,
                    )

    def merge_cites(self, from_work_id: str, to_work_id: str) -> None:
        q = """
        MATCH (a:Work {id: $from_id})
        MATCH (b:Work {id: $to_id})
        MERGE (a)-[:CITES]->(b)
        """
        with self._driver.session() as session:
            session.run(q, from_id=from_work_id, to_id=to_work_id)

    def merge_related_version(self, a_id: str, b_id: str) -> None:
        q = """
        MATCH (a:Work {id: $a})
        MATCH (b:Work {id: $b})
        MERGE (a)-[:RELATED_VERSION_OF]->(b)
        """
        with self._driver.session() as session:
            session.run(q, a=a_id, b=b_id)

    def upsert_minimal_work(
        self,
        work_id: str,
        *,
        title: str | None,
        publication_year: int | None,
        doi: str | None,
        arxiv_id: str | None = None,
        fingerprint: str | None,
        openalex_id: str | None,
        ingestion_confidence: float,
    ) -> None:
        props: dict[str, Any] = {
            "id": work_id,
            "ingestion_confidence": ingestion_confidence,
        }
        if title is not None:
            props["title"] = title
        if publication_year is not None:
            props["publication_year"] = publication_year
        if doi:
            props["doi"] = doi
        if arxiv_id:
            props["arxiv_id"] = arxiv_id
        if fingerprint:
            props["fingerprint"] = fingerprint
        if openalex_id:
            props["openalex_id"] = openalex_id
        q = "MERGE (w:Work {id: $id}) SET w += $props"
        with self._driver.session() as session:
            session.run(q, id=work_id, props=props)

    def find_work_dedup_violations(self) -> list[dict[str, Any]]:
        """
        Return clusters where multiple :Work nodes share the same dedup key.

        Only non-empty property values are considered (DOI, OpenAlex id, fingerprint, arXiv id).
        """

        queries: list[tuple[str, str]] = [
            (
                "doi",
                """
                MATCH (w:Work)
                WHERE w.doi IS NOT NULL AND trim(toString(w.doi)) <> ''
                WITH w.doi AS k, collect(DISTINCT w.id) AS ids
                WHERE size(ids) > 1
                RETURN k AS dedup_key, ids
                """,
            ),
            (
                "openalex_id",
                """
                MATCH (w:Work)
                WHERE w.openalex_id IS NOT NULL AND trim(toString(w.openalex_id)) <> ''
                WITH w.openalex_id AS k, collect(DISTINCT w.id) AS ids
                WHERE size(ids) > 1
                RETURN k AS dedup_key, ids
                """,
            ),
            (
                "fingerprint",
                """
                MATCH (w:Work)
                WHERE w.fingerprint IS NOT NULL AND trim(toString(w.fingerprint)) <> ''
                WITH w.fingerprint AS k, collect(DISTINCT w.id) AS ids
                WHERE size(ids) > 1
                RETURN k AS dedup_key, ids
                """,
            ),
            (
                "arxiv_id",
                """
                MATCH (w:Work)
                WHERE w.arxiv_id IS NOT NULL AND trim(toString(w.arxiv_id)) <> ''
                WITH w.arxiv_id AS k, collect(DISTINCT w.id) AS ids
                WHERE size(ids) > 1
                RETURN k AS dedup_key, ids
                """,
            ),
        ]
        out: list[dict[str, Any]] = []
        with self._driver.session() as session:
            for kind, cypher in queries:
                for rec in session.run(cypher):
                    out.append(
                        {
                            "kind": kind,
                            "dedup_key": rec["dedup_key"],
                            "work_ids": list(rec["ids"]),
                        },
                    )
        return out
