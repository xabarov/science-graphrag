# Agent v3 quality judge — judge_holdout

Cases: 1

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
  "all_passed": true
}
```

## holdout_open_01 — PASS

winner=tie confidence=low

```json
{
  "pairwise": {
    "winner": "tie",
    "confidence": "low",
    "rationale": "heuristic_judge_no_llm: compare answer length, hard-fail heuristics, and gold requirements"
  }
}
```
