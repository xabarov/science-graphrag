from __future__ import annotations

import json
import re
import uuid
from typing import Any

from neo4j import Driver, GraphDatabase, NotificationClassification

from science_graphrag.domain.authorship_ids import canonical_author_node_id
from science_graphrag.domain.models import AuthorshipDraft, WorkDraft
from science_graphrag.domain.semantic_models import SemanticExtractionV1


class Neo4jGraphStore:
    def __init__(self, uri: str, user: str, password: str) -> None:
        self._driver: Driver = GraphDatabase.driver(
            uri,
            auth=(user, password),
            notifications_disabled_classifications=[NotificationClassification.UNRECOGNIZED],
        )

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
            (
                "CREATE CONSTRAINT method_id_unique IF NOT EXISTS "
                "FOR (m:Method) REQUIRE m.id IS UNIQUE"
            ),
            (
                "CREATE CONSTRAINT dataset_id_unique IF NOT EXISTS "
                "FOR (d:Dataset) REQUIRE d.id IS UNIQUE"
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

    def merge_work_into_canonical(self, keep_id: str, drop_id: str) -> None:
        """
        Re-point :CITES / version / semantic edges from duplicate ``drop_id`` onto ``keep_id``.

        Removes ``drop_id`` only when it has no outgoing ``HAS_AUTHORSHIP`` (minimal Phase 1 aid).
        """

        if keep_id == drop_id:
            return
        with self._driver.session() as session:
            session.execute_write(self._merge_work_tx, keep_id, drop_id)

    @staticmethod
    def _merge_work_tx(tx, keep_id: str, drop_id: str) -> None:
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
        auth_row = tx.run(
            """
            MATCH (d:Work {id: $drop})-[:HAS_AUTHORSHIP]->(:Authorship)
            RETURN count(*) AS n
            """,
            drop=drop_id,
        ).single()
        if auth_row and int(auth_row["n"]) > 0:
            return
        tx.run(
            """
            MATCH (d:Work {id: $drop})
            DETACH DELETE d
            """,
            drop=drop_id,
        )
