# Agent v3 quality judge — judge_pilot

Cases: 10

```json
{
  "case_count": 10,
  "mean_weighted_score_baseline": 4.0,
  "mean_weighted_score_candidate": 4.0,
  "mean_delta": 0.0,
  "pairwise_candidate_win_rate": 0.2,
  "pairwise_baseline_win_rate": 0.4,
  "pairwise_tie_rate": 0.4,
  "hard_fail_count_baseline": 0,
  "hard_fail_count_candidate": 0,
  "family_breakdown": {
    "catalog_resolution": {
      "candidate_wins": 1,
      "baseline_wins": 0,
      "ties": 1
    },
    "dual_evidence_compare": {
      "candidate_wins": 0,
      "baseline_wins": 2,
      "ties": 0
    },
    "open_research": {
      "candidate_wins": 0,
      "baseline_wins": 1,
      "ties": 0
    },
    "quote_evidence": {
      "candidate_wins": 1,
      "baseline_wins": 0,
      "ties": 0
    },
    "relation_tracing": {
      "candidate_wins": 0,
      "baseline_wins": 1,
      "ties": 1
    },
    "workspace_stats": {
      "candidate_wins": 0,
      "baseline_wins": 0,
      "ties": 2
    }
  },
  "all_passed": true,
  "branch_outcome_schema": "branch_outcome_v1",
  "cases_with_any_branch_non_ok": 0,
  "baseline_status_counts": {
    "ok": 10
  },
  "candidate_status_counts": {
    "ok": 10
  },
  "error_kind_counts": {},
  "baseline_timeout_cases": [],
  "candidate_timeout_cases": [],
  "baseline_error_cases": [],
  "candidate_error_cases": []
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
    "baseline_wall_s": 11.532,
    "candidate_wall_s": 12.793,
    "judge_wall_s": 0.0,
    "case_wall_s": 24.326
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
    "baseline_wall_s": 15.944,
    "candidate_wall_s": 18.139,
    "judge_wall_s": 0.0,
    "case_wall_s": 34.083
  }
}
```


---

## mini_dual_evidence_compare_01 — PASS

winner=baseline confidence=low

```json
{
  "pairwise": {
    "winner": "baseline",
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
    "baseline_wall_s": 40.662,
    "candidate_wall_s": 40.828,
    "judge_wall_s": 0.0,
    "case_wall_s": 81.49
  }
}
```


---

## mini_open_research_01 — PASS

winner=baseline confidence=low

```json
{
  "pairwise": {
    "winner": "baseline",
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
    "baseline_wall_s": 28.724,
    "candidate_wall_s": 27.656,
    "judge_wall_s": 0.0,
    "case_wall_s": 56.38
  }
}
```


---

## mini_quote_evidence_01 — PASS

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
    "baseline_wall_s": 14.002,
    "candidate_wall_s": 15.17,
    "judge_wall_s": 0.0,
    "case_wall_s": 29.172
  }
}
```


---

## mini_relation_tracing_01 — PASS

winner=baseline confidence=low

```json
{
  "pairwise": {
    "winner": "baseline",
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
    "baseline_wall_s": 67.681,
    "candidate_wall_s": 23.255,
    "judge_wall_s": 0.0,
    "case_wall_s": 90.937
  }
}
```


---

## mini_workspace_stats_01 — PASS

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
    "baseline_wall_s": 6.822,
    "candidate_wall_s": 7.572,
    "judge_wall_s": 0.0,
    "case_wall_s": 14.395
  }
}
```


---

## mini_workspace_stats_02 — PASS

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
    "baseline_wall_s": 13.029,
    "candidate_wall_s": 9.419,
    "judge_wall_s": 0.0,
    "case_wall_s": 22.448
  }
}
```


---

## pilot_catalog_extra_01 — PASS

winner=baseline confidence=low

```json
{
  "pairwise": {
    "winner": "baseline",
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
    "baseline_wall_s": 109.945,
    "candidate_wall_s": 102.981,
    "judge_wall_s": 0.0,
    "case_wall_s": 212.926
  }
}
```


---

## pilot_relation_extra_01 — PASS

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
    "baseline_wall_s": 21.795,
    "candidate_wall_s": 98.575,
    "judge_wall_s": 0.0,
    "case_wall_s": 120.371
  }
}
```
