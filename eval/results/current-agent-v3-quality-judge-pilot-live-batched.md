# Agent v3 quality judge — judge_pilot live batched

Cases: 10

```json
{
  "case_count": 10,
  "mean_weighted_score_baseline": 3.6,
  "mean_weighted_score_candidate": 3.8,
  "mean_delta": 0.2,
  "pairwise_candidate_win_rate": 0.5,
  "pairwise_baseline_win_rate": 0.2,
  "pairwise_tie_rate": 0.3,
  "hard_fail_count_baseline": 2,
  "hard_fail_count_candidate": 1,
  "family_breakdown": {
    "catalog_resolution": {
      "candidate_wins": 1,
      "baseline_wins": 0,
      "ties": 1
    },
    "dual_evidence_compare": {
      "candidate_wins": 1,
      "baseline_wins": 1,
      "ties": 0
    },
    "open_research": {
      "candidate_wins": 1,
      "baseline_wins": 0,
      "ties": 0
    },
    "quote_evidence": {
      "candidate_wins": 0,
      "baseline_wins": 0,
      "ties": 1
    },
    "relation_tracing": {
      "candidate_wins": 0,
      "baseline_wins": 1,
      "ties": 1
    },
    "workspace_stats": {
      "candidate_wins": 2,
      "baseline_wins": 0,
      "ties": 0
    }
  },
  "all_passed": false,
  "latency_candidate_minus_baseline_ms_avg": 7416.14,
  "latency_candidate_minus_baseline_ms_max": 27140.0,
  "execution_error_case_count": 3,
  "execution_error_cases": [
    "mini_catalog_resolution_02",
    "mini_dual_evidence_compare_01",
    "mini_open_research_01"
  ]
}
```

## mini_catalog_resolution_01 — PASS

winner=tie confidence=low
baseline_ms=32377 candidate_ms=50410

## mini_catalog_resolution_02 — FAIL

winner=candidate confidence=low
baseline_ms=None candidate_ms=19429
execution_error=subprocess_timeout_after_120.0s: Command '['/home/roman/pyprojects/ML/Prod/science-graphrag/.venv/bin/python', '-m', 'eval.agent_v3_quality.one_shot', 'langgraph_research_v1', '/tmp/tmptcexla_0.json']' timed out after 120.0 seconds

## mini_dual_evidence_compare_01 — FAIL

winner=baseline confidence=low
baseline_ms=54890 candidate_ms=None
execution_error=subprocess_timeout_after_120.0s: Command '['/home/roman/pyprojects/ML/Prod/science-graphrag/.venv/bin/python', '-m', 'eval.agent_v3_quality.one_shot', 'langgraph_supervisor_v3', '/tmp/tmpwzrtip6g.json']' timed out after 120.0 seconds

## mini_open_research_01 — FAIL

winner=candidate confidence=low
baseline_ms=None candidate_ms=37309
execution_error=subprocess_timeout_after_120.0s: Command '['/home/roman/pyprojects/ML/Prod/science-graphrag/.venv/bin/python', '-m', 'eval.agent_v3_quality.one_shot', 'langgraph_research_v1', '/tmp/tmp7e1i9yz7.json']' timed out after 120.0 seconds

## mini_quote_evidence_01 — PASS

winner=tie confidence=low
baseline_ms=19230 candidate_ms=19372

## mini_relation_tracing_01 — PASS

winner=baseline confidence=low
baseline_ms=11728 candidate_ms=11982

## mini_workspace_stats_01 — PASS

winner=candidate confidence=low
baseline_ms=9478 candidate_ms=12461

## mini_workspace_stats_02 — PASS

winner=candidate confidence=low
baseline_ms=10695 candidate_ms=13798

## pilot_catalog_extra_01 — PASS

winner=candidate confidence=low
baseline_ms=43819 candidate_ms=70959

## pilot_relation_extra_01 — PASS

winner=tie confidence=low
baseline_ms=24086 candidate_ms=24344
