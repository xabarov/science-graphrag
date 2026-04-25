"""Claim/Evidence write operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from science_graphrag.storage.neo4j.client import _Neo4jClient

if TYPE_CHECKING:
    from science_graphrag.ingestion.claims.models import ClaimDraft


def detach_delete_claims_for_work(client: _Neo4jClient, work_id: str) -> None:
    """Remove Claim/Evidence subgraph anchored in this work (re-ingest idempotency)."""
    q = """
    MATCH (w:Work {id: $wid})<-[:ANCHORED_IN]-(e:Evidence)
    MATCH (c:Claim)-[:SUPPORTED_BY]->(e)
    DETACH DELETE c, e
    """
    with client.session() as session:
        session.run(q, wid=work_id)


def upsert_claims_with_evidence(
    client: _Neo4jClient,
    work_id: str,
    claims: list["ClaimDraft"],
) -> None:
    """Merge :Claim / :Evidence nodes and edges for one work."""
    if not claims:
        return
    with client.session() as session:
        session.execute_write(_upsert_claims_tx, work_id, claims)


def _upsert_claims_tx(tx, wid: str, rows: list["ClaimDraft"]) -> None:
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
