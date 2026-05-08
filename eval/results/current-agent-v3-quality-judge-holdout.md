# Agent v3 quality judge — judge_holdout

Cases: 1

```json
{
  "case_count": 1,
  "mean_weighted_score_baseline": 4.0,
  "mean_weighted_score_candidate": 4.0,
  "mean_delta": 0.0,
  "pairwise_candidate_win_rate": 1.0,
  "pairwise_baseline_win_rate": 0.0,
  "pairwise_tie_rate": 0.0,
  "hard_fail_count_baseline": 0,
  "hard_fail_count_candidate": 0,
  "family_breakdown": {
    "open_research": {
      "candidate_wins": 1,
      "baseline_wins": 0,
      "ties": 0
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
  "candidate_error_cases": []
}
```

## holdout_open_01 — PASS

winner=candidate confidence=low

```json
{
  "pairwise": {
    "winner": "candidate",
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
    "baseline_wall_s": 18.346,
    "candidate_wall_s": 22.178,
    "judge_wall_s": 0.0,
    "case_wall_s": 40.524
  }
}
```
