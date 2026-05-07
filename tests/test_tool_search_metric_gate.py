"""LLM / hybrid ``tool_search`` prep — measurement contract (roadmap §6 p.2 / §6.4).

Before enabling LLM shortlist selection, record from production-like runs:

- ``shortlist_ratio_avg`` — average of per-turn ``tool_search_result`` shortlist ratios
  (trace-review-v1 already rolls this into ``Metrics.shortlist_ratio_avg``).
- ``deferred_schema_event_count`` — counter when
  ``agent_tool_search_deferred_schema_refs_enabled`` is on (SSE ``run_metadata`` +
  trace-review merge).
- ``latency_p95_ms`` — from ``science-graphrag-agent-benchmark`` suite summaries for
  A/B toggles (off vs on deferred schemas).
- ``unnecessary_tool_calls`` — benchmark-side: ``eval/agent_tools/metrics.score_agent_case``
  (executed trace length minus expected tool count; see ``tests/eval/test_agent_tools_metrics.py``).

No runtime assertions here; implementation hooks live in ``scripts/live_check/trace_review_schema.py``
and ``science_graphrag/agent/tool_search.py``.
"""

from __future__ import annotations


def test_tool_search_prep_metric_keys_documented() -> None:
    expected_keys = (
        "shortlist_ratio_avg",
        "deferred_schema_event_count",
        "latency_p95_ms",
        "tool_call_count_vs_budget",
        "unnecessary_tool_calls",
        "tool_schema_bytes_saved",
        "tool_search_miss_due_to_no_discovery",
        "deferred_tool_activation_rate",
    )
    assert len(expected_keys) == 8
