from __future__ import annotations

import json
import re
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from neo4j import Driver, GraphDatabase, NotificationClassification

from science_graphrag.domain.authorship_ids import canonical_author_node_id
from science_graphrag.domain.models import AuthorshipDraft, WorkDraft
from science_graphrag.domain.semantic_models import SemanticExtractionV1
from science_graphrag.ingestion.claims.models import ClaimDraft


class Neo4jGraphStore:
    def __init__(self, uri: str, user: str, password: str) -> None:
        self._driver: Driver = GraphDatabase.driver(
            uri,
            auth=(user, password),
            notifications_disabled_classifications=[NotificationClassification.UNRECOGNIZED],
            # Fail fast when Bolt is unreachable so API handlers (e.g. /v1/workspaces) do not hang the UI.
            connection_timeout=15.0,
            connection_acquisition_timeout=20.0,
        )

    def close(self) -> None:
        self._driver.close()

    @contextmanager
    def session(self) -> Iterator[Any]:
        with self._driver.session() as session:
            yield session

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
            (
                "CREATE CONSTRAINT method_id_unique IF NOT EXISTS "
                "FOR (m:Method) REQUIRE m.id IS UNIQUE"
            ),
            (
                "CREATE CONSTRAINT dataset_id_unique IF NOT EXISTS "
                "FOR (d:Dataset) REQUIRE d.id IS UNIQUE"
            ),
            (
                "CREATE CONSTRAINT workspace_id_unique IF NOT EXISTS "
                "FOR (ws:Workspace) REQUIRE ws.id IS UNIQUE"
            ),
            (
                "CREATE CONSTRAINT claim_id_unique IF NOT EXISTS "
                "FOR (c:Claim) REQUIRE c.id IS UNIQUE"
            ),
            (
                "CREATE CONSTRAINT evidence_id_unique IF NOT EXISTS "
                "FOR (e:Evidence) REQUIRE e.id IS UNIQUE"
            ),
            "CREATE INDEX claim_type_idx IF NOT EXISTS FOR (c:Claim) ON (c.claim_type)",
            "CREATE INDEX claim_polarity_idx IF NOT EXISTS FOR (c:Claim) ON (c.polarity)",
            "CREATE INDEX evidence_chunk_fp_idx IF NOT EXISTS FOR (e:Evidence) ON (e.chunk_fingerprint)",
            (
                "CREATE FULLTEXT INDEX claim_normalized_fulltext IF NOT EXISTS "
                "FOR (n:Claim) ON EACH [n.normalized_text]"
            ),
            # Wave Q — range + composite + fulltext (idempotent; see neo4j_migrations/002_indexes_and_fulltext.cypher)
            "CREATE INDEX work_year IF NOT EXISTS FOR (w:Work) ON (w.publication_year)",
            "CREATE INDEX work_fingerprint IF NOT EXISTS FOR (w:Work) ON (w.fingerprint)",
            "CREATE INDEX work_normalized_title IF NOT EXISTS FOR (w:Work) ON (w.normalized_title)",
            "CREATE INDEX work_doi IF NOT EXISTS FOR (w:Work) ON (w.doi)",
            "CREATE INDEX work_arxiv_id IF NOT EXISTS FOR (w:Work) ON (w.arxiv_id)",
            "CREATE INDEX author_normalized_name IF NOT EXISTS FOR (a:Author) ON (a.normalized_name)",
            "CREATE INDEX institution_normalized_name IF NOT EXISTS FOR (i:Institution) ON (i.normalized_name)",
            "CREATE INDEX institution_ror_id IF NOT EXISTS FOR (i:Institution) ON (i.ror_id)",
            "CREATE INDEX venue_issn IF NOT EXISTS FOR (v:Venue) ON (v.issn)",
            "CREATE INDEX method_normalized IF NOT EXISTS FOR (m:Method) ON (m.normalized_name)",
            "CREATE INDEX dataset_normalized IF NOT EXISTS FOR (d:Dataset) ON (d.normalized_name)",
            "CREATE INDEX work_year_type IF NOT EXISTS FOR (w:Work) ON (w.publication_year, w.work_type)",
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

    def get_work_external_keys(self, work_id: str) -> dict[str, str] | None:
        """Return doi / arxiv_id / fingerprint for canonical-key checks (benchmarks, tools)."""

        q = """
        MATCH (w:Work {id: $id})
        RETURN coalesce(w.doi, '') AS doi,
               coalesce(w.arxiv_id, '') AS arxiv_id,
               coalesce(w.fingerprint, '') AS fingerprint
        LIMIT 1
        """
        with self._driver.session() as session:
            rec = session.run(q, id=work_id).single()
            if not rec:
                return None
            return {
                "doi": str(rec["doi"] or ""),
                "arxiv_id": str(rec["arxiv_id"] or ""),
                "fingerprint": str(rec["fingerprint"] or ""),
            }

    def work_exists(self, work_id: str) -> bool:
        q = "MATCH (w:Work {id: $id}) RETURN 1 AS ok LIMIT 1"
        with self._driver.session() as session:
            rec = session.run(q, id=work_id).single()
            return bool(rec)

    def work_has_incoming_cites(self, work_id: str) -> bool:
        q = """
        MATCH (:Work)-[:CITES]->(w:Work {id: $id})
        RETURN count(*) AS n
        """
        with self._driver.session() as session:
            rec = session.run(q, id=work_id).single()
            return bool(rec and int(rec["n"]) > 0)

    def detach_delete_work_if_no_incoming_cites(self, work_id: str) -> bool:
        """
        Remove :Work when no other :Work cites it (incoming CITES).

        Returns True if a node was deleted.
        """

        if not self.work_exists(work_id):
            return False
        if self.work_has_incoming_cites(work_id):
            return False
        q = "MATCH (w:Work {id: $id}) DETACH DELETE w"
        with self._driver.session() as session:
            session.run(q, id=work_id)
        return True

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

    @staticmethod
    def _semantic_method_id(name: str) -> str:
        key = "method:" + re.sub(r"\s+", " ", name.strip().lower())
        return str(uuid.uuid5(uuid.NAMESPACE_URL, key))

    @staticmethod
    def _semantic_dataset_id(name: str) -> str:
        key = "dataset:" + re.sub(r"\s+", " ", name.strip().lower())
        return str(uuid.uuid5(uuid.NAMESPACE_URL, key))

    @staticmethod
    def _semantic_provenance_json(evidence: list[Any]) -> str:
        if not evidence:
            return "[]"
        payload = []
        for item in evidence[:8]:
            if hasattr(item, "model_dump"):
                payload.append(item.model_dump(mode="json"))
            else:
                payload.append(item)
        return json.dumps(payload, ensure_ascii=False)

    def sync_work_semantic_layer(
        self,
        work_id: str,
        extraction: SemanticExtractionV1,
        *,
        confidence_threshold: float = 0.35,
    ) -> None:
        """Project ontology-v1 Method/Dataset nodes and ADR-004 edges for one :Work."""

        with self._driver.session() as session:
            session.execute_write(
                self._sync_semantic_tx,
                work_id,
                extraction,
                confidence_threshold,
            )

    @staticmethod
    def _sync_semantic_tx(
        tx,
        work_id: str,
        extraction: SemanticExtractionV1,
        confidence_threshold: float,
    ) -> None:
        tx.run(
            """
            MATCH (w:Work {id: $wid})-[r:USES_METHOD]->()
            DELETE r
            """,
            wid=work_id,
        )
        tx.run(
            """
            MATCH (w:Work {id: $wid})-[r:EVALUATED_ON]->()
            DELETE r
            """,
            wid=work_id,
        )
        tx.run(
            """
            MATCH (:Method)-[r:TRAINED_OR_TESTED_ON {source_work_id: $wid}]->(:Dataset)
            DELETE r
            """,
            wid=work_id,
        )

        for m in extraction.methods:
            if m.confidence < confidence_threshold:
                continue
            name = (m.name or "").strip()
            if not name:
                continue
            mid = Neo4jGraphStore._semantic_method_id(name)
            prov = Neo4jGraphStore._semantic_provenance_json(m.evidence)
            desc = (m.description_short or "").strip() or None
            tx.run(
                """
                MATCH (w:Work {id: $wid})
                MERGE (x:Method {id: $mid})
                SET x.name = $name,
                    x.description_short = coalesce($desc, x.description_short),
                    x.schema_version = 1
                MERGE (w)-[r:USES_METHOD]->(x)
                SET r.confidence = $conf,
                    r.provenance_json = $prov,
                    r.source_work_id = $wid
                """,
                wid=work_id,
                mid=mid,
                name=name[:500],
                desc=desc,
                conf=float(m.confidence),
                prov=prov,
            )

        for d in extraction.datasets:
            if d.confidence < confidence_threshold:
                continue
            name = (d.name or "").strip()
            if not name:
                continue
            did = Neo4jGraphStore._semantic_dataset_id(name)
            prov = Neo4jGraphStore._semantic_provenance_json(d.evidence)
            tx.run(
                """
                MATCH (w:Work {id: $wid})
                MERGE (y:Dataset {id: $did})
                SET y.name = $name,
                    y.schema_version = 1
                MERGE (w)-[r:EVALUATED_ON]->(y)
                SET r.confidence = $conf,
                    r.provenance_json = $prov,
                    r.source_work_id = $wid
                """,
                wid=work_id,
                did=did,
                name=name[:500],
                conf=float(d.confidence),
                prov=prov,
            )

        for rel in extraction.relations:
            if rel.confidence < confidence_threshold:
                continue
            if rel.type != "trained_or_tested_on":
                continue
            mname: str | None = None
            dname: str | None = None
            if rel.from_.kind == "method" and rel.from_.name:
                mname = rel.from_.name.strip()
            if rel.to.kind == "dataset" and rel.to.name:
                dname = rel.to.name.strip()
            if (
                rel.from_.kind == "dataset"
                and rel.to.kind == "method"
                and rel.from_.name
                and rel.to.name
            ):
                dname = rel.from_.name.strip()
                mname = rel.to.name.strip()
            if not mname or not dname:
                continue
            mid = Neo4jGraphStore._semantic_method_id(mname)
            did = Neo4jGraphStore._semantic_dataset_id(dname)
            prov = Neo4jGraphStore._semantic_provenance_json(rel.evidence)
            tx.run(
                """
                MERGE (mm:Method {id: $mid})
                SET mm.name = coalesce(mm.name, $mname)
                MERGE (dd:Dataset {id: $did})
                SET dd.name = coalesce(dd.name, $dname)
                MERGE (mm)-[rr:TRAINED_OR_TESTED_ON]->(dd)
                SET rr.confidence = $conf,
                    rr.provenance_json = $prov,
                    rr.source_work_id = $wid
                """,
                mid=mid,
                did=did,
                mname=mname[:500],
                dname=dname[:500],
                conf=float(rel.confidence),
                prov=prov,
                wid=work_id,
            )

    def merge_work_into_canonical(self, keep_id: str, drop_id: str) -> bool:
        """
        Re-point :CITES / version / semantic edges from duplicate ``drop_id`` onto ``keep_id``,
        re-bind ``HAS_AUTHORSHIP`` edges onto ``keep_id``, then ``DETACH DELETE`` the drop work.

        Returns:
            True if ``drop_id`` was detached-deleted.
        """

        if keep_id == drop_id:
            return False
        with self._driver.session() as session:
            return bool(session.execute_write(self._merge_work_tx, keep_id, drop_id))

    @staticmethod
    def _merge_work_tx(tx, keep_id: str, drop_id: str) -> bool:
        tx.run(
            """
            MATCH (k:Work {id: $keep}), (d:Work {id: $drop})
            MATCH (o:Work)-[r:CITES]->(d)
            MERGE (o)-[r2:CITES]->(k)
            DELETE r
            """,
            keep=keep_id,
            drop=drop_id,
        )
        tx.run(
            """
            MATCH (k:Work {id: $keep}), (d:Work {id: $drop})
            MATCH (d)-[r:CITES]->(t:Work)
            MERGE (k)-[r2:CITES]->(t)
            DELETE r
            """,
            keep=keep_id,
            drop=drop_id,
        )
        tx.run(
            """
            MATCH (k:Work {id: $keep}), (d:Work {id: $drop})
            MATCH (d)-[r:RELATED_VERSION_OF]->(x:Work)
            WHERE x.id <> $drop
            MERGE (k)-[r2:RELATED_VERSION_OF]->(x)
            DELETE r
            """,
            keep=keep_id,
            drop=drop_id,
        )
        tx.run(
            """
            MATCH (k:Work {id: $keep}), (d:Work {id: $drop})
            MATCH (x:Work)-[r:RELATED_VERSION_OF]->(d)
            WHERE x.id <> $drop
            MERGE (x)-[r2:RELATED_VERSION_OF]->(k)
            DELETE r
            """,
            keep=keep_id,
            drop=drop_id,
        )
        tx.run(
            """
            MATCH (k:Work {id: $keep}), (d:Work {id: $drop})
            MATCH (d)-[r:USES_METHOD]->(m:Method)
            MERGE (k)-[r2:USES_METHOD]->(m)
            SET r2.confidence = coalesce(r.confidence, r2.confidence),
                r2.provenance_json = coalesce(r.provenance_json, r2.provenance_json),
                r2.source_work_id = $keep
            DELETE r
            """,
            keep=keep_id,
            drop=drop_id,
        )
        tx.run(
            """
            MATCH (k:Work {id: $keep}), (d:Work {id: $drop})
            MATCH (d)-[r:EVALUATED_ON]->(ds:Dataset)
            MERGE (k)-[r2:EVALUATED_ON]->(ds)
            SET r2.confidence = coalesce(r.confidence, r2.confidence),
                r2.provenance_json = coalesce(r.provenance_json, r2.provenance_json),
                r2.source_work_id = $keep
            DELETE r
            """,
            keep=keep_id,
            drop=drop_id,
        )
        # Re-bind authorship subgraph from duplicate work onto canonical work (Wave L).
        tx.run(
            """
            MATCH (k:Work {id: $keep}), (d:Work {id: $drop})
            MATCH (d)-[ha:HAS_AUTHORSHIP]->(a:Authorship)
            MERGE (k)-[ha2:HAS_AUTHORSHIP]->(a)
            SET ha2 += properties(ha)
            DELETE ha
            """,
            keep=keep_id,
            drop=drop_id,
        )
        tx.run(
            """
            MATCH (d:Work {id: $drop})
            DETACH DELETE d
            """,
            drop=drop_id,
        )
        return True

    def merge_author_into_canonical(self, keep_id: str, drop_id: str) -> bool:
        """
        Move all ``(:Authorship)-[:OF_AUTHOR]->(drop)`` to ``keep`` Author, then remove ``drop``.

        Returns True if ``drop`` Author node was removed.
        """

        if keep_id == drop_id:
            return False
        with self._driver.session() as session:
            return bool(session.execute_write(self._merge_author_tx, keep_id, drop_id))

    @staticmethod
    def _merge_author_tx(tx, keep_id: str, drop_id: str) -> bool:
        tx.run(
            """
            MATCH (keep:Author {id: $keep}), (drop:Author {id: $drop})
            MATCH (x:Authorship)-[r:OF_AUTHOR]->(drop)
            MERGE (x)-[r2:OF_AUTHOR]->(keep)
            SET r2 += properties(r)
            DELETE r
            """,
            keep=keep_id,
            drop=drop_id,
        )
        row = tx.run(
            """
            MATCH (drop:Author {id: $drop})
            OPTIONAL MATCH (x:Authorship)-[:OF_AUTHOR]->(drop)
            WITH drop, count(x) AS n
            WHERE n = 0
            DETACH DELETE drop
            RETURN 1 AS deleted
            """,
            drop=drop_id,
        ).single()
        return bool(row)

    def fetch_work_bibliography_card(self, work_id: str) -> dict[str, Any] | None:
        """Title/year/first author + abstract snippet for dedup LLM prompts."""

        q = """
        MATCH (w:Work {id: $id})
        OPTIONAL MATCH (w)-[:HAS_AUTHORSHIP]->(ash:Authorship)
        WITH w, ash
        ORDER BY ash.author_position ASC
        WITH w, head(collect(ash)) AS a1
        OPTIONAL MATCH (a1)-[:OF_AUTHOR]->(auth:Author)
        RETURN coalesce(w.title, '') AS title,
               w.publication_year AS year,
               coalesce(w.abstract, '') AS abstract,
               coalesce(w.doi, '') AS doi,
               coalesce(w.arxiv_id, '') AS arxiv_id,
               coalesce(auth.full_name, '') AS first_author
        LIMIT 1
        """
        with self._driver.session() as session:
            rec = session.run(q, id=work_id).single()
            if not rec:
                return None
            return {
                "work_id": work_id,
                "title": str(rec["title"] or ""),
                "year": rec["year"],
                "abstract": str(rec["abstract"] or ""),
                "doi": str(rec["doi"] or ""),
                "arxiv_id": str(rec["arxiv_id"] or ""),
                "first_author": str(rec["first_author"] or ""),
            }

    def fulltext_search_work_ids(self, query: str, *, limit: int = 20) -> list[tuple[str, float]]:
        """Full-text search on ``works_title_abstract`` index (Wave Q). Returns (work_id, score)."""

        q = (query or "").strip()
        if not q:
            return []
        cypher = """
        CALL db.index.fulltext.queryNodes('works_title_abstract', $search)
        YIELD node, score
        WHERE 'Work' IN labels(node)
        RETURN node.id AS wid, score
        LIMIT $lim
        """
        try:
            with self._driver.session() as session:
                rows = session.run(cypher, search=q, lim=int(limit))
                out: list[tuple[str, float]] = []
                for r in rows:
                    wid = str(r["wid"] or "").strip()
                    if wid:
                        out.append((wid, float(r["score"] or 0.0)))
                return out
        except Exception:  # noqa: BLE001 — index missing or unsupported query
            return []

    def cites_neighbor_work_ids(
        self,
        seed_work_ids: list[str],
        *,
        exclude_ids: set[str],
        limit: int = 80,
    ) -> list[str]:
        """Distinct :Work ids reachable by one ``CITES`` hop from any seed work."""

        seeds = [str(x).strip() for x in seed_work_ids if str(x).strip()]
        if not seeds:
            return []
        excl = [str(x).strip() for x in exclude_ids if str(x).strip()]
        cypher = """
        UNWIND $seeds AS sid
        MATCH (w:Work {id: sid})-[r:CITES]-(n:Work)
        WHERE NOT n.id IN $excl
        RETURN DISTINCT n.id AS nid
        LIMIT $lim
        """
        try:
            with self._driver.session() as session:
                rows = session.run(cypher, seeds=seeds[:50], excl=excl[:500], lim=int(limit))
                return [str(r["nid"]) for r in rows if r.get("nid")]
        except Exception:  # noqa: BLE001
            return []

    def list_workspace_authors(self, workspace_id: str) -> list[dict[str, Any]]:
        """Distinct authors attached to works in a workspace (for L2 dedup scan)."""

        q = """
        MATCH (ws:Workspace {id: $ws})-[:CONTAINS]->(:Work)-[:HAS_AUTHORSHIP]->(:Authorship)-[:OF_AUTHOR]->(a:Author)
        RETURN DISTINCT a.id AS id, coalesce(a.full_name, '') AS full_name
        """
        with self._driver.session() as session:
            rows = session.run(q, ws=workspace_id)
            return [{"id": str(r["id"]), "full_name": str(r["full_name"] or "")} for r in rows]

    def fetch_author_affiliation_hint(self, author_id: str) -> str:
        q = """
        MATCH (a:Author {id: $id})<-[:OF_AUTHOR]-(x:Authorship)
        RETURN coalesce(x.raw_affiliation, '') AS aff
        LIMIT 1
        """
        with self._driver.session() as session:
            rec = session.run(q, id=author_id).single()
            if not rec:
                return ""
            return str(rec["aff"] or "")

    def detach_delete_claims_for_work(self, work_id: str) -> None:
        """Remove Claim/Evidence subgraph anchored in this work (re-ingest idempotency)."""

        q = """
        MATCH (w:Work {id: $wid})<-[:ANCHORED_IN]-(e:Evidence)
        MATCH (c:Claim)-[:SUPPORTED_BY]->(e)
        DETACH DELETE c, e
        """
        with self._driver.session() as session:
            session.run(q, wid=work_id)

    def upsert_claims_with_evidence(self, work_id: str, claims: list[ClaimDraft]) -> None:
        """Merge :Claim / :Evidence nodes and edges for one work (Wave O)."""

        if not claims:
            return

        def _tx(tx, wid: str, rows: list[ClaimDraft]) -> None:
            """Persist claim and evidence nodes for one work."""

            for draft in rows:
                tx.run(
                    """
                    MATCH (w:Work {id: $wid})
                    MERGE (c:Claim {id: $cid})
                    SET c.text = $text,
                        c.normalized_text = $norm,
                        c.claim_type = $ctype,
                        c.polarity = $pol,
                        c.confidence = $conf,
                        c.schema_version = 1
                    """,
                    wid=wid,
                    cid=draft.claim_id,
                    text=draft.text,
                    norm=draft.normalized_text,
                    ctype=draft.claim_type,
                    pol=draft.polarity,
                    conf=float(draft.confidence),
                )
                for ev in draft.evidence:
                    tx.run(
                        """
                        MATCH (w:Work {id: $wid})
                        MATCH (c:Claim {id: $cid})
                        MERGE (e:Evidence {id: $eid})
                        SET e.chunk_fingerprint = $cfp,
                            e.quote = $quote,
                            e.section_path = $spath,
                            e.schema_version = 1
                        MERGE (c)-[sr:SUPPORTED_BY]->(e)
                        SET sr.confidence = $conf
                        MERGE (e)-[:ANCHORED_IN]->(w)
                        """,
                        wid=wid,
                        cid=draft.claim_id,
                        eid=ev.evidence_id,
                        cfp=ev.chunk_fingerprint,
                        quote=ev.quote,
                        spath=ev.section_path,
                        conf=float(draft.confidence),
                    )

        with self._driver.session() as session:
            session.execute_write(_tx, work_id, claims)

    # --- User workspaces (:Workspace)-[:CONTAINS]->(:Work) ---

    def workspace_create(self, name: str) -> dict[str, Any]:
        """Create a Workspace node and return ``{id, name, created_at}``."""

        ws_id = str(uuid.uuid4())
        created = datetime.now(tz=timezone.utc).isoformat()
        label = (name or "").strip() or "Workspace"
        q = (
            "CREATE (ws:Workspace {id: $id, name: $name, created_at: $created}) "
            "RETURN ws.id AS id, ws.name AS name, ws.created_at AS created_at"
        )
        with self._driver.session() as session:
            rec = session.run(q, id=ws_id, name=label, created=created).single()
            if not rec:
                raise RuntimeError("workspace_create_failed")
        return {"id": str(rec["id"]), "name": str(rec["name"]), "created_at": str(rec["created_at"])}

    def workspace_list(self) -> list[dict[str, Any]]:
        q = """
        MATCH (ws:Workspace)
        OPTIONAL MATCH (ws)-[:CONTAINS]->(w:Work)
        WITH ws, collect(DISTINCT w.id) AS wids
        RETURN ws.id AS id, ws.name AS name, ws.created_at AS created_at, wids AS work_ids
        ORDER BY ws.created_at DESC
        """
        out: list[dict[str, Any]] = []
        with self._driver.session() as session:
            for rec in session.run(q):
                wids = [str(x) for x in (rec["work_ids"] or []) if x]
                out.append(
                    {
                        "id": str(rec["id"]),
                        "name": str(rec["name"] or ""),
                        "created_at": str(rec["created_at"] or ""),
                        "work_ids": wids,
                    },
                )
        return out

    def workspace_get(self, workspace_id: str) -> dict[str, Any] | None:
        q = """
        MATCH (ws:Workspace {id: $id})
        OPTIONAL MATCH (ws)-[:CONTAINS]->(w:Work)
        WITH ws, collect(DISTINCT w.id) AS wids
        RETURN ws.id AS id, ws.name AS name, ws.created_at AS created_at, wids AS work_ids
        """
        with self._driver.session() as session:
            rec = session.run(q, id=workspace_id).single()
            if not rec:
                return None
            wids = [str(x) for x in (rec["work_ids"] or []) if x]
            return {
                "id": str(rec["id"]),
                "name": str(rec["name"] or ""),
                "created_at": str(rec["created_at"] or ""),
                "work_ids": wids,
            }

    def workspace_rename(self, workspace_id: str, name: str) -> bool:
        label = (name or "").strip()
        if not label:
            return False
        q = "MATCH (ws:Workspace {id: $id}) SET ws.name = $name RETURN 1 AS ok"
        with self._driver.session() as session:
            return bool(session.run(q, id=workspace_id, name=label).single())

    def workspace_delete(self, workspace_id: str) -> bool:
        q = "MATCH (ws:Workspace {id: $id}) DETACH DELETE ws"
        with self._driver.session() as session:
            summary = session.run(q, id=workspace_id).consume()
            return int(summary.counters.nodes_deleted) > 0

    def workspace_add_work(self, workspace_id: str, work_id: str) -> bool:
        if not self.work_exists(work_id):
            return False
        q = """
        MATCH (ws:Workspace {id: $wid})
        MATCH (w:Work {id: $work})
        MERGE (ws)-[:CONTAINS]->(w)
        RETURN 1 AS ok
        """
        with self._driver.session() as session:
            return bool(session.run(q, wid=workspace_id, work=work_id).single())

    def workspace_remove_work(self, workspace_id: str, work_id: str) -> bool:
        q = """
        MATCH (ws:Workspace {id: $wid})-[r:CONTAINS]->(w:Work {id: $work})
        DELETE r
        RETURN count(*) AS n
        """
        with self._driver.session() as session:
            rec = session.run(q, wid=workspace_id, work=work_id).single()
            return bool(rec and int(rec["n"]) > 0)

    def workspace_merge_into(self, keep_workspace_id: str, drop_workspace_id: str) -> bool:
        if keep_workspace_id == drop_workspace_id:
            return False
        drop = self.workspace_get(drop_workspace_id)
        if not drop:
            return False
        for wid in drop.get("work_ids") or []:
            self.workspace_add_work(keep_workspace_id, str(wid))
        return self.workspace_delete(drop_workspace_id)
