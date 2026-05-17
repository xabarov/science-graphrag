"""Unit tests for final-answer validation (smolagents Phase 2)."""

from __future__ import annotations

from science_graphrag.agent.evidence_trust import MODE_METADATA_ONLY
from science_graphrag.agent.final_answer_validation import (
    REASON_EMPTY_ANSWER,
    REASON_FAILED_FETCH_WITHOUT_LIMITATION,
    REASON_GENERIC_FALLBACK_WITH_EVIDENCE,
    REASON_METADATA_ONLY_WITHOUT_LIMITATION,
    REASON_PARTIAL_ANSWER_OK,
    REASON_PDF_UNAVAILABLE_WITHOUT_LIMITATION,
    build_final_answer_validation_debug_event,
    evidence_present,
    is_generic_fallback_answer,
    maybe_append_final_answer_validation_event,
    validate_final_answer,
)
from science_graphrag.agent.runtime_answer_salvage import RUNTIME_FALLBACK_ANSWER


def test_is_generic_fallback_answer() -> None:
    assert is_generic_fallback_answer(RUNTIME_FALLBACK_ANSWER)
    assert not is_generic_fallback_answer("Grounded summary with citations.")


def test_validate_ok_complete_answer() -> None:
    verdict = validate_final_answer(
        answer="SAM 3 uses a promptable segmentation head.",
        citations=[{"url": "https://example.org", "evidence_mode": "web_summary"}],
    )
    assert verdict["status"] == "ok"
    assert verdict["answer_kind"] == "complete"
    assert verdict["user_visible_answer_allowed"] is True


def test_validate_generic_fallback_with_evidence() -> None:
    verdict = validate_final_answer(
        answer=RUNTIME_FALLBACK_ANSWER,
        citations=[{"work_id": "w1"}],
    )
    assert verdict["status"] == "fail"
    assert REASON_GENERIC_FALLBACK_WITH_EVIDENCE in verdict["reasons"]
    assert verdict["evidence_present"] is True
    assert verdict["user_visible_answer_allowed"] is False


def test_validate_empty_answer() -> None:
    verdict = validate_final_answer(answer="", citations=[])
    assert verdict["status"] == "fail"
    assert REASON_EMPTY_ANSWER in verdict["reasons"]
    assert verdict["answer_kind"] == "empty"


def test_validate_metadata_only_without_limitation() -> None:
    verdict = validate_final_answer(
        answer="This paper improves detection accuracy.",
        citations=[{"evidence_mode": MODE_METADATA_ONLY, "title": "Paper A"}],
    )
    assert verdict["status"] == "warn"
    assert REASON_METADATA_ONLY_WITHOUT_LIMITATION in verdict["reasons"]


def test_validate_partial_answer_with_limitation() -> None:
    verdict = validate_final_answer(
        answer="Partial synthesis with explicit limitations on PDF access.",
        citations=[{"work_id": "w1"}],
        specialist_results_v3={
            "merge": {"completion_state": "partial", "writer_directive": "pdf_unavailable"}
        },
    )
    assert verdict["answer_kind"] == "partial"
    assert REASON_PARTIAL_ANSWER_OK in verdict["reasons"]
    assert verdict["user_visible_answer_allowed"] is True


def test_validate_failed_fetch_requires_limitation_language() -> None:
    verdict = validate_final_answer(
        answer="Claims based on fetched page content.",
        citations=[],
        specialist_results_v3={
            "merge": {"writer_directive": "web_fetch failed for primary source."}
        },
    )
    assert REASON_FAILED_FETCH_WITHOUT_LIMITATION in verdict["reasons"]
    assert verdict["status"] == "warn"


def test_validate_partial_without_limitation_is_warn() -> None:
    verdict = validate_final_answer(
        answer="Short interim summary from collected sources only.",
        citations=[{"work_id": "w1"}],
        specialist_results_v3={"merge": {"completion_state": "partial"}},
    )
    assert verdict["answer_kind"] == "partial"
    assert verdict["status"] == "warn"
    assert REASON_PARTIAL_ANSWER_OK in verdict["reasons"]
    assert verdict["user_visible_answer_allowed"] is True


def test_validate_pdf_unavailable_requires_limitation_language() -> None:
    verdict = validate_final_answer(
        answer="Strong claims about full-text findings.",
        citations=[],
        specialist_results_v3={
            "merge": {"writer_directive": "PDF unavailable for safe OA candidate."}
        },
    )
    assert REASON_PDF_UNAVAILABLE_WITHOUT_LIMITATION in verdict["reasons"]


def test_typed_merge_limitations_count_as_limitation_present() -> None:
    verdict = validate_final_answer(
        answer="Answer without limitation keywords in prose.",
        citations=[{"work_id": "w1", "evidence_mode": "metadata_only"}],
        specialist_results_v3={
            "merge": {
                "limitations": ["metadata_only sources only"],
                "completion_state": "partial",
            }
        },
    )
    assert verdict["limitation_present"] is True
    assert verdict["status"] in {"ok", "warn"}


def test_evidence_present_from_specialist_results_v3() -> None:
    assert evidence_present(
        citations=[],
        specialist_results_v3={"legs": [{"subagent_id": "retrieval_agent"}]},
    )


def test_maybe_append_replace_existing_refreshes_verdict() -> None:
    events: list[dict] = [
        {
            "type": "final_answer_validation",
            "verdict": {"status": "fail", "reasons": ["generic_fallback_with_evidence"]},
        }
    ]
    verdict = maybe_append_final_answer_validation_event(
        events,
        answer="Grounded answer with explicit limitations on metadata-only sources.",
        citations=[{"evidence_mode": "web_summary", "url": "https://example.org"}],
        replace_existing=True,
    )
    assert len(events) == 1
    assert verdict["status"] in {"ok", "warn"}
    assert events[0]["verdict"]["status"] == verdict["status"]


def test_synthesized_partial_answer_classifies_as_partial() -> None:
    from science_graphrag.agent.runtime_answer_salvage import (
        synthesize_partial_answer_from_specialist_context,
    )

    partial = synthesize_partial_answer_from_specialist_context(
        citations=[{"url": "https://example.org"}],
        specialist_results_v3={"merge": {"writer_directive": "pdf unavailable"}},
        language="en",
    )
    verdict = validate_final_answer(
        answer=partial,
        citations=[{"url": "https://example.org"}],
        specialist_results_v3={"merge": {"writer_directive": "pdf unavailable"}},
    )
    assert verdict["answer_kind"] == "partial"
    assert verdict["user_visible_answer_allowed"] is True


def test_maybe_append_final_answer_validation_event_dedupes() -> None:
    events: list[dict] = []
    v1 = maybe_append_final_answer_validation_event(
        events, answer="ok", citations=[{"url": "https://a.example"}]
    )
    assert len(events) == 1
    assert events[0]["type"] == "final_answer_validation"
    v2 = maybe_append_final_answer_validation_event(
        events, answer="ok", citations=[{"url": "https://a.example"}]
    )
    assert len(events) == 1
    assert v2 == v1


def test_build_final_answer_validation_debug_event_shape() -> None:
    verdict = validate_final_answer(answer="x", citations=[])
    ev = build_final_answer_validation_debug_event(verdict)
    assert ev["type"] == "final_answer_validation"
    assert ev["verdict"]["status"] in {"ok", "warn", "fail"}
