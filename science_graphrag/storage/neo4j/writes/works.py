"""Write operations for :Work nodes (upsert, merge, delete)."""

from __future__ import annotations

from typing import Any

from science_graphrag.domain.authorship_ids import canonical_author_node_id
from science_graphrag.domain.models import AuthorshipDraft, WorkDraft
from science_graphrag.storage.neo4j import reads
from science_graphrag.storage.neo4j.client import _Neo4jClient


def upsert_work_layer1(
    client: _Neo4jClient,
    work_id: str,
    draft: WorkDraft,
    authorships: list[AuthorshipDraft],
    venue_id: str | None,
    institution_nodes: list[tuple[str, str, list[str]]],
) -> None:
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

    with client.session() as session:
        session.execute_write(_write_work_tx, props, authorships, venue_id, institution_nodes)


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


def merge_cites(client: _Neo4jClient, from_work_id: str, to_work_id: str) -> None:
    q = """
    MATCH (a:Work {id: $from_id})
    MATCH (b:Work {id: $to_id})
    MERGE (a)-[:CITES]->(b)
    """
    with client.session() as session:
        session.run(q, from_id=from_work_id, to_id=to_work_id)


def detach_delete_outgoing_cites(client: _Neo4jClient, from_work_id: str) -> int:
    """Delete all outgoing ``(:Work)-[:CITES]->(:Work)`` edges for ``from_work_id``.

    Returns the number of relationships deleted (best-effort; Neo4j summary counters).
    """

    q = """
    MATCH (a:Work {id: $from_id})-[r:CITES]->(:Work)
    DELETE r
    RETURN count(r) AS deleted
    """
    with client.session() as session:
        record = session.run(q, from_id=from_work_id).single()
        if record is None:
            return 0
        deleted = record.get("deleted")
        try:
            return int(deleted or 0)
        except Exception:  # noqa: BLE001
            return 0


def merge_related_version(client: _Neo4jClient, a_id: str, b_id: str) -> None:
    q = """
    MATCH (a:Work {id: $a})
    MATCH (b:Work {id: $b})
    MERGE (a)-[:RELATED_VERSION_OF]->(b)
    """
    with client.session() as session:
        session.run(q, a=a_id, b=b_id)


def upsert_minimal_work(
    client: _Neo4jClient,
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
    props: dict[str, Any] = {"id": work_id, "ingestion_confidence": ingestion_confidence}
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
    with client.session() as session:
        session.run(q, id=work_id, props=props)


def detach_delete_work_if_no_incoming_cites(client: _Neo4jClient, work_id: str) -> bool:
    """Remove :Work when no other :Work cites it (incoming CITES)."""
    if not reads.work_exists(client, work_id):
        return False
    if reads.work_has_incoming_cites(client, work_id):
        return False
    q = "MATCH (w:Work {id: $id}) DETACH DELETE w"
    with client.session() as session:
        session.run(q, id=work_id)
    return True
