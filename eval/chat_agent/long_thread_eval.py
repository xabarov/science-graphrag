"""Offline long-thread prompt-memory eval (Epic A3).

Deterministic checks on ``resolve_prompt_memory_policy`` + ``format_user_with_memory``
without live HTTP. Emits metrics merged into ``trace-review-v1`` by ``agent_trace_review``.
"""

from __future__ import annotations

from typing import Any

from science_graphrag.agent.context.prompt_memory_policy import resolve_prompt_memory_policy
from science_graphrag.agent.context.session_store import format_user_with_memory
from science_graphrag.config import Settings


def _scenario_fresh_insight_with_digest() -> dict[str, Any]:
    """Insight built at same turn_counter as digests; expect injection + last digest block."""
    return {
        "digests": [
            {
                "user_intent": "Find papers on topic alpha",
                "answer_excerpt": "Found two works.",
                "answer_class": "inventory",
                "tools_used": ["find_works"],
            },
            {
                "user_intent": "Summarize contradictions",
                "answer_excerpt": "Paper A disagrees with B.",
                "answer_class": "synthesis",
                "tools_used": [],
            },
        ],
        "session_summary": (
            "Q: Find papers on topic alpha\nA: Found two works.\n---\n"
            "Q: Summarize contradictions\nA: Paper A disagrees with B."
        ),
        "session_meta": {
            "turn_counter": 2,
            "thread_insight": {
                "current": "## thread_insight\nCovers topic alpha and contradiction between A/B.",
                "version": 1,
                "audit": {
                    "schema_version": "thread_insight_audit_v1",
                    "built_at_turn_counter": 2,
                    "chunk_count": 1,
                },
            },
            "thread_insight_control": {
                "schema_version": "thread_insight_control_v1",
                "refresh_decision": "skip_fresh",
                "last_turn": 2,
            },
            "insight_circuit": {"consecutive_failures": 0, "open_until_turn": 0},
        },
    }


def _scenario_stale_lag() -> dict[str, Any]:
    """Insight one turn behind digest window -> fallback, no insight in prompt."""
    return {
        "digests": [
            {
                "user_intent": "q1",
                "answer_excerpt": "a1",
                "answer_class": "x",
                "tools_used": [],
            },
            {
                "user_intent": "q2 latest intent marker",
                "answer_excerpt": "a2",
                "answer_class": "x",
                "tools_used": [],
            },
        ],
        "session_summary": "rolling",
        "session_meta": {
            "turn_counter": 2,
            "thread_insight": {
                "current": "old insight missing q2 latest intent marker",
                "version": 1,
                "audit": {
                    "schema_version": "thread_insight_audit_v1",
                    "built_at_turn_counter": 1,
                },
            },
            "insight_circuit": {"consecutive_failures": 0, "open_until_turn": 0},
        },
    }


def _scenario_conflict() -> dict[str, Any]:
    """Fresh insight but text omits latest digest intent -> conflicted status."""
    return {
        "digests": [
            {
                "user_intent": "first",
                "answer_excerpt": "x",
                "answer_class": "x",
                "tools_used": [],
            },
            {
                "user_intent": "uniquemarkerxyzforconflict",
                "answer_excerpt": "y",
                "answer_class": "x",
                "tools_used": [],
            },
        ],
        "session_summary": "Q: first\nA: x\n---\nQ: uniquemarkerxyzforconflict\nA: y",
        "session_meta": {
            "turn_counter": 2,
            "thread_insight": {
                "current": "## thread_insight\nOnly discusses first turn, no uniquemarker.",
                "version": 2,
                "audit": {
                    "schema_version": "thread_insight_audit_v1",
                    "built_at_turn_counter": 2,
                },
            },
            "insight_circuit": {"consecutive_failures": 0, "open_until_turn": 0},
        },
    }


def _evaluate_case(
    *,
    case_id: str,
    ent: dict[str, Any],
    must_contain: list[str],
    must_not: list[str],
    settings: Settings,
) -> tuple[dict[str, Any], bool, bool, bool]:
    pm = resolve_prompt_memory_policy(session_ent=ent, settings=settings)
    user_blob = format_user_with_memory(
        question="Follow-up question",
        session_summary=pm.session_memory_text,
        history_digest=[],
        last_turn_digest_text=pm.last_turn_digest_text,
        thread_insight_text=pm.thread_insight_text,
        thread_insight_status=pm.thread_insight_status,
    )
    ok = all(x in user_blob for x in must_contain) and all(ns not in user_blob for ns in must_not)
    claim_grounding_ok = bool(
        ok and ("<last_turn_digest" in user_blob or "<thread_insight" in user_blob)
    )
    if case_id == "long_thread_stale_fallback":
        ok = ok and pm.insight_fallback_reason == "insight_stale_lag"
        claim_grounding_ok = bool(
            claim_grounding_ok and pm.insight_fallback_reason == "insight_stale_lag"
        )

    case_out = {
        "case_id": case_id,
        "pass": ok,
        "claim_grounding_ok": claim_grounding_ok,
        "insight_fallback_reason": pm.insight_fallback_reason,
        "thread_insight_prompt_status": pm.run_metadata_fragment().get(
            "thread_insight_prompt_status"
        ),
    }
    stale_error = bool(case_id == "long_thread_stale_fallback" and pm.thread_insight_text)
    return case_out, ok, claim_grounding_ok, stale_error


# pylint: disable-next=too-many-locals
def run_offline_long_thread_metrics(
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Return ``{ "cases": [...], "metrics": {...} }`` for trace-review merge."""
    st2 = settings or Settings(
        agent_thread_insights_enabled=True, agent_thread_insights_min_digests=1
    )

    cases_out: list[dict[str, Any]] = []
    recall_hits = 0
    recall_total = 0
    stale_errors = 0
    grounding_hits = 0
    grounding_total = 0

    scenarios: list[tuple[str, dict[str, Any], list[str], list[str]]] = [
        (
            "long_thread_fresh_insight",
            _scenario_fresh_insight_with_digest(),
            ["<thread_insight", "<last_turn_digest", "topic alpha"],
            [],
        ),
        (
            "long_thread_stale_fallback",
            _scenario_stale_lag(),
            ["<last_turn_digest", "q2 latest intent marker", "<session_memory>"],
            ["<thread_insight"],
        ),
        (
            "long_thread_conflict_marked",
            _scenario_conflict(),
            ['status="conflicted"', "uniquemarkerxyzforconflict"],
            [],
        ),
    ]

    for case_id, ent, must_contain, must_not in scenarios:
        case_out, ok, claim_grounding_ok, stale_error = _evaluate_case(
            case_id=case_id,
            ent=ent,
            must_contain=must_contain,
            must_not=must_not,
            settings=st2,
        )
        cases_out.append(case_out)
        recall_total += 1
        if ok:
            recall_hits += 1
        grounding_total += 1
        if claim_grounding_ok:
            grounding_hits += 1
        if stale_error:
            stale_errors += 1

    n = float(recall_total or 1)
    g = float(grounding_total or 1)
    metrics = {
        "insight_recall_at_k": round(recall_hits / n, 6),
        "stale_summary_error_rate": round(stale_errors / n, 6),
        "long_thread_eval_pass_rate": round(recall_hits / n, 6),
        "claim_grounding_precision": round(grounding_hits / g, 6),
        "claim_grounding_recall": round(grounding_hits / g, 6),
    }
    return {"cases": cases_out, "metrics": metrics}
