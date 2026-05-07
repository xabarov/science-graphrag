"""Offline long-thread eval harness (Epic A3)."""

from __future__ import annotations

from eval.chat_agent.long_thread_eval import run_offline_long_thread_metrics


def test_long_thread_offline_all_pass() -> None:
    out = run_offline_long_thread_metrics()
    assert out["metrics"]["insight_recall_at_k"] == 1.0
    assert out["metrics"]["stale_summary_error_rate"] == 0.0
    assert out["metrics"]["long_thread_eval_pass_rate"] == 1.0
    assert out["metrics"]["claim_grounding_precision"] == 1.0
    assert out["metrics"]["claim_grounding_recall"] == 1.0
    assert out["metrics"]["insight_synthesis_conflict_audit_rate"] == round(1 / 3, 6)
    assert len(out["cases"]) == 3
    assert all(c["pass"] for c in out["cases"])
    assert all(c["claim_grounding_ok"] for c in out["cases"])
