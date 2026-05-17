"""Structured final-answer validation (smolagents ``final_answer_checks`` analogue).

Phase 2 ships diagnostics-only: verdicts are emitted in ``debug_events`` and
``run_metadata.final_answer_validation``. Enforcement is gated by
``Settings.agent_final_answer_validation_enforcement_enabled`` (default off).
"""

from __future__ import annotations

import re
from typing import Any, Literal

from science_graphrag.agent.evidence_trust import MODE_METADATA_ONLY
from science_graphrag.agent.runtime_answer_salvage import RUNTIME_FALLBACK_ANSWER
from science_graphrag.agent.subagent_output_contract import merge_limitation_signals

ValidationStatus = Literal["ok", "warn", "fail"]
EnforcementMode = Literal["diagnostic", "enforced"]
AnswerKind = Literal["complete", "partial", "fallback", "empty"]

# Operator gates before flipping ``agent_final_answer_validation_enforcement_enabled``.
ENFORCEMENT_READINESS_GATES: tuple[str, ...] = (
    "generic_fallback_with_evidence_cases == 0 on external CV matrix",
    "final_answer_validation present on all matrix cases",
    "no false reject on accepted partial_final_answer / budget_exhausted_with_partial",
)

REASON_EMPTY_ANSWER = "empty_answer"
REASON_GENERIC_FALLBACK_WITH_EVIDENCE = "generic_fallback_with_evidence"
REASON_METADATA_ONLY_WITHOUT_LIMITATION = "metadata_only_without_limitation"
REASON_PDF_UNAVAILABLE_WITHOUT_LIMITATION = "pdf_unavailable_without_limitation"
REASON_FAILED_FETCH_WITHOUT_LIMITATION = "failed_fetch_without_limitation"
REASON_PARTIAL_ANSWER_OK = "partial_answer_ok"
REASON_ANSWER_OK = "answer_ok"

_LIMITATION_MARKERS = (
    "limitation",
    "limitations",
    "ограничен",
    "ограничения",
    "metadata only",
    "metadata-only",
    "только метадан",
    "abstract only",
    "pdf_unavailable",
    "pdf unavailable",
    "не удалось прочитать pdf",
    "could not read pdf",
    "fetch failed",
    "partial",
    "промежуточ",
    "completion_state",
)

_PDF_UNAVAILABLE_MARKERS = (
    "pdf_unavailable",
    "pdf unavailable",
    "no safe pdf",
    "could not read pdf",
    "не удалось прочитать pdf",
    "oa pdf",
)

_FETCH_FAILURE_MARKERS = (
    "fetch failed",
    "web_fetch failed",
    "web_fetch_failure",
    "source_unreachable",
    "host_not_allowed",
)


def is_generic_fallback_answer(text: str) -> bool:
    """True for runtime/writer generic terminal fallback copy."""
    s = str(text or "").strip().lower()
    if not s:
        return False
    fallback = RUNTIME_FALLBACK_ANSWER.strip().lower()
    if s.startswith(fallback):
        return True
    return s.startswith("i could not produce a complete final answer for this turn")


def _answer_has_limitation_language(text: str) -> bool:
    lowered = str(text or "").lower()
    return any(m in lowered for m in _LIMITATION_MARKERS)


def _merge_has_typed_limitations(merge: dict[str, Any]) -> bool:
    lims, nxt = merge_limitation_signals(merge)
    return bool(lims or nxt)


def _limitation_present(*, answer: str, merge: dict[str, Any]) -> bool:
    return _answer_has_limitation_language(answer) or _merge_has_typed_limitations(merge)


