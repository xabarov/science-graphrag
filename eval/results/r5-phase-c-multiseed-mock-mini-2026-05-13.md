# Agent v3 quality judge — judge_mini

Cases: 8  seeds: 3

```json
{
  "case_count": 8,
  "mean_weighted_score_baseline": 4.0,
  "mean_weighted_score_candidate": 4.0,
  "mean_delta": 0.0,
  "pairwise_candidate_win_rate": 0.0,
  "pairwise_baseline_win_rate": 0.0,
  "pairwise_tie_rate": 1.0,
  "hard_fail_count_baseline": 0,
  "hard_fail_count_candidate": 0,
  "family_breakdown": {
    "catalog_resolution": {
      "candidate_wins": 0,
      "baseline_wins": 0,
      "ties": 2
    },
    "dual_evidence_compare": {
      "candidate_wins": 0,
      "baseline_wins": 0,
      "ties": 1
    },
    "open_research": {
      "candidate_wins": 0,
      "baseline_wins": 0,
      "ties": 1
    },
    "quote_evidence": {
      "candidate_wins": 0,
      "baseline_wins": 0,
      "ties": 1
    },
    "relation_tracing": {
      "candidate_wins": 0,
      "baseline_wins": 0,
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
    "ok": 8
  },
  "candidate_status_counts": {
    "ok": 8
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
    "tokens_total_baseline": 800.0,
    "tokens_total_candidate": 1440.0,
    "tokens_total_ratio": 1.8,
    "cases_with_latency_samples": 8,
    "cases_with_token_samples_baseline": 8,
    "cases_with_token_samples_candidate": 8
  },
  "multiseed": {
    "per_seed": [
      {
        "seed_index": 0,
        "mean_delta": 0.0,
        "pairwise_candidate_win_rate": 0.0,
        "cost_delta": {
          "latency_p95_baseline_ms": 50.0,
          "latency_p95_candidate_ms": 120.0,
          "latency_p95_ratio": 2.4,
          "tokens_total_baseline": 800.0,
          "tokens_total_candidate": 1440.0,
          "tokens_total_ratio": 1.8,
          "cases_with_latency_samples": 8,
          "cases_with_token_samples_baseline": 8,
          "cases_with_token_samples_candidate": 8
        }
      },
      {
        "seed_index": 1,
        "mean_delta": 0.0,
        "pairwise_candidate_win_rate": 0.0,
        "cost_delta": {
          "latency_p95_baseline_ms": 50.0,
          "latency_p95_candidate_ms": 120.0,
          "latency_p95_ratio": 2.4,
          "tokens_total_baseline": 800.0,
          "tokens_total_candidate": 1440.0,
          "tokens_total_ratio": 1.8,
          "cases_with_latency_samples": 8,
          "cases_with_token_samples_baseline": 8,
          "cases_with_token_samples_candidate": 8
        }
      },
      {
        "seed_index": 2,
        "mean_delta": 0.0,
        "pairwise_candidate_win_rate": 0.0,
        "cost_delta": {
          "latency_p95_baseline_ms": 50.0,
          "latency_p95_candidate_ms": 120.0,
          "latency_p95_ratio": 2.4,
          "tokens_total_baseline": 800.0,
          "tokens_total_candidate": 1440.0,
          "tokens_total_ratio": 1.8,
          "cases_with_latency_samples": 8,
          "cases_with_token_samples_baseline": 8,
          "cases_with_token_samples_candidate": 8
        }
      }
    ],
    "mean_delta_min": 0.0,
    "mean_delta_max": 0.0,
    "mean_delta_median": 0.0,
    "mean_delta_spread": 0.0
  }
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


---

## mini_catalog_resolution_02 — PASS

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


---

## mini_dual_evidence_compare_01 — PASS

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


---

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


---

## mini_quote_evidence_01 — PASS

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
