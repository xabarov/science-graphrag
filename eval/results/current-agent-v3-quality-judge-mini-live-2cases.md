# Agent v3 quality judge — judge_mini

Cases: 2

```json
{
  "case_count": 2,
  "mean_weighted_score_baseline": 4.0,
  "mean_weighted_score_candidate": 4.0,
  "mean_delta": 0.0,
  "pairwise_candidate_win_rate": 0.5,
  "pairwise_baseline_win_rate": 0.0,
  "pairwise_tie_rate": 0.5,
  "hard_fail_count_baseline": 0,
  "hard_fail_count_candidate": 0,
  "family_breakdown": {
    "catalog_resolution": {
      "candidate_wins": 1,
      "baseline_wins": 0,
      "ties": 1
    }
  },
  "all_passed": true
}
```

## mini_catalog_resolution_01 — PASS

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


---

## mini_catalog_resolution_02 — PASS

winner=candidate confidence=low

```json
{
  "pairwise": {
    "winner": "candidate",
    "confidence": "low",
    "rationale": "heuristic_judge_no_llm: compare answer length, hard-fail heuristics, and gold requirements"
  }
}
```
