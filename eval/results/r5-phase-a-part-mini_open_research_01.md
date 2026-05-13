# Agent v3 quality judge — judge_pilot

Cases: 1  seeds: 1

```json
{
  "case_count": 1,
  "mean_weighted_score_baseline": 4.0,
  "mean_weighted_score_candidate": 4.0,
  "mean_delta": 0.0,
  "pairwise_candidate_win_rate": 0.0,
  "pairwise_baseline_win_rate": 0.0,
  "pairwise_tie_rate": 1.0,
  "hard_fail_count_baseline": 0,
  "hard_fail_count_candidate": 0,
  "family_breakdown": {
    "open_research": {
      "candidate_wins": 0,
      "baseline_wins": 0,
      "ties": 1
    }
  },
  "all_passed": true,
  "branch_outcome_schema": "branch_outcome_v1",
  "cases_with_any_branch_non_ok": 0,
  "baseline_status_counts": {
    "ok": 1
  },
  "candidate_status_counts": {
    "ok": 1
  },
  "error_kind_counts": {},
  "baseline_timeout_cases": [],
  "candidate_timeout_cases": [],
  "baseline_error_cases": [],
  "candidate_error_cases": [],
  "cost_delta": {
    "latency_p95_baseline_ms": 50.0,
    "latency_p95_candidate_ms": 120.0,
    "latency_p95_ratio": 2.4,
    "tokens_total_baseline": 100.0,
    "tokens_total_candidate": 180.0,
    "tokens_total_ratio": 1.8,
    "cases_with_latency_samples": 1,
    "cases_with_token_samples_baseline": 1,
    "cases_with_token_samples_candidate": 1
  }
}
```

## mini_open_research_01 — PASS

winner=tie confidence=low

```json
{
  "pairwise": {
    "winner": "tie",
    "confidence": "low",
    "rationale": "heuristic_judge_no_llm: compare answer length, hard-fail heuristics, and gold requirements"
  },
  "baseline_outcome": {
    "status": "ok",
    "error_kind": null,
    "timeout_seconds": null,
    "error_message": null
  },
  "candidate_outcome": {
    "status": "ok",
    "error_kind": null,
    "timeout_seconds": null,
    "error_message": null
  },
  "timings": {
    "judge_wall_s": 0.0,
    "case_wall_s": 0.0
  },
  "latency_ms": {
    "baseline": 50,
    "candidate": 120
  },
  "usage_total_tokens": {
    "baseline": 100,
    "candidate": 180
  }
}
```
