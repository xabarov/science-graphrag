# Agent v3 quality — LLM calibration subset

Cases: mini_workspace_stats_01, mini_catalog_resolution_01, mini_dual_evidence_compare_01, mini_relation_tracing_01

Winner agreement rate (heuristic vs LLM): 0.5

## Per-case

- **mini_workspace_stats_01**: heuristic=tie llm=tie match=True
- **mini_catalog_resolution_01**: heuristic=tie llm=tie match=True
- **mini_dual_evidence_compare_01**: heuristic=candidate llm=baseline match=False
- **mini_relation_tracing_01**: heuristic=tie llm=baseline match=False

## Summary heuristic

```json
{
  "case_count": 4,
  "mean_weighted_score_baseline": 4.0,
  "mean_weighted_score_candidate": 4.0,
  "mean_delta": 0.0,
  "pairwise_candidate_win_rate": 0.25,
  "pairwise_baseline_win_rate": 0.0,
  "pairwise_tie_rate": 0.75,
  "hard_fail_count_baseline": 0,
  "hard_fail_count_candidate": 0,
  "family_breakdown": {
    "workspace_stats": {
      "candidate_wins": 0,
      "baseline_wins": 0,
      "ties": 1
    },
    "catalog_resolution": {
      "candidate_wins": 0,
      "baseline_wins": 0,
      "ties": 1
    },
    "dual_evidence_compare": {
      "candidate_wins": 1,
      "baseline_wins": 0,
      "ties": 0
    },
    "relation_tracing": {
      "candidate_wins": 0,
      "baseline_wins": 0,
      "ties": 1
    }
  },
  "all_passed": true,
  "branch_outcome_schema": "branch_outcome_v1",
  "cases_with_any_branch_non_ok": 0,
  "baseline_status_counts": {
    "ok": 4
  },
  "candidate_status_counts": {
    "ok": 4
  },
  "error_kind_counts": {},
  "baseline_timeout_cases": [],
  "candidate_timeout_cases": [],
  "baseline_error_cases": [],
  "candidate_error_cases": []
}
```

## Summary LLM judge

```json
{
  "case_count": 4,
  "mean_weighted_score_baseline": 5.3375,
  "mean_weighted_score_candidate": 4.1,
  "mean_delta": -1.2375,
  "pairwise_candidate_win_rate": 0.0,
  "pairwise_baseline_win_rate": 0.5,
  "pairwise_tie_rate": 0.5,
  "hard_fail_count_baseline": 0,
  "hard_fail_count_candidate": 1,
  "family_breakdown": {
    "workspace_stats": {
      "candidate_wins": 0,
      "baseline_wins": 0,
      "ties": 1
    },
    "catalog_resolution": {
      "candidate_wins": 0,
      "baseline_wins": 0,
      "ties": 1
    },
    "dual_evidence_compare": {
      "candidate_wins": 0,
      "baseline_wins": 1,
      "ties": 0
    },
    "relation_tracing": {
      "candidate_wins": 0,
      "baseline_wins": 1,
      "ties": 0
    }
  },
  "all_passed": false,
  "branch_outcome_schema": "branch_outcome_v1",
  "cases_with_any_branch_non_ok": 0,
  "baseline_status_counts": {
    "ok": 4
  },
  "candidate_status_counts": {
    "ok": 4
  },
  "error_kind_counts": {},
  "baseline_timeout_cases": [],
  "candidate_timeout_cases": [],
  "baseline_error_cases": [],
  "candidate_error_cases": []
}
```
