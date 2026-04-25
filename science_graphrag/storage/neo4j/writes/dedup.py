"""Canonical merge writes for Work and Author deduplication."""

from __future__ import annotations

from science_graphrag.storage.neo4j.client import _Neo4jClient


def merge_work_into_canonical(client: _Neo4jClient, keep_id: str, drop_id: str) -> bool:
    """Repoint graph edges from duplicate `drop_id` to canonical `keep_id`."""
    if keep_id == drop_id:
        return False
    with client.session() as session:
        return bool(session.execute_write(_merge_work_tx, keep_id, drop_id))


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


def merge_author_into_canonical(client: _Neo4jClient, keep_id: str, drop_id: str) -> bool:
    """Move all authorships from duplicate author to canonical author."""
    if keep_id == drop_id:
        return False
    with client.session() as session:
        return bool(session.execute_write(_merge_author_tx, keep_id, drop_id))


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
