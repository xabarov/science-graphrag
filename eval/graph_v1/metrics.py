"""Metrics for graph-level benchmark after full ingest."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from eval.layer1.metrics import prf1_tp_fp_fn
from eval.layer1.spec import Layer1GoldSpec


@dataclass
class GraphSnapshot:
    """Observed graph state for one ingested work."""

    work_id: str
    work_title: str | None
    authorship_count: int
    institution_count: int
    cites_count: int
    cited_arxiv_ids: list[str] = field(default_factory=list)
    duplicate_work_fingerprints: int = 0
    related_version_edge_count: int = 0
    work_dedup_violation_count: int = 0

    def to_json_dict(self) -> dict[str, Any]:
        """Serialize snapshot for JSON reports."""

        return asdict(self)


def score_graph_snapshot(snapshot: GraphSnapshot, gold: Layer1GoldSpec) -> dict[str, Any]:
    """Compare graph snapshot against optional graph expectations in gold."""

    exp = gold.graph_expectations
    if exp is None:
        return {
            "has_expectations": False,
            "snapshot": snapshot.to_json_dict(),
            "contract": {
                "checks": {"graph_expectations_present": None},
                "passed": True,
            },
        }

    cited_gold = {value.strip() for value in exp.expected_cited_arxiv_ids if value.strip()}
    cited_pred = {value.strip() for value in snapshot.cited_arxiv_ids if value.strip()}
    arxiv_p, arxiv_r, arxiv_f1, tp, fp, fn = prf1_tp_fp_fn(cited_gold, cited_pred)

    def _bounded(value: int, min_value: int | None, max_value: int | None) -> bool | None:
        if min_value is None and max_value is None:
            return None
        if min_value is not None and value < min_value:
            return False
        if max_value is not None and value > max_value:
            return False
        return True

    dup_ok = None
    if exp.max_duplicate_work_fingerprints is not None:
        dup_ok = snapshot.duplicate_work_fingerprints <= exp.max_duplicate_work_fingerprints

    dedup_ok = None
    if exp.max_work_dedup_violations is not None:
        dedup_ok = snapshot.work_dedup_violation_count <= exp.max_work_dedup_violations

    rel_ok = None
    if exp.min_related_version_edges is not None or exp.max_related_version_edges is not None:
        rel_ok = _bounded(
            snapshot.related_version_edge_count,
            exp.min_related_version_edges,
            exp.max_related_version_edges,
        )

    checks = {
        "cites_range_ok": _bounded(snapshot.cites_count, exp.min_cites, exp.max_cites),
        "authorships_range_ok": _bounded(
            snapshot.authorship_count,
            exp.min_authorships,
            exp.max_authorships,
        ),
        "institutions_range_ok": _bounded(
            snapshot.institution_count,
            exp.min_institutions,
            exp.max_institutions,
        ),
        "duplicate_work_fingerprints_ok": dup_ok,
        "work_dedup_violations_ok": dedup_ok,
        "related_version_edges_ok": rel_ok,
    }
    contract_values = [value for value in checks.values() if value is not None]
    return {
        "has_expectations": True,
        "snapshot": snapshot.to_json_dict(),
        "cites_range_ok": checks["cites_range_ok"],
        "authorships_range_ok": checks["authorships_range_ok"],
        "institutions_range_ok": checks["institutions_range_ok"],
        "cited_arxiv_precision": arxiv_p,
        "cited_arxiv_recall": arxiv_r,
        "cited_arxiv_f1": arxiv_f1,
        "cited_arxiv_tp_fp_fn": {"tp": tp, "fp": fp, "fn": fn},
        "duplicate_work_fingerprints_ok": checks["duplicate_work_fingerprints_ok"],
        "work_dedup_violations_ok": checks["work_dedup_violations_ok"],
        "related_version_edges_ok": checks["related_version_edges_ok"],
        "contract": {
            "checks": checks,
            "passed": all(contract_values) if contract_values else True,
        },
    }
