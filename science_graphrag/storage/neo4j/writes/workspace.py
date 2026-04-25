"""Workspace write operations."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from science_graphrag.storage.neo4j import reads
from science_graphrag.storage.neo4j.client import _Neo4jClient


def workspace_create(client: _Neo4jClient, name: str) -> dict[str, Any]:
    """Create a Workspace node and return `{id, name, created_at}`."""
    ws_id = str(uuid.uuid4())
    created = datetime.now(tz=timezone.utc).isoformat()
    label = (name or "").strip() or "Workspace"
    q = (
        "CREATE (ws:Workspace {id: $id, name: $name, created_at: $created}) "
        "RETURN ws.id AS id, ws.name AS name, ws.created_at AS created_at"
    )
    with client.session() as session:
        rec = session.run(q, id=ws_id, name=label, created=created).single()
        if not rec:
            raise RuntimeError("workspace_create_failed")
    return {"id": str(rec["id"]), "name": str(rec["name"]), "created_at": str(rec["created_at"])}


def workspace_rename(client: _Neo4jClient, workspace_id: str, name: str) -> bool:
    label = (name or "").strip()
    if not label:
        return False
    q = "MATCH (ws:Workspace {id: $id}) SET ws.name = $name RETURN 1 AS ok"
    with client.session() as session:
        return bool(session.run(q, id=workspace_id, name=label).single())


def workspace_delete(client: _Neo4jClient, workspace_id: str) -> bool:
    q = "MATCH (ws:Workspace {id: $id}) DETACH DELETE ws"
    with client.session() as session:
        summary = session.run(q, id=workspace_id).consume()
        return int(summary.counters.nodes_deleted) > 0


def workspace_add_work(client: _Neo4jClient, workspace_id: str, work_id: str) -> bool:
    if not reads.work_exists(client, work_id):
        return False
    q = """
    MATCH (ws:Workspace {id: $wid})
    MATCH (w:Work {id: $work})
    MERGE (ws)-[:CONTAINS]->(w)
    RETURN 1 AS ok
    """
    with client.session() as session:
        return bool(session.run(q, wid=workspace_id, work=work_id).single())


def workspace_remove_work(client: _Neo4jClient, workspace_id: str, work_id: str) -> bool:
    q = """
    MATCH (ws:Workspace {id: $wid})-[r:CONTAINS]->(w:Work {id: $work})
    DELETE r
    RETURN count(*) AS n
    """
    with client.session() as session:
        rec = session.run(q, wid=workspace_id, work=work_id).single()
        return bool(rec and int(rec["n"]) > 0)


def workspace_merge_into(
    client: _Neo4jClient, keep_workspace_id: str, drop_workspace_id: str
) -> bool:
    if keep_workspace_id == drop_workspace_id:
        return False
    drop = reads.workspace_get(client, drop_workspace_id)
    if not drop:
        return False
    for wid in drop.get("work_ids") or []:
        workspace_add_work(client, keep_workspace_id, str(wid))
    return workspace_delete(client, drop_workspace_id)
