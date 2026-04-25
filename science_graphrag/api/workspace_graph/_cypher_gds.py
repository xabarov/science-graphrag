from __future__ import annotations

import hashlib
import uuid
from typing import Any

from science_graphrag.api.workspace_graph.projection import (
    edge_dict_from_ids,
    edge_dict_from_rel,
    edge_key,
    node_dict_from_neo,
)
from science_graphrag.config import Settings


def gds_runtime_available(session: Any) -> bool:
    try:
        session.run("RETURN gds.version() AS v").consume()
        return True
    except Exception:  # noqa: BLE001
        return False


def gds_graph_drop(session: Any, graph_name: str) -> None:
    try:
        session.run("CALL gds.graph.drop($gn, false) YIELD graphName", gn=graph_name).consume()
    except Exception:  # noqa: BLE001
        pass


def gds_internal_workspace_work_graph(
    session: Any,
    *,
    settings: Settings,
    workspace_id: str,
    internal_ids: list[str],
    cap: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool] | None:
    if not settings.gds_enabled or not gds_runtime_available(session) or len(internal_ids) < 51:
        return None
    gn = "ws_" + hashlib.sha256(f"{workspace_id}:{uuid.uuid4().hex}".encode()).hexdigest()[:18]
    nq = "MATCH (ws:Workspace {id: $wid})-[:CONTAINS]->(w:Work) RETURN id(w) AS id, labels(w) AS labels"
    rq = (
        "MATCH (ws:Workspace {id: $wid})-[:CONTAINS]->(a:Work)-[r]-(b:Work) "
        "WHERE (ws)-[:CONTAINS]->(b) RETURN id(a) AS source, id(b) AS target, type(r) AS type"
    )
    try:
        row = session.run(
            """
            CALL gds.graph.project.cypher(
              $gn, $nq, $rq, {validateRelationships: false, parameters: {wid: $wid}}
            ) YIELD relationshipCount
            RETURN relationshipCount AS rc
            """,
            gn=gn,
            nq=nq,
            rq=rq,
            wid=workspace_id,
        ).single()
        if int(row["rc"] or 0) <= 0 if row else True:
            gds_graph_drop(session, gn)
            return None
    except Exception:  # noqa: BLE001
        gds_graph_drop(session, gn)
        return None
    neo_ids: set[int] = set()
    triples: list[tuple[int, int, str]] = []
    try:
        try:
            stream = session.run(
                "CALL gds.graph.relationshipStream($gn) YIELD sourceNodeId, targetNodeId, relationshipType "
                "RETURN sourceNodeId, targetNodeId, relationshipType LIMIT $cap",
                gn=gn,
                cap=max(1, cap),
            )
        except Exception:  # noqa: BLE001
            stream = session.run(
                "CALL gds.graph.streamRelationships($gn) YIELD sourceNodeId, targetNodeId, relationshipType "
                "RETURN sourceNodeId, targetNodeId, relationshipType LIMIT $cap",
                gn=gn,
                cap=max(1, cap),
            )
        seen = 0
        for rec in stream:
            seen += 1
            sn = int(rec["sourceNodeId"])
            tn = int(rec["targetNodeId"])
            triples.append((sn, tn, str(rec["relationshipType"] or "")))
            neo_ids.update((sn, tn))
        truncated = seen >= cap
    except Exception:  # noqa: BLE001
        gds_graph_drop(session, gn)
        return None
    finally:
        gds_graph_drop(session, gn)
    if not triples:
        return None
    id_map: dict[int, str] = {}
    for row in session.run(
        "UNWIND $neo AS nid MATCH (w:Work) WHERE id(w) = nid RETURN nid AS neo, w.id AS wid",
        neo=list(neo_ids),
    ):
        id_map[int(row["neo"])] = str(row["wid"])
    if len(id_map) < 2:
        return None
    nodes_by_id: dict[str, dict[str, Any]] = {}
    for wid in internal_ids:
        one = session.run("MATCH (w:Work {id: $id}) RETURN w", id=wid).single()
        if one and one["w"] is not None:
            nd = node_dict_from_neo(one["w"])
            if nd:
                nodes_by_id[nd["id"]] = nd
    edges_by_key: dict[str, dict[str, Any]] = {}
    for seq, (sn, tn, rt) in enumerate(triples):
        sa, tb = id_map.get(sn), id_map.get(tn)
        if not sa or not tb:
            continue
        edge = edge_dict_from_ids(sa, tb, rt, seq)
        edges_by_key[edge_key(edge["source"], edge["type"], edge["target"])] = edge
    return list(nodes_by_id.values()), list(edges_by_key.values()), truncated


def cypher_append_authorships(
    session: Any, *, workspace_id: str, internal_ids: list[str], cap: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
    nodes_by_id: dict[str, dict[str, Any]] = {}
    edges_by_key: dict[str, dict[str, Any]] = {}
    n = 0
    for rec in session.run(
        """
        MATCH (ws:Workspace {id: $wid})-[:CONTAINS]->(w:Work)-[r1:HAS_AUTHORSHIP]->(ash:Authorship)
              -[r2:OF_AUTHOR]->(a:Author)
        WHERE w.id IN $ids
        RETURN w, r1, ash, r2, a
        LIMIT $cap
        """,
        wid=workspace_id,
        ids=internal_ids,
        cap=max(1, cap),
    ):
        n += 1
        w, r1, ash, r2, author = rec["w"], rec["r1"], rec["ash"], rec["r2"], rec["a"]
        for node in (w, ash, author):
            nd = node_dict_from_neo(node)
            if nd:
                nodes_by_id[nd["id"]] = nd
        if w is not None and ash is not None and r1 is not None:
            e1 = edge_dict_from_rel(w, ash, r1, len(edges_by_key))
            edges_by_key[edge_key(e1["source"], e1["type"], e1["target"])] = e1
        if ash is not None and author is not None and r2 is not None:
            e2 = edge_dict_from_rel(ash, author, r2, len(edges_by_key))
            edges_by_key[edge_key(e2["source"], e2["type"], e2["target"])] = e2
    return list(nodes_by_id.values()), list(edges_by_key.values()), n >= cap


def semantic_any(session: Any, internal_ids: list[str]) -> bool:
    if not internal_ids:
        return False
    row = session.run(
        """
        UNWIND $ids AS wid
        MATCH (w:Work {id: wid})
        WHERE EXISTS { MATCH (w)-[:USES_METHOD]->(:Method) }
           OR EXISTS { MATCH (w)-[:EVALUATED_ON]->(:Dataset) }
        RETURN count(w) > 0 AS has_sem
        """,
        ids=internal_ids,
    ).single()
    return bool(row and row["has_sem"])
