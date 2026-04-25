"""Semantic graph writes (Method/Dataset projection and semantic relations)."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

from science_graphrag.domain.semantic_models import SemanticExtractionV1
from science_graphrag.storage.neo4j.client import _Neo4jClient


def _semantic_method_id(name: str) -> str:
    key = "method:" + re.sub(r"\s+", " ", name.strip().lower())
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))


def _semantic_dataset_id(name: str) -> str:
    key = "dataset:" + re.sub(r"\s+", " ", name.strip().lower())
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))


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

    for method in extraction.methods:
        if method.confidence < confidence_threshold:
            continue
        name = (method.name or "").strip()
        if not name:
            continue
        mid = _semantic_method_id(name)
        prov = _semantic_provenance_json(method.evidence)
        desc = (method.description_short or "").strip() or None
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
            conf=float(method.confidence),
            prov=prov,
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
                y.schema_version = 1
            MERGE (w)-[r:EVALUATED_ON]->(y)
            SET r.confidence = $conf,
                r.provenance_json = $prov,
                r.source_work_id = $wid
            """,
            wid=work_id,
            did=did,
            name=name[:500],
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
