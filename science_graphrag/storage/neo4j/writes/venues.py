"""Venue dedup writes."""

from __future__ import annotations

from science_graphrag.storage.neo4j.client import _Neo4jClient


def merge_venue(client: _Neo4jClient, entity_id_a: str, entity_id_b: str, keep_id: str) -> bool:
    if keep_id not in (entity_id_a, entity_id_b):
        return False
    drop_id = entity_id_b if keep_id == entity_id_a else entity_id_a
    if keep_id == drop_id:
        return False
    with client.session() as session:
        return bool(session.execute_write(_merge_venue_tx, keep_id, drop_id))


def _merge_venue_tx(tx, keep_id: str, drop_id: str) -> bool:
    tx.run(
        """
        MATCH (k:Venue {id: $keep}), (d:Venue {id: $drop})
        MATCH (w:Work)-[r:PUBLISHED_IN]->(d)
        MERGE (w)-[r2:PUBLISHED_IN]->(k)
        SET r2 += properties(r)
        DELETE r
        """,
        keep=keep_id,
        drop=drop_id,
    )
    tx.run(
        """
        MATCH (k:Venue {id: $keep}), (d:Venue {id: $drop})
        WITH k, d, coalesce(k.alternative_names, []) + coalesce(d.alternative_names, []) + [coalesce(d.name, '')] AS all_names
        WITH k, reduce(acc = [], x IN all_names | CASE WHEN x = '' OR x IN acc THEN acc ELSE acc + x END) AS dedup_names
        SET k.alternative_names = dedup_names
        """,
        keep=keep_id,
        drop=drop_id,
    )
    tx.run("MATCH (d:Venue {id: $drop}) DETACH DELETE d", drop=drop_id)
    return True
