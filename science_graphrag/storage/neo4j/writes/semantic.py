"""Semantic graph writes (Method/Dataset projection and semantic relations)."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

from science_graphrag.domain.semantic_models import SemanticExtractionV1, SemanticMethodV1
from science_graphrag.storage.neo4j.client import _Neo4jClient


def _semantic_method_id(name: str) -> str:
    key = "method:" + re.sub(r"\s+", " ", name.strip().lower())
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))


def _semantic_dataset_id(name: str) -> str:
    key = "dataset:" + re.sub(r"\s+", " ", name.strip().lower())
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))


def normalize_method_surface(name: str) -> str:
    """Lowercase single-spaced surface for search / dedup (ADR 023)."""
    return re.sub(r"\s+", " ", (name or "").strip().lower())


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


def _method_evidence_id(work_id: str, method_id: str, idx: int, quote: str) -> str:
    material = f"mev:{work_id}:{method_id}:{idx}:{quote[:120]}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, material))


def _method_node_schema_version(method: SemanticMethodV1) -> int:
    if (
        (method.description_markdown and method.description_markdown.strip())
        or (method.description_plaintext and method.description_plaintext.strip())
        or (method.method_kind and method.method_kind.strip())
    ):
        return 2
    return 1


def merge_method_into_canonical(client: _Neo4jClient, keep_id: str, drop_id: str) -> bool:
    """Rewire all method edges onto ``keep_id`` and delete ``drop_id`` (:Method)."""
    keep_id = (keep_id or "").strip()
    drop_id = (drop_id or "").strip()
    if not keep_id or not drop_id or keep_id == drop_id:
        return False
    with client.session() as session:
        return bool(session.execute_write(_merge_method_tx, keep_id, drop_id))


def _merge_method_tx(tx, keep_id: str, drop_id: str) -> bool:
    krec = tx.run("MATCH (k:Method {id: $id}) RETURN k AS node", id=keep_id).single()
    drec = tx.run("MATCH (d:Method {id: $id}) RETURN d AS node", id=drop_id).single()
    if not krec or not drec:
        return False
    kp = dict(krec["node"])
    dp = dict(drec["node"])

    def _longer(a: str | None, b: str | None) -> str:
        sa = (a or "").strip()
        sb = (b or "").strip()
        return sb if len(sb) > len(sa) else sa

    merged_name = _longer(kp.get("name"), dp.get("name")) or str(kp.get("name") or dp.get("name"))
    alias_pool: list[str] = []
    for src in (kp.get("aliases"), dp.get("aliases")):
        if isinstance(src, list):
            alias_pool.extend(str(x).strip() for x in src if str(x).strip())
    for nm in (kp.get("name"), dp.get("name")):
        t = str(nm or "").strip()
        if t and t != merged_name:
            alias_pool.append(t)
    seen: set[str] = set()
    dedup_aliases: list[str] = []
    for a in alias_pool:
        if a in seen or a == merged_name:
            continue
        seen.add(a)
        dedup_aliases.append(a[:500])
        if len(dedup_aliases) >= 50:
            break

    merged_short = _longer(kp.get("description_short"), dp.get("description_short")) or None
    merged_md = _longer(kp.get("description_markdown"), dp.get("description_markdown")) or None
    merged_plain = _longer(kp.get("description_plaintext"), dp.get("description_plaintext")) or None
    merged_kind = (kp.get("method_kind") or dp.get("method_kind") or None)
    if merged_kind is not None:
        merged_kind = str(merged_kind).strip()[:64] or None
    merged_src = (kp.get("description_source") or dp.get("description_source") or None)
    if merged_src is not None:
        merged_src = str(merged_src).strip()[:64] or None
    try:
        kconf = float(kp.get("description_confidence") or 0.0)
        dconf = float(dp.get("description_confidence") or 0.0)
        merged_dconf = max(kconf, dconf) if (kconf or dconf) else None
    except (TypeError, ValueError):
        merged_dconf = None
    schema_v = max(int(kp.get("schema_version") or 1), int(dp.get("schema_version") or 1))
    if merged_md or merged_plain or merged_kind:
        schema_v = max(schema_v, 2)

    tx.run(
        """
        MATCH (k:Method {id: $keep})
        SET k.name = $name,
            k.normalized_name = $norm,
            k.aliases = $aliases,
            k.description_short = coalesce($ds, k.description_short),
            k.description_markdown = CASE WHEN $dm IS NULL THEN k.description_markdown ELSE $dm END,
            k.description_plaintext = CASE WHEN $pt IS NULL THEN k.description_plaintext ELSE $pt END,
            k.method_kind = CASE WHEN $mk IS NULL THEN k.method_kind ELSE $mk END,
            k.description_source = CASE WHEN $src IS NULL THEN k.description_source ELSE $src END,
            k.description_confidence = CASE WHEN $dcf IS NULL THEN k.description_confidence ELSE $dcf END,
            k.schema_version = $schema_v
        """,
        keep=keep_id,
        name=str(merged_name)[:500],
        norm=normalize_method_surface(str(merged_name)),
        aliases=dedup_aliases,
        ds=merged_short,
        dm=merged_md,
        pt=merged_plain,
        mk=merged_kind,
        src=merged_src,
        dcf=merged_dconf,
        schema_v=int(schema_v),
    )

    tx.run(
        """
        MATCH (w:Work)-[r:USES_METHOD]->(d:Method {id: $drop})
        WITH w, r, $keep AS keepId
        MATCH (k:Method {id: keepId})
        MERGE (w)-[r2:USES_METHOD]->(k)
        SET r2.confidence = CASE
            WHEN coalesce(r.confidence, 0.0) >= coalesce(r2.confidence, 0.0) THEN r.confidence
            ELSE r2.confidence
        END,
        r2.provenance_json = CASE
            WHEN size(coalesce(r.provenance_json, '')) >= size(coalesce(r2.provenance_json, ''))
            THEN r.provenance_json
            ELSE r2.provenance_json
        END,
        r2.source_work_id = coalesce(r.source_work_id, r2.source_work_id)
        DELETE r
        """,
        drop=drop_id,
        keep=keep_id,
    )

    tx.run(
        """
        MATCH (d:Method {id: $drop})-[r:TRAINED_OR_TESTED_ON]->(ds:Dataset)
        WITH d, r, ds, $keep AS keepId
        MATCH (k:Method {id: keepId})
        MERGE (k)-[r2:TRAINED_OR_TESTED_ON]->(ds)
        SET r2.confidence = CASE
            WHEN coalesce(r.confidence, 0.0) >= coalesce(r2.confidence, 0.0) THEN r.confidence
            ELSE r2.confidence
        END,
        r2.provenance_json = CASE
            WHEN size(coalesce(r.provenance_json, '')) >= size(coalesce(r2.provenance_json, ''))
            THEN r.provenance_json
            ELSE r2.provenance_json
        END,
        r2.source_work_id = coalesce(r.source_work_id, r2.source_work_id)
        DELETE r
        """,
        drop=drop_id,
        keep=keep_id,
    )

    tx.run(
        """
        MATCH (d:Method {id: $drop})-[r:HAS_EVIDENCE]->(ev:MethodEvidence)
        WITH d, r, ev, $keep AS keepId
        MATCH (k:Method {id: keepId})
        MERGE (k)-[:HAS_EVIDENCE]->(ev)
        DELETE r
        """,
        drop=drop_id,
        keep=keep_id,
    )

    tx.run("MATCH (d:Method {id: $drop}) DETACH DELETE d", drop=drop_id)
    return True


def sync_work_semantic_layer(
    client: _Neo4jClient,
    work_id: str,
    extraction: SemanticExtractionV1,
    *,
    confidence_threshold: float = 0.35,
) -> None:
    """Project ontology-v1 Method/Dataset nodes and ADR-004 edges for one :Work."""
    with client.session() as session:
        session.execute_write(_sync_semantic_tx, work_id, extraction, confidence_threshold)


def add_method_alias(client: _Neo4jClient, method_id: str, alias: str) -> bool:
    alias_clean = str(alias or "").strip()
    if not method_id or not alias_clean:
        return False
    with client.session() as session:
        rec = session.run(
            """
            MATCH (n:Method {id: $id})
            WITH n, coalesce(n.aliases, []) + [$alias] AS all_aliases
            WITH n, reduce(acc = [], x IN all_aliases | CASE WHEN x = '' OR x IN acc THEN acc ELSE acc + x END) AS dedup_aliases
            SET n.aliases = dedup_aliases
            RETURN 1 AS ok
            """,
            id=method_id,
            alias=alias_clean,
        ).single()
        return bool(rec)


def add_dataset_alias(client: _Neo4jClient, dataset_id: str, alias: str) -> bool:
    alias_clean = str(alias or "").strip()
    if not dataset_id or not alias_clean:
        return False
    with client.session() as session:
        rec = session.run(
            """
            MATCH (n:Dataset {id: $id})
            WITH n, coalesce(n.aliases, []) + [$alias] AS all_aliases
            WITH n, reduce(acc = [], x IN all_aliases | CASE WHEN x = '' OR x IN acc THEN acc ELSE acc + x END) AS dedup_aliases
            SET n.aliases = dedup_aliases
            RETURN 1 AS ok
            """,
            id=dataset_id,
            alias=alias_clean,
        ).single()
        return bool(rec)


def _delete_work_method_evidence(tx, work_id: str) -> None:
    tx.run(
        """
        MATCH (w:Work {id: $wid})-[r:HAS_METHOD_EVIDENCE]->(e:MethodEvidence)
        OPTIONAL MATCH (m:Method)-[he:HAS_EVIDENCE]->(e)
        DELETE r, he
        DETACH DELETE e
        """,
        wid=work_id,
    )


def _sync_semantic_tx(
    tx,
    work_id: str,
    extraction: SemanticExtractionV1,
    confidence_threshold: float,
) -> None:
    tx.run("MATCH (w:Work {id: $wid})-[r:USES_METHOD]->() DELETE r", wid=work_id)
    tx.run("MATCH (w:Work {id: $wid})-[r:EVALUATED_ON]->() DELETE r", wid=work_id)
    tx.run(
        """
        MATCH (:Method)-[r:TRAINED_OR_TESTED_ON {source_work_id: $wid}]->(:Dataset)
        DELETE r
        """,
        wid=work_id,
    )
    _delete_work_method_evidence(tx, work_id)

    for method in extraction.methods:
        if method.confidence < confidence_threshold:
            continue
        name = (method.name or "").strip()
        if not name:
            continue
        mid = _semantic_method_id(name)
        prov = _semantic_provenance_json(method.evidence)
        desc = (method.description_short or "").strip() or None
        norm = normalize_method_surface(name)
        alias_list = [a.strip() for a in method.aliases if a and str(a).strip()][:40]
        dm = (method.description_markdown or "").strip() or None
        if dm and len(dm) > 12000:
            dm = dm[:12000]
        dplain = (method.description_plaintext or "").strip() or None
        if dplain and len(dplain) > 12000:
            dplain = dplain[:12000]
        mk = (method.method_kind or "").strip()[:64] or None
        dsrc = (method.description_source or "").strip()[:64] or None
        dcf = method.description_confidence
        schema_v = _method_node_schema_version(method)

        tx.run(
            """
            MATCH (w:Work {id: $wid})
            MERGE (x:Method {id: $mid})
            SET x.name = $name,
                x.normalized_name = $norm,
                x.aliases = $aliases,
                x.description_short = coalesce($desc, x.description_short),
                x.description_markdown = CASE WHEN $dm IS NULL THEN x.description_markdown ELSE $dm END,
                x.description_plaintext = CASE WHEN $dpt IS NULL THEN x.description_plaintext ELSE $dpt END,
                x.method_kind = CASE WHEN $mk IS NULL THEN x.method_kind ELSE $mk END,
                x.description_source = CASE WHEN $dsrc IS NULL THEN x.description_source ELSE $dsrc END,
                x.description_confidence = CASE
                    WHEN $dcf IS NULL THEN x.description_confidence
                    ELSE $dcf
                END,
                x.schema_version = CASE
                    WHEN coalesce(x.schema_version, 1) < $schema_v THEN $schema_v
                    ELSE coalesce(x.schema_version, 1)
                END
            MERGE (w)-[r:USES_METHOD]->(x)
            SET r.confidence = $conf,
                r.provenance_json = $prov,
                r.source_work_id = $wid
            """,
            wid=work_id,
            mid=mid,
            name=name[:500],
            norm=norm,
            aliases=alias_list,
            desc=desc,
            dm=dm,
            dpt=dplain,
            mk=mk,
            dsrc=dsrc,
            dcf=float(dcf) if dcf is not None else None,
            schema_v=int(schema_v),
            conf=float(method.confidence),
            prov=prov,
        )

        for idx, ev in enumerate(method.evidence[:8]):
            quote = (ev.quote or "").strip()[:400]
            chunk_id = (ev.chunk_id or "").strip()[:128] or None
            sec = (ev.section_heading or "").strip()[:256] or None
            eid = _method_evidence_id(work_id, mid, idx, quote)
            tx.run(
                """
                MATCH (w:Work {id: $wid}), (x:Method {id: $mid})
                MERGE (ev:MethodEvidence {id: $eid})
                SET ev.chunk_id = $chunk_id,
                    ev.quote = $quote,
                    ev.section_heading = $sec,
                    ev.source_work_id = $wid,
                    ev.schema_version = 1
                MERGE (x)-[:HAS_EVIDENCE]->(ev)
                MERGE (w)-[:HAS_METHOD_EVIDENCE]->(ev)
                """,
                wid=work_id,
                mid=mid,
                eid=eid,
                chunk_id=chunk_id,
                quote=quote or "",
                sec=sec,
            )

    for dataset in extraction.datasets:
        if dataset.confidence < confidence_threshold:
            continue
        name = (dataset.name or "").strip()
        if not name:
            continue
        did = _semantic_dataset_id(name)
        prov = _semantic_provenance_json(dataset.evidence)
        tx.run(
            """
            MATCH (w:Work {id: $wid})
            MERGE (y:Dataset {id: $did})
            SET y.name = $name,
                y.normalized_name = coalesce(y.normalized_name, $dnorm),
                y.schema_version = 1
            MERGE (w)-[r:EVALUATED_ON]->(y)
            SET r.confidence = $conf,
                r.provenance_json = $prov,
                r.source_work_id = $wid
            """,
            wid=work_id,
            did=did,
            name=name[:500],
            dnorm=re.sub(r"\s+", " ", name.strip().lower()),
            conf=float(dataset.confidence),
            prov=prov,
        )

    for rel in extraction.relations:
        if rel.confidence < confidence_threshold or rel.type != "trained_or_tested_on":
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
        mid = _semantic_method_id(mname)
        did = _semantic_dataset_id(dname)
        prov = _semantic_provenance_json(rel.evidence)
        tx.run(
            """
            MERGE (mm:Method {id: $mid})
            SET mm.name = coalesce(mm.name, $mname),
                mm.normalized_name = coalesce(mm.normalized_name, $mnorm)
            MERGE (dd:Dataset {id: $did})
            SET dd.name = coalesce(dd.name, $dname),
                dd.normalized_name = coalesce(dd.normalized_name, $dnorm)
            MERGE (mm)-[rr:TRAINED_OR_TESTED_ON]->(dd)
            SET rr.confidence = $conf,
                rr.provenance_json = $prov,
                rr.source_work_id = $wid
            """,
            mid=mid,
            did=did,
            mname=mname[:500],
            mnorm=normalize_method_surface(mname),
            dname=dname[:500],
            dnorm=re.sub(r"\s+", " ", dname.strip().lower()),
            conf=float(rel.confidence),
            prov=prov,
            wid=work_id,
        )
