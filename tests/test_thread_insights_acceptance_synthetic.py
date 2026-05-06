"""Synthetic acceptance proxies for A1 metrics (insight_recall@k, stale_summary_error_rate).

Full A3 eval lane remains separate; these tests lock deterministic behavior + baselines.
"""

from __future__ import annotations

from science_graphrag.agent.context.session_backend import get_session_memory_backend
from science_graphrag.agent.context.session_store import clear_session_store_for_tests
from science_graphrag.agent.context.thread_insights import (
    build_thread_insight_snapshot,
    maybe_refresh_thread_insight_after_turn,
)
from science_graphrag.config import Settings


def _insight_recall_at_k(insight_text: str, keywords: list[str], k: int) -> float:
    """Proxy: fraction of first ``k`` keywords found as substrings (case-sensitive)."""
    if k <= 0:
        return 0.0
    take = keywords[:k]
    hits = sum(1 for kw in take if kw in insight_text)
    return hits / float(len(take))


def test_insight_recall_at_k_synthetic_baseline() -> None:
    """Planted intents must surface in deterministic stub chunk lines."""
    digests = [
        {
            "user_intent": "alpha_unique_kw",
            "answer_excerpt": "a0",
            "answer_class": "inventory",
            "tools_used": [],
        },
        {
            "user_intent": "beta_unique_kw",
            "answer_excerpt": "a1",
            "answer_class": "fact_lookup",
            "tools_used": [],
        },
    ]
    st = Settings(
        agent_thread_insights_min_digests=2,
        agent_thread_insights_max_chunks=2,
        agent_thread_insights_max_workers=2,
    )
    snap = build_thread_insight_snapshot(
        digests,
        settings=st,
        prev_version=0,
        turn_counter=2,
        stale_reason="turn_delta",
    )
    assert snap is not None
    body = str(snap.get("current") or "")
    recall = _insight_recall_at_k(body, ["alpha_unique_kw", "beta_unique_kw"], k=2)
    assert recall >= 1.0


def test_stale_summary_error_rate_proxy_no_false_stale_when_fresh() -> None:
    """When policy says skip_fresh, we must not bump version (stale mis-label proxy)."""
    clear_session_store_for_tests()
    st = Settings(
        agent_thread_insights_enabled=True,
        agent_thread_insights_min_digests=2,
        agent_thread_insights_stale_after_turn_delta=50,
    )
    be = get_session_memory_backend()
    be.update_after_turn(
        "tid-s",
        turn_digest={"user_intent": "u0", "answer_excerpt": "a0", "tools_used": []},
    )
    be.update_after_turn(
        "tid-s",
        turn_digest={"user_intent": "u1", "answer_excerpt": "a1", "tools_used": []},
    )
    maybe_refresh_thread_insight_after_turn("tid-s", settings=st)
    be.update_after_turn(
        "tid-s",
        turn_digest={"user_intent": "u2", "answer_excerpt": "a2", "tools_used": []},
    )
    maybe_refresh_thread_insight_after_turn("tid-s", settings=st)
    tip = (be.get_session_copy("tid-s").get("session_meta") or {}).get("thread_insight")
    assert tip.get("version") == 1
    ctrl = (be.get_session_copy("tid-s").get("session_meta") or {}).get("thread_insight_control")
    assert ctrl.get("refresh_decision") == "skip_fresh"
    # "error rate" proxy: no incorrect stale_reason on the last retained snapshot
    assert tip.get("audit", {}).get("stale_reason") in (None, "turn_delta", "manual")
