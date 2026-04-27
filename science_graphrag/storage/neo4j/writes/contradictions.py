"""Persist :CONTRADICTS edges between :Work nodes (BT12 / Wave 9) + article-grounded v1."""

from __future__ import annotations

import json
from typing import Any

from science_graphrag.ontology.article_contradictions import (
    compute_has_evidence,
    compute_underspecified,
    sanitize_provenance,
    sanitize_severity,
    sanitize_subtype,
    stable_article_contradiction_id,
    truncate_str,
)
from science_graphrag.storage.neo4j.client import _Neo4jClient

_ALLOWED_EXTRA_KEYS = frozenset(
    {
        "severity",
        "rationale_short",
        "provenance",
        "claim_pair_fingerprint",
        "claim_a_id",
        "claim_b_id",
        "claim_a_text",
        "claim_b_text",
        "quote_a",
        "quote_b",
        "scope_json",
        "confidence",
        "has_evidence",
        "underspecified",
        "rel_schema_version",
        "article_contradiction_id",
    }
)


def merge_work_contradicts(
    client: _Neo4jClient,
    work_id_a: str,
    work_id_b: str,
    *,
    subtype: str = "unspecified",
    **kwargs: Any,
) -> None:
    """Create a single directed CONTRADICTS edge (canonical order by id). Idempotent MERGE.

    Backward compatible: with no extra kwargs, only ``subtype`` and ``schema_version`` are set
    (legacy BT12 behavior).

    With optional keyword arguments (filtered), persists v1 article-grounded metadata on the
    relationship. When quotes meet the minimum gate and claim texts are present, also MERGEs an
    ``ArticleContradiction`` reification linked from both works.
    """
    a = str(work_id_a or "").strip()
    b = str(work_id_b or "").strip()
    if not a or not b or a == b:
        return
    lo, hi = (a, b) if a < b else (b, a)
    st = sanitize_subtype(subtype)

    if not kwargs:
        q = """
        MATCH (x:Work {id: $lo}), (y:Work {id: $hi})
        MERGE (x)-[r:CONTRADICTS]->(y)
        SET r.subtype = $subtype,
            r.schema_version = coalesce(r.schema_version, 1)
        """
        with client.session() as session:
            session.run(q, lo=lo, hi=hi, subtype=truncate_str(st, 120))
        return

    extra: dict[str, Any] = {k: v for k, v in kwargs.items() if k in _ALLOWED_EXTRA_KEYS and v is not None}

    severity = sanitize_severity(str(extra.pop("severity", "") or "nuanced"))
    rationale_short = truncate_str(str(extra.pop("rationale_short", "") or ""), 4000)
    provenance = sanitize_provenance(str(extra.pop("provenance", "") or "unspecified"))
    claim_pair_fingerprint = truncate_str(str(extra.pop("claim_pair_fingerprint", "") or ""), 200)
    claim_a_id = truncate_str(str(extra.pop("claim_a_id", "") or ""), 200)
    claim_b_id = truncate_str(str(extra.pop("claim_b_id", "") or ""), 200)
    claim_a_text = truncate_str(str(extra.pop("claim_a_text", "") or ""), 8000)
    claim_b_text = truncate_str(str(extra.pop("claim_b_text", "") or ""), 8000)
    quote_a = str(extra.pop("quote_a", "") or "")
    quote_b = str(extra.pop("quote_b", "") or "")
    scope_json = truncate_str(str(extra.pop("scope_json", "") or ""), 12000)
    confidence = extra.pop("confidence", None)
    rel_schema_version = extra.pop("rel_schema_version", None)
    article_contradiction_id = truncate_str(str(extra.pop("article_contradiction_id", "") or ""), 220)
    has_evidence_kw = extra.pop("has_evidence", None)
    underspecified_kw = extra.pop("underspecified", None)
    # Ignore unknown kwargs (forward-compat).
    _ = extra

    has_evidence = (
        bool(has_evidence_kw) if has_evidence_kw is not None else compute_has_evidence(quote_a, quote_b)
    )
    underspecified = (
        bool(underspecified_kw)
        if underspecified_kw is not None
        else compute_underspecified(
            has_evidence=has_evidence,
            rationale_short=rationale_short,
            claim_a_text=claim_a_text,
            claim_b_text=claim_b_text,
        )
    )

    conf_f: float | None = None
    if confidence is not None:
        try:
            conf_f = float(confidence)
        except (TypeError, ValueError):
            conf_f = None

    rel_ver = int(rel_schema_version) if rel_schema_version is not None else 2

    cid = article_contradiction_id or stable_article_contradiction_id(lo, hi, claim_pair_fingerprint or None)
    create_article_node = has_evidence and bool(claim_a_text.strip()) and bool(claim_b_text.strip())

    q = """
    MATCH (x:Work {id: $lo}), (y:Work {id: $hi})
    MERGE (x)-[r:CONTRADICTS]->(y)
    SET r.subtype = $subtype,
        r.schema_version = coalesce(r.schema_version, 1),
        r.rel_schema_version = $rel_schema_version,
        r.severity = $severity,
        r.rationale_short = $rationale_short,
        r.provenance = $provenance,
        r.claim_pair_fingerprint = $claim_pair_fingerprint,
        r.claim_a_id = $claim_a_id,
        r.claim_b_id = $claim_b_id,
        r.claim_a_text = $claim_a_text,
        r.claim_b_text = $claim_b_text,
        r.quote_a = $quote_a,
        r.quote_b = $quote_b,
        r.scope_json = $scope_json,
        r.confidence = $confidence,
        r.has_evidence = $has_evidence,
        r.underspecified = $underspecified,
        r.article_contradiction_id = $article_contradiction_id
    """
    params: dict[str, Any] = {
        "lo": lo,
        "hi": hi,
        "subtype": truncate_str(st, 120),
        "rel_schema_version": rel_ver,
        "severity": severity,
        "rationale_short": rationale_short,
        "provenance": provenance,
        "claim_pair_fingerprint": claim_pair_fingerprint,
        "claim_a_id": claim_a_id,
        "claim_b_id": claim_b_id,
        "claim_a_text": claim_a_text,
        "claim_b_text": claim_b_text,
        "quote_a": truncate_str(quote_a, 12000),
        "quote_b": truncate_str(quote_b, 12000),
        "scope_json": scope_json,
        "confidence": conf_f,
        "has_evidence": has_evidence,
        "underspecified": underspecified,
        "article_contradiction_id": cid,
    }

    with client.session() as session:
        session.run(q, **params)
        if create_article_node:
            cprops = {
                "work_id_lo": lo,
                "work_id_hi": hi,
                "subtype": truncate_str(st, 120),
                "severity": severity,
                "provenance": provenance,
                "claim_pair_fingerprint": claim_pair_fingerprint,
                "claim_a_id": claim_a_id,
                "claim_b_id": claim_b_id,
                "claim_a_text": claim_a_text,
                "claim_b_text": claim_b_text,
                "quote_a": truncate_str(quote_a, 12000),
                "quote_b": truncate_str(quote_b, 12000),
                "rationale_short": rationale_short,
                "scope_json": scope_json,
                "has_evidence": has_evidence,
                "underspecified": underspecified,
                "rel_schema_version": rel_ver,
                "schema_version": 1,
            }
            cprops["payload_json"] = truncate_str(
                json.dumps(
                    {
                        "pair_id": claim_pair_fingerprint,
                        "subtype": st,
                        "severity": severity,
                        "provenance": provenance,
                        "claim_a_text": claim_a_text,
                        "claim_b_text": claim_b_text,
                        "quote_a": truncate_str(quote_a, 12000),
                        "quote_b": truncate_str(quote_b, 12000),
                        "rationale_short": rationale_short,
                    },
                    ensure_ascii=False,
                ),
                32000,
            )
            q2 = """
            MATCH (x:Work {id: $lo})-[r:CONTRADICTS]->(y:Work {id: $hi})
            MERGE (c:ArticleContradiction {id: $cid})
            SET c += $cprops
            MERGE (x)-[:ARTICLE_CONTRADICTION_RECORD]->(c)
            MERGE (y)-[:ARTICLE_CONTRADICTION_RECORD]->(c)
            SET r.article_contradiction_id = $cid
            """
            session.run(q2, lo=lo, hi=hi, cid=cid, cprops=cprops)
