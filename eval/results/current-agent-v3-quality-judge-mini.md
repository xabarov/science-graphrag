# Agent v3 quality judge — judge_mini

Cases: 8

```json
{
  "case_count": 8,
  "mean_weighted_score_baseline": 4.0,
  "mean_weighted_score_candidate": 4.0,
  "mean_delta": 0.0,
  "pairwise_candidate_win_rate": 0.25,
  "pairwise_baseline_win_rate": 0.375,
  "pairwise_tie_rate": 0.375,
  "hard_fail_count_baseline": 0,
  "hard_fail_count_candidate": 0,
  "family_breakdown": {
    "catalog_resolution": {
      "candidate_wins": 0,
      "baseline_wins": 1,
      "ties": 1
    },
    "dual_evidence_compare": {
      "candidate_wins": 1,
      "baseline_wins": 0,
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
      "candidate_wins": 0,
      "baseline_wins": 0,
      "ties": 1
    },
    "workspace_stats": {
      "candidate_wins": 0,
      "baseline_wins": 1,
      "ties": 1
    }
  },
  "all_passed": true,
  "branch_outcome_schema": "branch_outcome_v1",
  "cases_with_any_branch_non_ok": 0,
  "baseline_status_counts": {
    "ok": 8
  },
  "candidate_status_counts": {
    "ok": 8
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
    "baseline_wall_s": 11.978,
    "candidate_wall_s": 14.076,
    "judge_wall_s": 0.0,
    "case_wall_s": 26.054
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
    "baseline_wall_s": 20.208,
    "candidate_wall_s": 26.859,
    "judge_wall_s": 0.0,
    "case_wall_s": 47.067
  }
}
```


---

## mini_dual_evidence_compare_01 — PASS

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
    "baseline_wall_s": 54.425,
    "candidate_wall_s": 60.446,
    "judge_wall_s": 0.0,
    "case_wall_s": 114.871
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
    "baseline_wall_s": 35.805,
    "candidate_wall_s": 35.789,
    "judge_wall_s": 0.0,
    "case_wall_s": 71.594
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
    "baseline_wall_s": 21.587,
    "candidate_wall_s": 17.99,
    "judge_wall_s": 0.0,
    "case_wall_s": 39.577
  }
}
```


---

## mini_relation_tracing_01 — PASS

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
    "baseline_wall_s": 7.317,
    "candidate_wall_s": 7.429,
    "judge_wall_s": 0.0,
    "case_wall_s": 14.746
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
    "baseline_wall_s": 11.196,
    "candidate_wall_s": 7.7,
    "judge_wall_s": 0.0,
    "case_wall_s": 18.896
  }
}
```


---

## mini_workspace_stats_02 — PASS

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
    "baseline_wall_s": 9.985,
    "candidate_wall_s": 15.476,
    "judge_wall_s": 0.0,
    "case_wall_s": 25.461
  }
}
```