def _merge_block(specialist_results_v3: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(specialist_results_v3, dict):
        return {}
    merge = specialist_results_v3.get("merge")
    return merge if isinstance(merge, dict) else {}


def evidence_present(
    *,
    citations: list[dict[str, Any]] | None,
    specialist_results_v3: dict[str, Any] | None = None,
    specialist_results: dict[str, Any] | None = None,
    tool_trace_count: int | None = None,
) -> bool:
    """Whether grounded material exists beyond an empty coordinator-only turn."""
    cits = [c for c in list(citations or []) if isinstance(c, dict)]
    if cits:
        return True
    sr3 = specialist_results_v3 if isinstance(specialist_results_v3, dict) else {}
    legs = sr3.get("legs")
    if isinstance(legs, list) and legs:
        return True
    merge = _merge_block(sr3)
    if str(merge.get("writer_directive") or "").strip():
        return True
    if str(merge.get("outcome_summary") or "").strip():
        return True
    if _merge_has_typed_limitations(merge):
        return True
    sr = specialist_results if isinstance(specialist_results, dict) else {}
    if sr:
        return True
    if tool_trace_count is not None and int(tool_trace_count) > 1:
        return True
    return False


def _citations_metadata_only(citations: list[dict[str, Any]]) -> bool:
    if not citations:
        return False
    modes: list[str] = []
    for c in citations:
        mode = str(c.get("evidence_mode") or "").strip()
        if mode:
            modes.append(mode)
    if not modes:
        return False
    return all(m == MODE_METADATA_ONLY for m in modes)


def _context_requires_pdf_limitation(
    *,
    citations: list[dict[str, Any]],
    merge: dict[str, Any],
) -> bool:
    directive = str(merge.get("writer_directive") or "").lower()
    lims, _ = merge_limitation_signals(merge)
    combined = directive + " " + " ".join(lims).lower()
    if any(m in combined for m in _PDF_UNAVAILABLE_MARKERS):
        return True
    for c in citations:
        fb = str(c.get("fallback_reason") or c.get("trust_fallback_reason") or "").lower()
        if "pdf_unavailable" in fb or "pdf_parse" in fb or "pdf_too_large" in fb:
            return True
    return False


def _context_requires_fetch_limitation(*, merge: dict[str, Any]) -> bool:
    directive = str(merge.get("writer_directive") or "").lower()
    lims, _ = merge_limitation_signals(merge)
    combined = directive + " " + " ".join(lims).lower()
    return any(m in combined for m in _FETCH_FAILURE_MARKERS)


def classify_answer_kind(
    *,
    answer: str,
    merge: dict[str, Any] | None = None,
) -> AnswerKind:
    text = str(answer or "").strip()
    if not text:
        return "empty"
    if is_generic_fallback_answer(text):
        return "fallback"
    merge = merge or {}
    completion = str(merge.get("completion_state") or "").strip().lower()
    if completion in {"partial", "partial_failure"} or merge.get("partial_failure"):
        return "partial"
    if re.search(r"(?i)\bpartial\b", text) or "промежуточ" in text.lower():
        return "partial"
    if "не удалось автоматически завершить" in text.lower():
        return "partial"
    if text.lower().startswith("the run did not finish a complete final synthesis"):
        return "partial"
    return "complete"


def validate_final_answer(
    *,
    answer: str,
    citations: list[dict[str, Any]] | None = None,
    specialist_results_v3: dict[str, Any] | None = None,
    specialist_results: dict[str, Any] | None = None,
    tool_trace_count: int | None = None,
    enforcement_mode: EnforcementMode = "diagnostic",
) -> dict[str, Any]:
    """Return a structured validation verdict for a terminal answer payload."""
    cits = [c for c in list(citations or []) if isinstance(c, dict)]
    merge = _merge_block(specialist_results_v3)
    ev_present = evidence_present(
        citations=cits,
        specialist_results_v3=specialist_results_v3,
        specialist_results=specialist_results,
        tool_trace_count=tool_trace_count,
    )
    answer_kind = classify_answer_kind(answer=answer, merge=merge)
    reasons: list[str] = []
    status: ValidationStatus = "ok"

    if answer_kind == "empty":
        reasons.append(REASON_EMPTY_ANSWER)
        status = "fail"
    elif answer_kind == "fallback" and ev_present:
        reasons.append(REASON_GENERIC_FALLBACK_WITH_EVIDENCE)
        status = "fail"
    elif answer_kind == "partial":
        reasons.append(REASON_PARTIAL_ANSWER_OK)
        status = "warn" if not _limitation_present(answer=answer, merge=merge) else "ok"
    else:
        if _citations_metadata_only(cits) and not _limitation_present(answer=answer, merge=merge):
            reasons.append(REASON_METADATA_ONLY_WITHOUT_LIMITATION)
            status = "warn"
        if _context_requires_pdf_limitation(citations=cits, merge=merge) and not (
            any(m in str(answer or "").lower() for m in _PDF_UNAVAILABLE_MARKERS)
            or _limitation_present(answer=answer, merge=merge)
        ):
            if REASON_PDF_UNAVAILABLE_WITHOUT_LIMITATION not in reasons:
                reasons.append(REASON_PDF_UNAVAILABLE_WITHOUT_LIMITATION)
            status = "warn" if status == "ok" else status
        if _context_requires_fetch_limitation(merge=merge) and not _limitation_present(
            answer=answer, merge=merge
        ):
            if REASON_FAILED_FETCH_WITHOUT_LIMITATION not in reasons:
                reasons.append(REASON_FAILED_FETCH_WITHOUT_LIMITATION)
            status = "warn" if status == "ok" else status
        if not reasons:
            reasons.append(REASON_ANSWER_OK)

    user_allowed = answer_kind != "empty" and not (
        answer_kind == "fallback" and ev_present and status == "fail"
    )
    if answer_kind == "partial":
        user_allowed = True

    return {
        "status": status,
        "reasons": reasons,
        "terminal_reason": None,
        "evidence_present": ev_present,
        "citations_present": bool(cits),
        "citation_count": len(cits),
        "answer_kind": answer_kind,
        "limitation_required": bool(
            _citations_metadata_only(cits)
            or _context_requires_pdf_limitation(citations=cits, merge=merge)
            or _context_requires_fetch_limitation(merge=merge)
        ),
        "limitation_present": _limitation_present(answer=answer, merge=merge),
        "user_visible_answer_allowed": user_allowed,
        "enforcement_mode": enforcement_mode,
    }


def build_final_answer_validation_debug_event(verdict: dict[str, Any]) -> dict[str, Any]:
    """Debug event row consumed by ``extract_runtime_telemetry_from_debug_events``."""
    return {"type": "final_answer_validation", "verdict": dict(verdict)}


def maybe_append_final_answer_validation_event(
    debug_events: list[dict[str, Any]],
    *,
    answer: str,
    citations: list[dict[str, Any]] | None,
    specialist_results_v3: dict[str, Any] | None = None,
    specialist_results: dict[str, Any] | None = None,
    tool_trace_count: int | None = None,
    enforcement_mode: EnforcementMode = "diagnostic",
    replace_existing: bool = False,
) -> dict[str, Any]:
    """Append validation debug event; optionally replace prior rows of the same type."""
    if replace_existing:
        debug_events[:] = [
            ev
            for ev in debug_events
            if not (isinstance(ev, dict) and ev.get("type") == "final_answer_validation")
        ]
    else:
        for ev in reversed(debug_events[-8:]):
            if isinstance(ev, dict) and ev.get("type") == "final_answer_validation":
                return ev.get("verdict") if isinstance(ev.get("verdict"), dict) else {}
    verdict = validate_final_answer(
        answer=answer,
        citations=citations,
        specialist_results_v3=specialist_results_v3,
        specialist_results=specialist_results,
        tool_trace_count=tool_trace_count,
        enforcement_mode=enforcement_mode,
    )
    debug_events.append(build_final_answer_validation_debug_event(verdict))
    return verdict


__all__ = [
    "REASON_ANSWER_OK",
    "REASON_EMPTY_ANSWER",
    "REASON_GENERIC_FALLBACK_WITH_EVIDENCE",
    "REASON_METADATA_ONLY_WITHOUT_LIMITATION",
    "REASON_PARTIAL_ANSWER_OK",
    "REASON_PDF_UNAVAILABLE_WITHOUT_LIMITATION",
    "REASON_FAILED_FETCH_WITHOUT_LIMITATION",
    "AnswerKind",
    "EnforcementMode",
    "ValidationStatus",
    "build_final_answer_validation_debug_event",
    "classify_answer_kind",
    "evidence_present",
    "is_generic_fallback_answer",
    "maybe_append_final_answer_validation_event",
    "validate_final_answer",
]
