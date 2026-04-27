"""Vocabulary and sanitizers for article-grounded Work–Work CONTRADICTS (v1)."""

from __future__ import annotations

import math
from typing import Any

# Align with tests/fixtures/benchmarks/contradictions_v1 gold.json and dual_validate extractor.
CONTRADICTION_SUBTYPES = frozenset(
    {
        "era_shift",
        "post_processing",
        "scaling",
        "design_paradigm",
        "architectural",
        "classical_vs_deep",
        "unspecified",
    }
)

SEVERITY_VALUES = frozenset({"direct", "nuanced"})

PROVENANCE_VALUES = frozenset(
    {
        "human_corpus",
        "benchmark_materialize",
        "llm_quote_gated",
        "legacy",
        "unspecified",
    }
)

# Keys allowed on API responses for CONTRADICTS edges (graph list + detail subset).
CONTRADICTION_REL_API_KEYS = frozenset(
    {
        "subtype",
        "severity",
        "rationale_short",
        "provenance",
        "claim_pair_fingerprint",
        "claim_a_id",
        "claim_b_id",
        "claim_a_text",
        "claim_b_text",
        "scope_json",
        "confidence",
        "has_evidence",
        "underspecified",
        "rel_schema_version",
        "schema_version",
        "article_contradiction_id",
        "quote_a",
        "quote_b",
        "quote_a_preview",
        "quote_b_preview",
    }
)

_MIN_QUOTE_LEN = 8


def truncate_str(value: str, max_len: int) -> str:
    s = (value or "").strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 1].rstrip() + "…"


def sanitize_subtype(raw: str | None) -> str:
    s = str(raw or "").strip().lower()
    return s if s in CONTRADICTION_SUBTYPES else "unspecified"


def sanitize_severity(raw: str | None) -> str:
    s = str(raw or "").strip().lower()
    return s if s in SEVERITY_VALUES else "nuanced"


def sanitize_provenance(raw: str | None) -> str:
    s = str(raw or "").strip().lower()
    return s if s in PROVENANCE_VALUES else "unspecified"


def quote_pair_meets_gate(quote_a: str, quote_b: str) -> bool:
    return len((quote_a or "").strip()) >= _MIN_QUOTE_LEN and len((quote_b or "").strip()) >= _MIN_QUOTE_LEN


def compute_has_evidence(quote_a: str, quote_b: str) -> bool:
    return quote_pair_meets_gate(quote_a, quote_b)


def compute_underspecified(
    *,
    has_evidence: bool,
    rationale_short: str,
    claim_a_text: str,
    claim_b_text: str,
) -> bool:
    if not has_evidence:
        return True
    if not (rationale_short or "").strip():
        return True
    if not (claim_a_text or "").strip() or not (claim_b_text or "").strip():
        return True
    return False


def stable_article_contradiction_id(work_id_a: str, work_id_b: str, fingerprint: str | None) -> str:
    """Deterministic id for :ArticleContradiction (canonical lexicographic work order)."""
    a = str(work_id_a or "").strip()
    b = str(work_id_b or "").strip()
    lo, hi = (a, b) if a < b else (b, a)
    fp = str(fingerprint or "").strip() or "default"
    return f"ac:{lo}:{hi}:{fp[:120]}"


def extract_contradiction_rel_api_props(rel_props: dict[str, Any], *, for_graph_list: bool) -> dict[str, Any]:
    """Whitelist + truncate Neo4j relationship properties for JSON APIs."""
    raw = dict(rel_props or {})
    out: dict[str, Any] = {}
    subtype = sanitize_subtype(raw.get("subtype"))
    out["subtype"] = subtype
    if raw.get("severity") is not None:
        out["severity"] = sanitize_severity(raw.get("severity"))
    if raw.get("provenance") is not None:
        out["provenance"] = sanitize_provenance(raw.get("provenance"))
    for key in (
        "claim_pair_fingerprint",
        "claim_a_id",
        "claim_b_id",
        "article_contradiction_id",
    ):
        if raw.get(key) is not None:
            v = str(raw.get(key) or "").strip()
            if v:
                out[key] = truncate_str(v, 200)
    for key in ("claim_a_text", "claim_b_text"):
        if raw.get(key) is not None:
            v = str(raw.get(key) or "").strip()
            if v:
                out[key] = truncate_str(v, 2000 if not for_graph_list else 400)
    if raw.get("scope_json") is not None:
        sj = str(raw.get("scope_json") or "").strip()
        if sj:
            out["scope_json"] = truncate_str(sj, 6000 if not for_graph_list else 800)
    if raw.get("confidence") is not None:
        try:
            c = float(raw.get("confidence"))
            if math.isfinite(c):
                out["confidence"] = max(0.0, min(1.0, c))
        except (TypeError, ValueError):
            pass
    for key in ("rel_schema_version", "schema_version"):
        if raw.get(key) is not None:
            try:
                out[key] = int(raw.get(key))
            except (TypeError, ValueError):
                pass
    qa = str(raw.get("quote_a") or "").strip()
    qb = str(raw.get("quote_b") or "").strip()
    has_evidence = compute_has_evidence(qa, qb)
    out["has_evidence"] = has_evidence
    rat = str(raw.get("rationale_short") or "").strip()
    underspecified = compute_underspecified(
        has_evidence=has_evidence,
        rationale_short=rat,
        claim_a_text=str(raw.get("claim_a_text") or ""),
        claim_b_text=str(raw.get("claim_b_text") or ""),
    )
    out["underspecified"] = underspecified
    if rat:
        out["rationale_short"] = truncate_str(rat, 2000 if not for_graph_list else 400)
    if for_graph_list:
        if qa:
            out["quote_a_preview"] = truncate_str(qa, 160)
        if qb:
            out["quote_b_preview"] = truncate_str(qb, 160)
    else:
        if qa:
            out["quote_a"] = truncate_str(qa, 8000)
        if qb:
            out["quote_b"] = truncate_str(qb, 8000)
    return {
        k: v
        for k, v in out.items()
        if k in CONTRADICTION_REL_API_KEYS
        and v is not None
        and (isinstance(v, bool) or isinstance(v, int) or isinstance(v, float) or v != "")
    }


def build_edge_contradiction_preview(api_props: dict[str, Any]) -> dict[str, Any]:
    """Compact object attached to workspace graph edges for UI chips."""
    keys = (
        "subtype",
        "severity",
        "provenance",
        "has_evidence",
        "underspecified",
        "claim_pair_fingerprint",
        "article_contradiction_id",
    )
    return {k: api_props[k] for k in keys if k in api_props}
