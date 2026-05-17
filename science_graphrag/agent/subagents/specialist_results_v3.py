"""Typed merge payload for multi-specialist + subagent runs (Epic B2).

``specialist_results`` remains the legacy dict[str, list[dict]] of raw tool payloads.
``specialist_results_v3`` holds schema_version, ordered legs, and a derived merge block
for writer-facing provenance, confidence, and conflict surfacing.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

# Phase 6 of the orchestration stabilization plan (2026-05-07): typed
# completion-readiness markers consumed by the planner and salvage paths.
# Source of truth for the literal values is ``coordination.route_plan``
# (CompletionSignalId); this re-export lets v3 callers validate without
# importing the planner package.
from science_graphrag.agent.coordination.route_plan import CompletionSignalId as _CompletionSignalId
from science_graphrag.agent.subagent_output_contract import parse_managed_report_from_text

_SCHEMA_VERSION = 1

COMPLETION_STATE_VALUES: frozenset[str] = frozenset(
    _CompletionSignalId.__args__  # type: ignore[attr-defined]
)

_VERDICT_RE = re.compile(
    r"(?im)^\s*VERDICT\s*:\s*(PASS|FAIL|PARTIAL)\b",
)


def parse_verdict_from_text(text: str) -> str | None:
    """Return PASS|FAIL|PARTIAL from a verification-style body, or None."""
    m = _VERDICT_RE.search(str(text or ""))
    if not m:
        return None
    return m.group(1).upper()


def _parse_verdict(text: str) -> str | None:
    return parse_verdict_from_text(text)


def prior_specialist_results_v3(
    state: Mapping[str, Any], next_state: Mapping[str, Any]
) -> dict[str, Any] | None:
    """Pick v3 blob after a subgraph invoke (prefer channel output, then input state)."""
    for src in (next_state, state):
        v = src.get("specialist_results_v3")
        if isinstance(v, dict) and v:
            return v
    v0 = next_state.get("specialist_results_v3")
    if isinstance(v0, dict):
        return v0
    return None


def _confidence_for_leg(leg: dict[str, Any]) -> float:
    raw = leg.get("confidence")
    if isinstance(raw, (int, float)) and 0.0 <= float(raw) <= 1.0:
        return float(raw)
    if leg.get("terminal_state") not in (None, "succeeded"):
        return 0.0
    if leg.get("failure_code"):
        return 0.25
    return 0.85


def _evidence_origin_for_subagent_id(subagent_id: str) -> str:
    sid = str(subagent_id or "").strip()
    return f"subagent:{sid}" if sid else "subagent:unknown"


def _empty_merge_block() -> dict[str, Any]:
    return {
        "evidence_origin": "parent_tool",
        "confidence": 1.0,
        "conflict": None,
        "writer_directive": "",
        "partial_failure": False,
        "completion_state": "any_specialist_payload",
        "outcome_summary": "",
        "limitations": [],
        "next_checks": [],
        "report_sections_present": False,
    }


def empty_specialist_results_v3() -> dict[str, Any]:
    return {
        "schema_version": _SCHEMA_VERSION,
        "legs": [],
        "merge": _empty_merge_block(),
    }


def _attach_managed_report_to_leg(leg: dict[str, Any], text: str) -> dict[str, Any]:
    """Parse child text into ``leg[\"managed_report\"]`` for typed parent merge."""
    parsed = parse_managed_report_from_text(text)
    if any(
        (
            parsed.get("report_sections_present"),
            str(parsed.get("outcome_summary") or "").strip(),
            parsed.get("limitations"),
            parsed.get("next_checks"),
        )
    ):
        leg["managed_report"] = parsed
    return leg


def append_writer_directive(prev: dict[str, Any] | None, extra: str) -> dict[str, Any]:
    """Append free-text guidance for the writer merge block."""
    text = str(extra or "").strip()
    if not text:
        return prev if isinstance(prev, dict) else empty_specialist_results_v3()
    blob = dict(prev) if isinstance(prev, dict) else empty_specialist_results_v3()
    merge = dict(blob.get("merge") or {})
    existing = str(merge.get("writer_directive") or "").strip()
    merge["writer_directive"] = f"{existing}\n{text}".strip() if existing else text
    blob["merge"] = merge
    return blob


def annotate_completion_state(
    prev: dict[str, Any] | None, *, completion_state: str
) -> dict[str, Any]:
    """Stamp ``merge.completion_state`` on the v3 payload.

    Specialists call this after they have decided their leg is "ready". The
    planner (``planner_post_retrieval_handoff`` and salvage paths) inspects
    this value to decide whether to hand off to writer immediately.
    Unknown values fall back to ``any_specialist_payload`` so older callers
    cannot poison the merge.
    """
    base = dict(prev) if isinstance(prev, dict) else empty_specialist_results_v3()
    state = str(completion_state or "").strip()
    if state not in COMPLETION_STATE_VALUES:
        state = "any_specialist_payload"
    merge = dict(base.get("merge") or {})
    merge["completion_state"] = state
    base["merge"] = merge
    base["schema_version"] = _SCHEMA_VERSION
    return base


def append_parent_tool_leg(
    prev: dict[str, Any] | None,
    *,
    specialist_id: str,
    tool_payloads: list[dict[str, Any]],
    spawn_reason: str = "parent_specialist",
) -> dict[str, Any]:
    """Record one parent specialist hop (retrieval/graph) as a typed leg."""
    base = dict(prev) if isinstance(prev, dict) else empty_specialist_results_v3()
    legs = list(base.get("legs") or [])
    legs.append(
        {
            "kind": "parent_tool",
            "specialist_id": str(specialist_id),
            "spawn_reason": str(spawn_reason),
            "tool_payloads_count": len(tool_payloads),
            "tool_payloads_excerpt": _excerpt_payloads(tool_payloads),
            "evidence_origin": "parent_tool",
            "confidence": 0.9 if tool_payloads else 0.4,
            "terminal_state": "succeeded",
            "failure_code": None,
        }
    )
    base["schema_version"] = _SCHEMA_VERSION
    base["legs"] = legs
    base["merge"] = _compute_merge(legs)
    return base


def append_corpus_explore_leg(
    prev: dict[str, Any] | None,
    *,
    subagent_id: str,
    text: str,
    terminal_state: str,
    failure_code: str | None,
    issues: list[str],
    salvage_used: bool = False,
) -> dict[str, Any]:
    """Append a corpus_explore child leg (read-only exploration fanout)."""
    base = dict(prev) if isinstance(prev, dict) else empty_specialist_results_v3()
    legs = list(base.get("legs") or [])
    leg = {
        "kind": "corpus_explore",
        "subagent_id": str(subagent_id),
        "spawn_reason": "corpus_explore",
        "text_excerpt": str(text or "")[:8000],
        "issues": list(issues or [])[:32],
        "terminal_state": str(terminal_state),
        "failure_code": failure_code,
        "salvage_used": bool(salvage_used),
        "evidence_origin": _evidence_origin_for_subagent_id(subagent_id),
        "confidence": _confidence_for_child(terminal_state, failure_code, verdict=None),
    }
    _attach_managed_report_to_leg(leg, text)
    legs.append(leg)
    base["schema_version"] = _SCHEMA_VERSION
    base["legs"] = legs
    base["merge"] = _compute_merge(legs)
    return base


def append_research_plan_leg(
    prev: dict[str, Any] | None,
    *,
    subagent_id: str,
    text: str,
    terminal_state: str,
    failure_code: str | None,
    issues: list[str],
    salvage_used: bool = False,
    research_plan_write_attempted: bool = False,
    research_plan_write_ok: bool | None = None,
) -> dict[str, Any]:
    """Append a research-plan decomposition child leg."""
    base = dict(prev) if isinstance(prev, dict) else empty_specialist_results_v3()
    legs = list(base.get("legs") or [])
    leg = {
        "kind": "research_plan",
        "subagent_id": str(subagent_id),
        "spawn_reason": "research_plan",
        "text_excerpt": str(text or "")[:8000],
        "issues": list(issues or [])[:32],
        "terminal_state": str(terminal_state),
        "failure_code": failure_code,
        "salvage_used": bool(salvage_used),
        "research_plan_write_attempted": bool(research_plan_write_attempted),
        "research_plan_write_ok": research_plan_write_ok,
        "evidence_origin": _evidence_origin_for_subagent_id(subagent_id),
        "confidence": _confidence_for_child(terminal_state, failure_code, verdict=None),
    }
    _attach_managed_report_to_leg(leg, text)
    legs.append(leg)
    base["schema_version"] = _SCHEMA_VERSION
    base["legs"] = legs
    base["merge"] = _compute_merge(legs)
    return base


def append_claim_verification_leg(
    prev: dict[str, Any] | None,
    *,
    subagent_id: str,
    text: str,
    terminal_state: str,
    failure_code: str | None,
    issues: list[str],
    salvage_used: bool = False,
) -> dict[str, Any]:
    """Append a claim_verification child leg and recompute merge metadata."""
    base = dict(prev) if isinstance(prev, dict) else empty_specialist_results_v3()
    legs = list(base.get("legs") or [])
    verdict = _parse_verdict(text)
    conf = _confidence_for_child(terminal_state, failure_code, verdict)
    leg = {
        "kind": "claim_verification",
        "subagent_id": str(subagent_id),
        "spawn_reason": "claim_verification",
        "text_excerpt": str(text or "")[:8000],
        "verdict": verdict,
        "issues": list(issues or [])[:32],
        "terminal_state": str(terminal_state),
        "failure_code": failure_code,
        "salvage_used": bool(salvage_used),
        "evidence_origin": _evidence_origin_for_subagent_id(subagent_id),
        "confidence": conf,
    }
    _attach_managed_report_to_leg(leg, text)
    legs.append(leg)
    base["schema_version"] = _SCHEMA_VERSION
    base["legs"] = legs
    base["merge"] = _compute_merge(legs)
    return base


def _confidence_for_child(
    terminal_state: str, failure_code: str | None, verdict: str | None
) -> float:
    if terminal_state in {"failed", "cancelled", "timed_out"}:
        return 0.0
    if failure_code == "tool_denied":
        return 0.15
    if failure_code == "timeout":
        return 0.2
    if failure_code == "partial":
        return 0.45
    if verdict is None and terminal_state == "succeeded":
        return 0.35
    if verdict == "FAIL":
        return 0.5
    if verdict == "PARTIAL":
        return 0.65
    if verdict == "PASS":
        return 0.95
    return 0.7


def _excerpt_payloads(payloads: list[dict[str, Any]], max_items: int = 6) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in payloads[:max_items]:
        if not isinstance(p, dict):
            continue
        keys = tuple(sorted(p.keys()))[:12]
        out.append({k: p.get(k) for k in keys if k in p})
    return out


def _aggregate_managed_report_from_legs(legs: list[dict[str, Any]]) -> dict[str, Any]:
    limitations: list[str] = []
    next_checks: list[str] = []
    outcome_summary = ""
    report_sections_present = False
    subagent_kinds = frozenset({"claim_verification", "corpus_explore", "research_plan"})
    for leg in legs:
        if leg.get("kind") not in subagent_kinds:
            continue
        mr = leg.get("managed_report")
        if not isinstance(mr, dict):
            text = str(leg.get("text_excerpt") or "")
            if text.strip():
                mr = parse_managed_report_from_text(text)
            else:
                continue
        if mr.get("report_sections_present"):
            report_sections_present = True
        short = str(mr.get("outcome_summary") or "").strip()
        if short:
            outcome_summary = short
        for item in list(mr.get("limitations") or []):
            s = str(item).strip()
            if s and s not in limitations:
                limitations.append(s)
        for item in list(mr.get("next_checks") or []):
            s = str(item).strip()
            if s and s not in next_checks:
                next_checks.append(s)
    return {
        "outcome_summary": outcome_summary,
        "limitations": limitations[:32],
        "next_checks": next_checks[:32],
        "report_sections_present": report_sections_present,
    }


def _compute_merge(legs: list[dict[str, Any]]) -> dict[str, Any]:
    if not legs:
        return _empty_merge_block()
    kinds = {str(x.get("kind") or "") for x in legs}
    has_parent = "parent_tool" in kinds
    has_cv = "claim_verification" in kinds
    has_child_leg = bool(kinds & {"claim_verification", "corpus_explore", "research_plan"})
    if has_parent and has_child_leg:
        origin = "mixed"
    elif has_cv:
        cv_ids = [
            str(x.get("subagent_id") or "") for x in legs if x.get("kind") == "claim_verification"
        ]
        origin = _evidence_origin_for_subagent_id(cv_ids[-1]) if cv_ids else "subagent:unknown"
    elif "corpus_explore" in kinds:
        sids = [str(x.get("subagent_id") or "") for x in legs if x.get("kind") == "corpus_explore"]
        origin = _evidence_origin_for_subagent_id(sids[-1]) if sids else "subagent:unknown"
    elif "research_plan" in kinds:
        sids = [str(x.get("subagent_id") or "") for x in legs if x.get("kind") == "research_plan"]
        origin = _evidence_origin_for_subagent_id(sids[-1]) if sids else "subagent:unknown"
    else:
        origin = "parent_tool"

    confidences = [_confidence_for_leg(x) for x in legs]
    confidence = min(confidences) if confidences else 1.0

    cv_verdicts: list[tuple[str, str]] = []
    for leg in legs:
        if leg.get("kind") != "claim_verification":
            continue
        sid = str(leg.get("subagent_id") or "")
        v = leg.get("verdict")
        if isinstance(v, str) and v.strip():
            cv_verdicts.append((sid, v.strip().upper()))

    conflict: dict[str, Any] | None = None
    if len(cv_verdicts) >= 2:
        uniq = {v for _, v in cv_verdicts}
        if len(uniq) > 1:
            conflict = {
                "type": "claim_verification_verdict_mismatch",
                "by_subagent": [{"subagent_id": s, "verdict": v} for s, v in cv_verdicts],
            }

    subagent_kinds = frozenset({"claim_verification", "corpus_explore", "research_plan"})
    partial_failure = any(
        str(x.get("terminal_state") or "") not in ("", "succeeded") or bool(x.get("failure_code"))
        for x in legs
        if x.get("kind") in subagent_kinds
    )

    writer_directive = _build_writer_directive(origin, conflict, partial_failure, legs)
    managed = _aggregate_managed_report_from_legs(legs)
    if not bool(managed.get("report_sections_present")):
        writer_directive = _enrich_writer_directive_with_managed_fields(
            writer_directive,
            limitations=list(managed.get("limitations") or []),
            next_checks=list(managed.get("next_checks") or []),
            outcome_summary=str(managed.get("outcome_summary") or ""),
        )

    completion_state = _infer_completion_state(legs, partial_failure=partial_failure)

    return {
        "evidence_origin": origin,
        "confidence": round(float(confidence), 4),
        "conflict": conflict,
        "writer_directive": writer_directive,
        "partial_failure": partial_failure,
        "completion_state": completion_state,
        "outcome_summary": managed.get("outcome_summary") or "",
        "limitations": list(managed.get("limitations") or []),
        "next_checks": list(managed.get("next_checks") or []),
        "report_sections_present": bool(managed.get("report_sections_present")),
    }


def _infer_completion_state(legs: list[dict[str, Any]], *, partial_failure: bool) -> str:
    """Heuristic completion_state derived from leg shapes.

    Specialists are expected to call ``annotate_completion_state`` for an
    explicit marker. This helper covers the implicit case so older legs do
    not break v3 readers.
    """
    if not legs:
        return "any_specialist_payload"
    for leg in legs:
        explicit = leg.get("completion_state")
        if isinstance(explicit, str) and explicit in COMPLETION_STATE_VALUES:
            return explicit
    if partial_failure:
        return "partial_failure_recoverable"
    return "any_specialist_payload"


def _enrich_writer_directive_with_managed_fields(
    directive: str,
    *,
    limitations: list[str],
    next_checks: list[str],
    outcome_summary: str,
) -> str:
    parts = [str(directive or "").strip()]
    if outcome_summary:
        parts.append(f"Subagent outcome (short): {outcome_summary[:400]}")
    if limitations:
        parts.append("Open limitations: " + "; ".join(limitations[:8]))
    if next_checks:
        parts.append("Next checks: " + "; ".join(next_checks[:8]))
    return "\n".join(p for p in parts if p).strip()


def _build_writer_directive(
    origin: str,
    conflict: dict[str, Any] | None,
    partial_failure: bool,
    legs: list[dict[str, Any]],
) -> str:
    parts: list[str] = []
    parts.append(
        "Evidence merge (v3): synthesize a single grounded answer. "
        f"evidence_origin={origin!r}. "
        "Do not hide tool denials, timeouts, or conflicting VERDICT lines; state them explicitly."
    )
    if conflict:
        parts.append(
            "CONFLICT: multiple claim_verification children disagree on VERDICT. "
            "Summarize each stance and recommend how the user should resolve ambiguity."
        )
    if partial_failure:
        _sub_kinds = frozenset({"claim_verification", "corpus_explore", "research_plan"})
        bad = [
            f"{x.get('subagent_id')}: {x.get('failure_code') or x.get('terminal_state')}"
            for x in legs
            if x.get("kind") in _sub_kinds
            and (
                str(x.get("terminal_state") or "") not in ("", "succeeded")
                or bool(x.get("failure_code"))
            )
        ]
        if bad:
            parts.append("PARTIAL_FAILURE legs: " + "; ".join(bad))
    return "\n".join(parts)


def serialize_for_writer(prev: dict[str, Any] | None, *, max_chars: int = 12000) -> str:
    """JSON excerpt of v3 for writer / supervisor context."""
    blob = prev if isinstance(prev, dict) else empty_specialist_results_v3()
    raw = json.dumps(blob, ensure_ascii=True, default=str)
    return raw[:max_chars]


__all__ = [
    "COMPLETION_STATE_VALUES",
    "append_writer_directive",
    "annotate_completion_state",
    "append_claim_verification_leg",
    "append_corpus_explore_leg",
    "append_parent_tool_leg",
    "append_research_plan_leg",
    "empty_specialist_results_v3",
    "parse_verdict_from_text",
    "prior_specialist_results_v3",
    "serialize_for_writer",
]
