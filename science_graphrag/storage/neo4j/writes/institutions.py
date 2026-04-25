"""Institution dedup writes."""

from __future__ import annotations

from science_graphrag.storage.neo4j.client import _Neo4jClient


def merge_institution(
    client: _Neo4jClient, entity_id_a: str, entity_id_b: str, keep_id: str
) -> bool:
    if keep_id not in (entity_id_a, entity_id_b):
        return False
    drop_id = entity_id_b if keep_id == entity_id_a else entity_id_a
    if keep_id == drop_id:
        return False
    with client.session() as session:
        return bool(session.execute_write(_merge_institution_tx, keep_id, drop_id))


def _merge_institution_tx(tx, keep_id: str, drop_id: str) -> bool:
    tx.run(
        """
        MATCH (k:Institution {id: $keep}), (d:Institution {id: $drop})
        MATCH (a:Authorship)-[r:AFFILIATED_WITH]->(d)
        MERGE (a)-[r2:AFFILIATED_WITH]->(k)
        SET r2 += properties(r)
        DELETE r
        """,
        keep=keep_id,
        drop=drop_id,
    )
    tx.run(
        """
        MATCH (k:Institution {id: $keep}), (d:Institution {id: $drop})
        WITH k, d, coalesce(k.alternative_names, []) + coalesce(d.alternative_names, []) + [coalesce(d.name, '')] AS all_names
        WITH k, reduce(acc = [], x IN all_names | CASE WHEN x = '' OR x IN acc THEN acc ELSE acc + x END) AS dedup_names
        SET k.alternative_names = dedup_names
        """,
        keep=keep_id,
        drop=drop_id,
    )
    tx.run("MATCH (d:Institution {id: $drop}) DETACH DELETE d", drop=drop_id)
    return True


def add_institution_alias(client: _Neo4jClient, institution_id: str, alias: str) -> bool:
    alias_clean = str(alias or "").strip()
    if not institution_id or not alias_clean:
        return False
    with client.session() as session:
        rec = session.run(
            """
            MATCH (n:Institution {id: $id})
            WITH n, coalesce(n.alternative_names, []) + [$alias] AS all_names
            WITH n, reduce(acc = [], x IN all_names | CASE WHEN x = '' OR x IN acc THEN acc ELSE acc + x END) AS dedup_names
            SET n.alternative_names = dedup_names
            RETURN 1 AS ok
            """,
            id=institution_id,
            alias=alias_clean,
        ).single()
        return bool(rec)
