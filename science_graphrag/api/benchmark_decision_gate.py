"""Read-only API: aggregated benchmark decision gate + trust signals (BT1)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(tags=["benchmark"])


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_benchmark_summary_path() -> Path:
    """Path to ``benchmark-metrics-summary.json`` (overridable in tests)."""

    return _repo_root() / "eval" / "results" / "benchmark-metrics-summary.json"


def _extract_trust_public(summary: dict[str, Any]) -> dict[str, Any]:
    """Per-family ``trust_aggregate`` + each member's ``trust_signal`` only."""

    out: dict[str, Any] = {}
    for fam_key in (
        "retrieval_family",
        "claims_family",
        "claims_production_family",
        "references_resolution_family",
        "concept_topic_family",
        "agent_tools_family",
    ):
        fam = summary.get(fam_key)
        if not isinstance(fam, dict):
            continue
        members: dict[str, Any] = {}
        for mid, block in fam.items():
            if mid in {"role", "trust_aggregate"} or not isinstance(block, dict):
                continue
            ts = block.get("trust_signal")
            if isinstance(ts, dict):
                members[str(mid)] = ts
        out[fam_key] = {
            "trust_aggregate": fam.get("trust_aggregate"),
            "members": members,
        }
    return out


class DecisionGateSummaryResponse(BaseModel):
    """Public slice of ``benchmark-metrics-summary.json`` for the Benchmark UI."""

    decision: str = Field(description="GO | CONDITIONAL-GO | NO-GO")
    reason: str
    criteria: dict[str, Any]
    trust_by_family: dict[str, Any]
    summary_path: str = Field(description="Resolved JSON path (for debugging)")


@router.get(
    "/benchmark/decision-gate-summary",
    response_model=DecisionGateSummaryResponse,
    summary="Benchmark decision gate + trust signals",
)
def get_decision_gate_summary(
    summary_path: Annotated[Path, Depends(default_benchmark_summary_path)],
) -> DecisionGateSummaryResponse:
    """Return a compact slice of ``benchmark-metrics-summary.json`` for the admin UI."""
    if not summary_path.is_file():
        raise HTTPException(status_code=404, detail="benchmark_metrics_summary_not_found")
    try:
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=500,
            detail="benchmark_metrics_summary_invalid",
        ) from exc
    dg = payload.get("decision_gate")
    if not isinstance(dg, dict):
        raise HTTPException(
            status_code=500,
            detail="benchmark_metrics_summary_missing_decision_gate",
        )
    return DecisionGateSummaryResponse(
        decision=str(dg.get("decision") or ""),
        reason=str(dg.get("reason") or ""),
        criteria=dict(dg.get("criteria") or {}),
        trust_by_family=_extract_trust_public(payload),
        summary_path=str(summary_path.resolve()),
    )
