"""Workspace-scoped graph projection (Wave J): v2 modes, stats, neighbors, optional GDS probe."""

from __future__ import annotations

import hashlib
import re
import uuid
from typing import Any

from neo4j import GraphDatabase, NotificationClassification

from science_graphrag.api import works as works_api
from science_graphrag.config import Settings

MAX_NEIGHBORS_CAP = 300
SEMANTIC_REL_TYPES_LIST = sorted(
    {
        "USES_METHOD",
        "EVALUATED_ON",
        "HAS_AUTHORSHIP",
        "OF_AUTHOR",
        "AFFILIATED_WITH",
    },
)
ALLOWED_NODE_TYPES = frozenset({"Work", "Author", "Method", "Dataset", "Venue", "Institution", "Authorship"})


def _neo4j_driver(settings: Settings):
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
        notifications_disabled_classifications=[NotificationClassification.UNRECOGNIZED],
        connection_timeout=15.0,
        connection_acquisition_timeout=20.0,
    )


def merge_graph_payloads(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge multiple work neighborhood payloads (legacy union_1hop)."""

    nodes_by_id: dict[str, dict[str, Any]] = {}
    edges_by_key: dict[str, dict[str, Any]] = {}
    semantic_any = False
    truncated_any = False
    for g in payloads:
        if not g:
            continue
        if g.get("meta", {}).get("semantic_available"):
            semantic_any = True
        if g.get("meta", {}).get("is_truncated"):
            truncated_any = True
        for n in g.get("nodes") or []:
            nid = str(n.get("id") or "")
            if nid:
                nodes_by_id[nid] = n
        for e in g.get("edges") or []:
            eid = str(e.get("id") or "")
            if eid:
                edges_by_key[eid] = e
                continue
            src = str(e.get("source_id") or e.get("source") or "")
            tgt = str(e.get("target_id") or e.get("target") or "")
            rt = str(e.get("rel_type") or e.get("type") or "")
            key = f"{src}|{rt}|{tgt}"
            edges_by_key[key] = e
    nodes = list(nodes_by_id.values())
    edges = list(edges_by_key.values())
    return {
        "work_id": "",
        "nodes": nodes,
        "edges": edges,
        "meta": {
            "semantic_available": semantic_any,
            "graph_scope": "workspace_union_1hop",
            "graph_depth_effective": 1,
            "workspace_node_count": len(nodes),
            "workspace_edge_count": len(edges),
            "is_truncated": truncated_any,
            "available_expansions": [],
        },
    }


def legacy_workspace_graph_union(
    settings: Settings,
    workspace_id: str,
    *,
    neighbor_limit: int = 160,
) -> dict[str, Any] | None:
    """Per-work 1-hop union (pre–Wave-J behavior)."""

    driver = _neo4j_driver(settings)
    try:
        with driver.session() as session:
            row = session.run(
                """
                MATCH (ws:Workspace {id: $wid})
                OPTIONAL MATCH (ws)-[:CONTAINS]->(w:Work)
                RETURN ws.id AS wid, collect(DISTINCT w.id) AS wids
                """,
                wid=workspace_id,
            ).single()
        if not row or not row["wid"]:
            return None
        work_ids = [str(x) for x in (row["wids"] or []) if x]
        if not work_ids:
            return {
                "work_id": "",
                "nodes": [],
                "edges": [],
                "meta": {
                    "semantic_available": False,
                    "graph_scope": "workspace_union_1hop",
                    "graph_depth_effective": 1,
                    "workspace_node_count": 0,
                    "workspace_edge_count": 0,
                    "is_truncated": False,
                    "available_expansions": [],
                    "workspace_id": workspace_id,
                    "source_work_ids": [],
                },
            }
        per_lim = max(30, min(neighbor_limit, 800 // max(1, len(work_ids))))
        payloads: list[dict[str, Any]] = []
        for wid in work_ids:
            g = works_api.work_graph_neighborhood(
                settings,
                wid,
                neighbor_limit=per_lim,
                depth=1,
            )
            if g:
                payloads.append(g)
        merged = merge_graph_payloads(payloads)
        merged["meta"]["workspace_id"] = workspace_id
        merged["meta"]["source_work_ids"] = work_ids
        return merged
    finally:
        driver.close()


def _primary_label(labels: list[Any]) -> str:
    order = ["Work", "Author", "Method", "Dataset", "Venue", "Institution", "Authorship"]
    labs = [str(x) for x in (labels or [])]
    for o in order:
        if o in labs:
            return o
    return labs[0] if labs else "Node"


def _node_dict_from_neo(node: Any) -> dict[str, Any] | None:
    if node is None:
        return None
    props = dict(node)
    nid = props.get("id")
    if nid is None:
        nid = str(node.element_id)
    nid = str(nid).strip()
    if not nid:
        return None
    ntype = _primary_label(list(node.labels))
    raw_title = str(props.get("title") or props.get("name") or props.get("full_name") or "").strip()
    label = (raw_title[:200] if raw_title else nid)[:200]
    subtitle = ntype
    if ntype == "Work" and props.get("publication_year") is not None:
        subtitle = f"Work · {int(props['publication_year'])}"
    center_props: dict[str, Any] = {}
    if props.get("publication_year") is not None:
        center_props["publication_year"] = props["publication_year"]
    if props.get("doi"):
        center_props["doi"] = str(props["doi"]).strip()
    if props.get("arxiv_id"):
        center_props["arxiv_id"] = str(props["arxiv_id"]).strip()
    if props.get("venue_name"):
        center_props["venue"] = str(props["venue_name"]).strip()[:200]
    return {
        "id": nid,
        "type": ntype,
        "label": label,
        "display_label": label,
        "subtitle": subtitle,
        "node_kind": ntype,
        "properties": center_props,
    }


def _edge_key(aid: str, rt: str, bid: str) -> str:
    return f"{aid}|{rt}|{bid}"


def _edge_dict_from_rel(a: Any, b: Any, rel: Any, seq: int) -> dict[str, Any]:
    rt = str(rel.type) if rel is not None else ""
    src = str(dict(a).get("id") or a.element_id)
    tgt = str(dict(b).get("id") or b.element_id)
    payload = f"{src}\0{rt}\0{tgt}\0{seq}".encode()
    eid = "e_" + hashlib.sha256(payload).hexdigest()[:22]
    return {"id": eid, "source": src, "target": tgt, "type": rt}


def _enrich_edges_workspace(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> None:
    by_id = {n["id"]: n for n in nodes}

    def _display_type(rel_type: str) -> str:
        t = (rel_type or "").strip()
        return t.replace("_", " ") if t else "related"

    for seq, edge in enumerate(edges):
        src_id = str(edge.get("source") or "")
        tgt_id = str(edge.get("target") or "")
        src_n = by_id.get(src_id, {})
        tgt_n = by_id.get(tgt_id, {})
        sl = str(src_n.get("display_label") or src_n.get("label") or src_id)
        tl = str(tgt_n.get("display_label") or tgt_n.get("label") or tgt_id)
        rt = str(edge.get("type") or "")
        disp_t = _display_type(rt)
        edge["display_type"] = disp_t
        edge["source_label"] = sl
        edge["target_label"] = tl
        edge["summary"] = f"{sl} —[{disp_t}]→ {tl}"
        edge["direction"] = "lateral"


def _annotate_membership_and_cites(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    internal_work_ids: set[str],
) -> tuple[int, int]:
    """Set workspace_membership and per-Work CITES counts; return (internal_node_count, external_node_count)."""

    iws = {str(x) for x in internal_work_ids}

    def _outgoing_cite_targets(wid: str) -> list[str]:
        out: list[str] = []
        for e in edges:
            if str(e.get("type") or "") != "CITES":
                continue
            if str(e.get("source") or "") == wid:
                out.append(str(e.get("target") or ""))
        return out

    internal_nodes = 0
    external_nodes = 0
    for n in nodes:
        nid = str(n["id"])
        ntype = str(n.get("type") or "")
        if ntype == "Work":
            if nid in iws:
                n["workspace_membership"] = "internal"
                internal_nodes += 1
            else:
                n["workspace_membership"] = "external"
                external_nodes += 1
            targets = _outgoing_cite_targets(nid)
            internal_cite = sum(1 for t in targets if t in iws)
            external_cite = sum(1 for t in targets if t and t not in iws)
            n["internal_cite_count"] = internal_cite
            n["external_cite_count"] = external_cite
        else:
            attached_internal = False
            for e in edges:
                s, t = str(e.get("source") or ""), str(e.get("target") or "")
                if s != nid and t != nid:
                    continue
                other = t if s == nid else s
                if other in iws:
                    attached_internal = True
                    break
            n["workspace_membership"] = "internal" if attached_internal else "external"
            if n["workspace_membership"] == "internal":
                internal_nodes += 1
            else:
                external_nodes += 1
    return internal_nodes, external_nodes


def _filter_external_works_by_min_citers(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    internal_work_ids: set[str],
    min_citers: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Drop external :Work nodes cited by fewer than min_citers distinct internal works."""

    if min_citers <= 0:
        return nodes, edges
    iws = internal_work_ids
    cite_count: dict[str, set[str]] = {}
    for e in edges:
        if str(e.get("type") or "") != "CITES":
            continue
        s, t = str(e.get("source") or ""), str(e.get("target") or "")
        if s in iws and t not in iws:
            cite_count.setdefault(t, set()).add(s)
    drop_works = {w for w, srcs in cite_count.items() if len(srcs) < min_citers}
    if not drop_works:
        return nodes, edges
    # drop external works below threshold
    new_nodes = [
        n
        for n in nodes
        if not (str(n.get("type")) == "Work" and n["id"] in drop_works and n["id"] not in iws)
    ]
    kept = {n["id"] for n in new_nodes}
    new_edges = [e for e in edges if str(e.get("source") or "") in kept and str(e.get("target") or "") in kept]
    return new_nodes, new_edges


def parse_node_types_csv(raw: str | None) -> list[str] | None:
    if not raw or not str(raw).strip():
        return None
    parts = [p.strip() for p in re.split(r"[,;]", str(raw)) if p.strip()]
    cleaned = [p for p in parts if p in ALLOWED_NODE_TYPES]
    return cleaned or None


def _gds_runtime_available(session: Any) -> bool:
    try:
        session.run("RETURN gds.version() AS v").consume()
        return True
    except Exception:  # noqa: BLE001
        return False


def _gds_graph_drop(session: Any, graph_name: str) -> None:
    try:
        session.run("CALL gds.graph.drop($gn, false) YIELD graphName", gn=graph_name).consume()
    except Exception:  # noqa: BLE001
        pass


def _edge_dict_from_ids(src: str, tgt: str, rt: str, seq: int) -> dict[str, Any]:
    payload = f"{src}\0{rt}\0{tgt}\0{seq}".encode()
    eid = "e_" + hashlib.sha256(payload).hexdigest()[:22]
    return {"id": eid, "source": src, "target": tgt, "type": rt}


def _gds_internal_workspace_work_graph(
    session: Any,
    *,
    settings: Settings,
    workspace_id: str,
    internal_ids: list[str],
    cap: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool] | None:
    """
    Optional GDS path: project internal :Work subgraph (workspace members + Work--Work rels).
    Returns None on any failure so callers fall back to Cypher.
    """

    if not settings.gds_enabled or not _gds_runtime_available(session):
        return None
    if len(internal_ids) < 51:
        return None
    gn = "ws_" + hashlib.sha256(f"{workspace_id}:{uuid.uuid4().hex}".encode()).hexdigest()[:18]
    nq = (
        "MATCH (ws:Workspace {id: $wid})-[:CONTAINS]->(w:Work) "
        "RETURN id(w) AS id, labels(w) AS labels"
    )
    rq = (
        "MATCH (ws:Workspace {id: $wid})-[:CONTAINS]->(a:Work)-[r]-(b:Work) "
        "WHERE (ws)-[:CONTAINS]->(b) "
        "RETURN id(a) AS source, id(b) AS target, type(r) AS type"
    )
    try:
        row = session.run(
            """
            CALL gds.graph.project.cypher(
              $gn,
              $nq,
              $rq,
              {validateRelationships: false, parameters: {wid: $wid}}
            ) YIELD relationshipCount
            RETURN relationshipCount AS rc
            """,
            gn=gn,
            nq=nq,
            rq=rq,
            wid=workspace_id,
        ).single()
        rc = int(row["rc"] or 0) if row else 0
        if rc <= 0:
            _gds_graph_drop(session, gn)
            return None
    except Exception:  # noqa: BLE001
        _gds_graph_drop(session, gn)
        return None

    neo_ids: set[int] = set()
    triples: list[tuple[int, int, str]] = []
    truncated = False
    stream = None
    try:
        try:
            stream = session.run(
                """
                CALL gds.graph.relationshipStream($gn)
                YIELD sourceNodeId, targetNodeId, relationshipType
                RETURN sourceNodeId, targetNodeId, relationshipType
                LIMIT $cap
                """,
                gn=gn,
                cap=max(1, cap),
            )
        except Exception:  # noqa: BLE001
            try:
                stream = session.run(
                    """
                    CALL gds.graph.streamRelationships($gn)
                    YIELD sourceNodeId, targetNodeId, relationshipType
                    RETURN sourceNodeId, targetNodeId, relationshipType
                    LIMIT $cap
                    """,
                    gn=gn,
                    cap=max(1, cap),
                )
            except Exception:  # noqa: BLE001
                _gds_graph_drop(session, gn)
                return None
        if stream is None:
            _gds_graph_drop(session, gn)
            return None
        n_seen = 0
        for rec in stream:
            n_seen += 1
            sn = int(rec["sourceNodeId"])
            tn = int(rec["targetNodeId"])
            rt = str(rec["relationshipType"] or "")
            neo_ids.add(sn)
            neo_ids.add(tn)
            triples.append((sn, tn, rt))
        truncated = n_seen >= cap
    except Exception:  # noqa: BLE001
        _gds_graph_drop(session, gn)
        return None
    finally:
        _gds_graph_drop(session, gn)

    if not triples:
        return None

    id_map: dict[int, str] = {}
    if neo_ids:
        mrows = session.run(
            """
            UNWIND $neo AS nid
            MATCH (w:Work)
            WHERE id(w) = nid
            RETURN nid AS neo, w.id AS wid, w
            """,
            neo=list(neo_ids),
        )
        for mr in mrows:
            id_map[int(mr["neo"])] = str(mr["wid"])

    if len(id_map) < 2:
        return None

    nodes_by_id: dict[str, dict[str, Any]] = {}
    for wid in internal_ids:
        wrow = session.run("MATCH (w:Work {id: $id}) RETURN w", id=wid).single()
        if wrow and wrow["w"] is not None:
            nd = _node_dict_from_neo(wrow["w"])
            if nd:
                nodes_by_id[nd["id"]] = nd

    edges_by_key: dict[str, dict[str, Any]] = {}
    for seq, (sn, tn, rt) in enumerate(triples):
        sa = id_map.get(sn)
        tb = id_map.get(tn)
        if not sa or not tb:
            continue
        ed = _edge_dict_from_ids(sa, tb, rt, seq)
        edges_by_key[_edge_key(ed["source"], ed["type"], ed["target"])] = ed

    return list(nodes_by_id.values()), list(edges_by_key.values()), truncated


def _cypher_append_authorships(
    session: Any,
    *,
    workspace_id: str,
    internal_ids: list[str],
    cap: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
    """Add HAS_AUTHORSHIP / OF_AUTHOR edges for internal works (bounded)."""

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
        w, r1, ash, r2, a = rec["w"], rec["r1"], rec["ash"], rec["r2"], rec["a"]
        for node in (w, ash, a):
            nd = _node_dict_from_neo(node)
            if nd:
                nodes_by_id[nd["id"]] = nd
        if w is not None and ash is not None and r1 is not None:
            e1 = _edge_dict_from_rel(w, ash, r1, len(edges_by_key))
            edges_by_key[_edge_key(e1["source"], e1["type"], e1["target"])] = e1
        if ash is not None and a is not None and r2 is not None:
            e2 = _edge_dict_from_rel(ash, a, r2, len(edges_by_key))
            edges_by_key[_edge_key(e2["source"], e2["type"], e2["target"])] = e2
    truncated = n >= cap
    return list(nodes_by_id.values()), list(edges_by_key.values()), truncated


def _merge_nodes_edges_lists(
    base_nodes: list[dict[str, Any]],
    base_edges: list[dict[str, Any]],
    extra_nodes: list[dict[str, Any]],
    extra_edges: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    nb = {n["id"]: n for n in base_nodes}
    for n in extra_nodes:
        nb.setdefault(n["id"], n)
    eb: dict[str, dict[str, Any]] = {}
    for e in base_edges:
        eb[_edge_key(str(e["source"]), str(e["type"]), str(e["target"]))] = e
    for e in extra_edges:
        eb[_edge_key(str(e["source"]), str(e["type"]), str(e["target"]))] = e
    return list(nb.values()), list(eb.values())


def _build_from_depth1_rows(
    session: Any,
    *,
    workspace_id: str,
    internal_ids: list[str],
    include_external: bool,
    node_types: list[str] | None,
    semantic_only: bool,
    cap: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
    types_empty = not node_types
    type_list = node_types or []
    sem_clause = ""
    params: dict[str, Any] = {
        "wid": workspace_id,
        "includeExternal": include_external,
        "typesEmpty": types_empty,
        "nodeTypes": type_list,
        "cap": cap,
        "semTypes": SEMANTIC_REL_TYPES_LIST,
    }
    if semantic_only:
        sem_clause = (
            "AND (type(r) IN $semTypes OR any(l IN labels(b) WHERE l IN ['Method','Dataset'])) "
        )
    q = (
        "MATCH (ws:Workspace {id: $wid})-[:CONTAINS]->(iw:Work) "
        "WITH collect(DISTINCT iw.id) AS internalIds "
        "MATCH (a:Work)-[r]-(b) "
        "WHERE a.id IN internalIds "
        "AND ($includeExternal OR NOT b:Work OR b.id IN internalIds) "
        "AND ($typesEmpty OR any(l IN labels(b) WHERE l IN $nodeTypes)) "
        f"{sem_clause}"
        "RETURN DISTINCT a, r, b "
        "LIMIT $cap"
    )
    nodes_by_id: dict[str, dict[str, Any]] = {}
    edges_by_key: dict[str, dict[str, Any]] = {}
    truncated = False
    count = 0
    for rec in session.run(q, **params):
        count += 1
        a, rel, b = rec["a"], rec["r"], rec["b"]
        na = _node_dict_from_neo(a)
        nb = _node_dict_from_neo(b)
        if na:
            nodes_by_id[na["id"]] = na
        if nb:
            nodes_by_id[nb["id"]] = nb
        if na and nb and rel is not None:
            ed = _edge_dict_from_rel(a, b, rel, len(edges_by_key))
            edges_by_key[_edge_key(ed["source"], ed["type"], ed["target"])] = ed
    if count >= cap:
        truncated = True
    return list(nodes_by_id.values()), list(edges_by_key.values()), truncated


def _build_from_depth2_rows(
    session: Any,
    *,
    workspace_id: str,
    internal_ids: list[str],
    include_external: bool,
    node_types: list[str] | None,
    semantic_only: bool,
    cap: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
    types_empty = not node_types
    type_list = node_types or []
    sem_clause = ""
    if semantic_only:
        sem_clause = (
            "AND (type(r1) IN $semTypes OR type(r2) IN $semTypes "
            "OR any(l IN labels(m) WHERE l IN ['Method','Dataset']) "
            "OR any(l IN labels(b) WHERE l IN ['Method','Dataset'])) "
        )
    q = (
        "MATCH (ws:Workspace {id: $wid})-[:CONTAINS]->(iw:Work) "
        "WITH collect(DISTINCT iw.id) AS I "
        "MATCH (a:Work)-[r1]-(m)-[r2]-(b) "
        "WHERE a.id IN I "
        "AND (NOT m:Work OR m.id IN I OR $includeExternal) "
        "AND (NOT b:Work OR b.id IN I OR $includeExternal) "
        "AND ($typesEmpty OR any(l IN labels(b) WHERE l IN $nodeTypes)) "
        f"{sem_clause}"
        "RETURN DISTINCT a, r1, m, r2, b "
        "LIMIT $lim"
    )
    nodes_by_id: dict[str, dict[str, Any]] = {}
    edges_by_key: dict[str, dict[str, Any]] = {}
    lim = max(1, cap // 2)
    params = {
        "wid": workspace_id,
        "includeExternal": include_external,
        "typesEmpty": types_empty,
        "nodeTypes": type_list,
        "lim": lim,
        "semTypes": SEMANTIC_REL_TYPES_LIST,
    }
    n_rows = 0
    for rec in session.run(q, **params):
        n_rows += 1
        a, r1, m, r2, b = rec["a"], rec["r1"], rec["m"], rec["r2"], rec["b"]
        for node in (a, m, b):
            nd = _node_dict_from_neo(node)
            if nd:
                nodes_by_id[nd["id"]] = nd
        if a is not None and m is not None and r1 is not None:
            e1 = _edge_dict_from_rel(a, m, r1, len(edges_by_key))
            edges_by_key[_edge_key(e1["source"], e1["type"], e1["target"])] = e1
        if m is not None and b is not None and r2 is not None:
            e2 = _edge_dict_from_rel(m, b, r2, len(edges_by_key))
            edges_by_key[_edge_key(e2["source"], e2["type"], e2["target"])] = e2
    truncated = n_rows >= lim
    return list(nodes_by_id.values()), list(edges_by_key.values()), truncated


def _semantic_any(session: Any, internal_ids: list[str]) -> bool:
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


def project_workspace_graph(
    settings: Settings,
    workspace_id: str,
    *,
    mode: str = "inner_only",
    depth: int = 1,
    include_external: bool = False,
    node_types: str | None = None,
    neighbor_limit: int = 200,
    external_min_internal_citers: int = 0,
) -> dict[str, Any] | None:
    """
    Workspace graph v2. Modes: inner_only, union_1hop, semantic_layer, full.
    ``external_min_internal_citers``: when >0, keep external :Work only if cited by >= N internal works.
    """

    mode_norm = (mode or "inner_only").strip().lower()
    depth_eff = 2 if int(depth) >= 2 else 1
    cap = min(MAX_NEIGHBORS_CAP, max(1, min(int(neighbor_limit), 2000)))
    if depth_eff >= 2:
        cap = min(MAX_NEIGHBORS_CAP, cap)
    types_list = parse_node_types_csv(node_types)

    driver = _neo4j_driver(settings)
    try:
        with driver.session() as session:
            row = session.run(
                """
                MATCH (ws:Workspace {id: $wid})
                OPTIONAL MATCH (ws)-[:CONTAINS]->(w:Work)
                RETURN ws.id AS wid, collect(DISTINCT w.id) AS wids
                """,
                wid=workspace_id,
            ).single()
            if not row or not row["wid"]:
                return None
            internal_ids = [str(x) for x in (row["wids"] or []) if x]
            iws = set(internal_ids)
            gds_avail = _gds_runtime_available(session)

        if mode_norm == "union_1hop":
            out = legacy_workspace_graph_union(settings, workspace_id, neighbor_limit=neighbor_limit)
            if out is None:
                return None
            nodes = list(out.get("nodes") or [])
            edges = list(out.get("edges") or [])
            _enrich_edges_workspace(nodes, edges)
            inc, exc = _annotate_membership_and_cites(nodes, edges, iws)
            meta = dict(out.get("meta") or {})
            meta.update(
                {
                    "graph_scope": "workspace_v2",
                    "mode": mode_norm,
                    "graph_depth_requested": int(depth),
                    "graph_depth_effective": 1,
                    "include_external": True,
                    "node_types_filter": types_list,
                    "internal_node_count": inc,
                    "external_node_count": exc,
                    "edge_count": len(edges),
                    "cap_applied": cap,
                    "workspace_id": workspace_id,
                    "source_work_ids": internal_ids,
                    "gds_used": False,
                    "gds_runtime_available": gds_avail,
                },
            )
            out["meta"] = meta
            return out

        if not internal_ids:
            return {
                "work_id": "",
                "nodes": [],
                "edges": [],
                "meta": {
                    "semantic_available": False,
                    "graph_scope": "workspace_v2",
                    "mode": mode_norm,
                    "graph_depth_requested": int(depth),
                    "graph_depth_effective": depth_eff,
                    "include_external": include_external,
                    "node_types_filter": types_list or [],
                    "internal_node_count": 0,
                    "external_node_count": 0,
                    "edge_count": 0,
                    "is_truncated": False,
                    "cap_applied": cap,
                    "workspace_id": workspace_id,
                    "source_work_ids": [],
                    "available_expansions": ["add_works"],
                    "gds_used": False,
                    "gds_runtime_available": gds_avail,
                },
            }

        semantic_only = mode_norm == "semantic_layer"
        inc_ext = include_external

        with driver.session() as session:
            if depth_eff == 1:
                nodes, edges, truncated = _build_from_depth1_rows(
                    session,
                    workspace_id=workspace_id,
                    internal_ids=internal_ids,
                    include_external=inc_ext,
                    node_types=types_list,
                    semantic_only=semantic_only,
                    cap=cap,
                )
                gds_used = False
            else:
                try_gds = (
                    settings.gds_enabled
                    and gds_avail
                    and not inc_ext
                    and not semantic_only
                    and mode_norm != "union_1hop"
                    and len(internal_ids) > 50
                    and (types_list is None or "Work" in types_list)
                )
                gds_pack = None
                if try_gds:
                    gds_pack = _gds_internal_workspace_work_graph(
                        session,
                        settings=settings,
                        workspace_id=workspace_id,
                        internal_ids=internal_ids,
                        cap=cap,
                    )
                if gds_pack is not None:
                    nodes, edges, truncated = gds_pack
                    gds_used = True
                    if types_list is None or "Author" in types_list or "Authorship" in types_list:
                        an, ae, atr = _cypher_append_authorships(
                            session,
                            workspace_id=workspace_id,
                            internal_ids=internal_ids,
                            cap=max(30, cap // 2),
                        )
                        nodes, edges = _merge_nodes_edges_lists(nodes, edges, an, ae)
                        truncated = truncated or atr
                else:
                    nodes, edges, truncated = _build_from_depth2_rows(
                        session,
                        workspace_id=workspace_id,
                        internal_ids=internal_ids,
                        include_external=inc_ext,
                        node_types=types_list,
                        semantic_only=semantic_only,
                        cap=cap,
                    )
                    gds_used = False

            sem = _semantic_any(session, internal_ids)

        if external_min_internal_citers > 0 and inc_ext:
            nodes, edges = _filter_external_works_by_min_citers(
                nodes,
                edges,
                iws,
                external_min_internal_citers,
            )

        _enrich_edges_workspace(nodes, edges)
        inc_n, exc_n = _annotate_membership_and_cites(nodes, edges, iws)

        expansions: list[str] = []
        if truncated:
            expansions.append("increase_neighbor_limit")
        if depth_eff == 1:
            expansions.extend(["depth_2", "include_external", "expand_node"])

        meta: dict[str, Any] = {
            "semantic_available": sem,
            "graph_scope": "workspace_v2",
            "mode": mode_norm,
            "graph_depth_requested": int(depth),
            "graph_depth_effective": depth_eff,
            "include_external": inc_ext,
            "node_types_filter": types_list or [],
            "internal_node_count": inc_n,
            "external_node_count": exc_n,
            "edge_count": len(edges),
            "is_truncated": truncated,
            "cap_applied": cap,
            "workspace_id": workspace_id,
            "source_work_ids": internal_ids,
            "available_expansions": expansions,
            "gds_used": gds_used,
            "gds_runtime_available": gds_avail,
        }
        return {"work_id": "", "nodes": nodes, "edges": edges, "meta": meta}
    finally:
        driver.close()


def workspace_graph_stats(settings: Settings, workspace_id: str) -> dict[str, Any] | None:
    driver = _neo4j_driver(settings)
    try:
        with driver.session() as session:
            row = session.run(
                """
                MATCH (ws:Workspace {id: $wid})
                OPTIONAL MATCH (ws)-[:CONTAINS]->(w:Work)
                RETURN ws.id AS wid, count(DISTINCT w) AS works_n, collect(DISTINCT w.id) AS wids
                """,
                wid=workspace_id,
            ).single()
            if not row or not row["wid"]:
                return None
            wids = [str(x) for x in (row["wids"] or []) if x is not None]
            works_count = int(row["works_n"] or 0)
            if works_count == 0:
                return {
                    "workspace_id": workspace_id,
                    "works_count": 0,
                    "authors_count": 0,
                    "internal_citations": 0,
                    "external_citations": 0,
                    "external_works_count": 0,
                }
            arow = session.run(
                """
                MATCH (ws:Workspace {id: $wid})-[:CONTAINS]->(:Work)-[:HAS_AUTHORSHIP]->(:Authorship)-[:OF_AUTHOR]->(a:Author)
                RETURN count(DISTINCT a) AS c
                """,
                wid=workspace_id,
            ).single()
            authors_count = int(arow["c"]) if arow else 0
            irow = session.run(
                """
                MATCH (ws:Workspace {id: $wid})-[:CONTAINS]->(iw:Work)
                WITH collect(DISTINCT iw.id) AS I
                MATCH (a:Work)-[:CITES]->(b:Work)
                WHERE a.id IN I AND b.id IN I
                RETURN count(*) AS c
                """,
                wid=workspace_id,
            ).single()
            internal_citations = int(irow["c"]) if irow else 0
            erow = session.run(
                """
                MATCH (ws:Workspace {id: $wid})-[:CONTAINS]->(iw:Work)
                WITH collect(DISTINCT iw.id) AS I
                MATCH (a:Work)-[:CITES]->(b:Work)
                WHERE a.id IN I AND NOT b.id IN I
                RETURN count(*) AS c, count(DISTINCT b) AS dw
                """,
                wid=workspace_id,
            ).single()
            external_citations = int(erow["c"]) if erow else 0
            external_works_count = int(erow["dw"]) if erow else 0
        return {
            "workspace_id": workspace_id,
            "works_count": works_count,
            "authors_count": authors_count,
            "internal_citations": internal_citations,
            "external_citations": external_citations,
            "external_works_count": external_works_count,
        }
    finally:
        driver.close()


def workspace_graph_neighbors(
    settings: Settings,
    workspace_id: str,
    node_id: str,
    *,
    depth: int = 1,
    limit: int = 80,
) -> dict[str, Any] | None:
    """1-hop (or shallow) neighborhood for lazy expand; does not require node to be in workspace."""

    nid = (node_id or "").strip()
    if not nid:
        return None
    lim = max(1, min(int(limit), 200))
    driver = _neo4j_driver(settings)
    try:
        with driver.session() as session:
            ws_row = session.run(
                "MATCH (ws:Workspace {id: $wid}) RETURN ws.id AS wid",
                wid=workspace_id,
            ).single()
            if not ws_row or not ws_row["wid"]:
                return None
            rows = session.run(
                """
                MATCH (n {id: $nid})
                MATCH (n)-[r]-(m)
                RETURN n, r, m
                LIMIT $lim
                """,
                nid=nid,
                lim=lim,
            )
            nodes_by_id: dict[str, dict[str, Any]] = {}
            edges_by_key: dict[str, dict[str, Any]] = {}
            for rec in rows:
                n, rel_obj, m = rec["n"], rec["r"], rec["m"]
                nn = _node_dict_from_neo(n)
                nm = _node_dict_from_neo(m)
                if nn:
                    nodes_by_id[nn["id"]] = nn
                if nm:
                    nodes_by_id[nm["id"]] = nm
                if n is not None and m is not None and rel_obj is not None:
                    ed = _edge_dict_from_rel(n, m, rel_obj, len(edges_by_key))
                    edges_by_key[_edge_key(ed["source"], ed["type"], ed["target"])] = ed
            nodes = list(nodes_by_id.values())
            edges = list(edges_by_key.values())
            row_ids = session.run(
                """
                MATCH (ws:Workspace {id: $wid})-[:CONTAINS]->(w:Work)
                RETURN collect(DISTINCT w.id) AS I
                """,
                wid=workspace_id,
            ).single()
            iws = {str(x) for x in (row_ids["I"] or []) if x}
            _enrich_edges_workspace(nodes, edges)
            _annotate_membership_and_cites(nodes, edges, iws)
        return {
            "workspace_id": workspace_id,
            "center_id": nid,
            "depth_requested": int(depth),
            "depth_effective": 1,
            "nodes": nodes,
            "edges": edges,
            "meta": {"graph_scope": "workspace_neighbors", "neighbor_limit_applied": lim},
        }
    finally:
        driver.close()


# Fix neighbors: rec should include relationship object - use rec["r"] from query RETURN n, r, m
