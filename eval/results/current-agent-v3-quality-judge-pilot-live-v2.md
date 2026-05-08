# Agent v3 quality judge — judge_pilot

Cases: 10

```json
{
  "case_count": 10,
  "mean_weighted_score_baseline": 4.0,
  "mean_weighted_score_candidate": 4.0,
  "mean_delta": 0.0,
  "pairwise_candidate_win_rate": 0.4,
  "pairwise_baseline_win_rate": 0.4,
  "pairwise_tie_rate": 0.2,
  "hard_fail_count_baseline": 0,
  "hard_fail_count_candidate": 0,
  "family_breakdown": {
    "catalog_resolution": {
      "candidate_wins": 0,
      "baseline_wins": 1,
      "ties": 1
    },
    "dual_evidence_compare": {
      "candidate_wins": 0,
      "baseline_wins": 2,
      "ties": 0
    },
    "open_research": {
      "candidate_wins": 1,
      "baseline_wins": 0,
      "ties": 0
    },
    "quote_evidence": {
      "candidate_wins": 0,
      "baseline_wins": 1,
      "ties": 0
    },
    "relation_tracing": {
      "candidate_wins": 2,
      "baseline_wins": 0,
      "ties": 0
    },
    "workspace_stats": {
      "candidate_wins": 1,
      "baseline_wins": 0,
      "ties": 1
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
    "baseline_wall_s": 13.063,
    "candidate_wall_s": 12.734,
    "judge_wall_s": 0.0,
    "case_wall_s": 25.798
  }
}
```


---

## mini_catalog_resolution_02 — PASS

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
    "baseline_wall_s": 20.096,
    "candidate_wall_s": 17.882,
    "judge_wall_s": 0.0,
    "case_wall_s": 37.978
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
    "baseline_wall_s": 219.169,
    "candidate_wall_s": 238.518,
    "judge_wall_s": 0.0,
    "case_wall_s": 457.687
  }
}
```


---

## mini_open_research_01 — PASS

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
    "baseline_wall_s": 32.749,
    "candidate_wall_s": 34.443,
    "judge_wall_s": 0.0,
    "case_wall_s": 67.192
  }
}
```


---

## mini_quote_evidence_01 — PASS

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
    "baseline_wall_s": 19.237,
    "candidate_wall_s": 18.273,
    "judge_wall_s": 0.0,
    "case_wall_s": 37.511
  }
}
```


---

## mini_relation_tracing_01 — PASS

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
    "baseline_wall_s": 12.146,
    "candidate_wall_s": 11.52,
    "judge_wall_s": 0.0,
    "case_wall_s": 23.666
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
    "baseline_wall_s": 12.153,
    "candidate_wall_s": 12.267,
    "judge_wall_s": 0.0,
    "case_wall_s": 24.42
  }
}
```


---

## mini_workspace_stats_02 — PASS

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
    "baseline_wall_s": 10.198,
    "candidate_wall_s": 15.351,
    "judge_wall_s": 0.0,
    "case_wall_s": 25.55
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
    "baseline_wall_s": 96.677,
    "candidate_wall_s": 66.795,
    "judge_wall_s": 0.0,
    "case_wall_s": 163.473
  }
}
```


---

## pilot_relation_extra_01 — PASS

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
    "baseline_wall_s": 25.462,
    "candidate_wall_s": 23.86,
    "judge_wall_s": 0.0,
    "case_wall_s": 49.321
  }
}
```
