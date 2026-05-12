# Agent v3 quality judge — judge_mini

Cases: 8  seeds: 3

```json
{
  "case_count": 8,
  "mean_weighted_score_baseline": 4.7812,
  "mean_weighted_score_candidate": 4.4062,
  "mean_delta": -0.375,
  "pairwise_candidate_win_rate": 0.125,
  "pairwise_baseline_win_rate": 0.25,
  "pairwise_tie_rate": 0.625,
  "hard_fail_count_baseline": 1,
  "hard_fail_count_candidate": 3,
  "family_breakdown": {
    "catalog_resolution": {
      "candidate_wins": 1,
      "baseline_wins": 0,
      "ties": 1
    },
    "dual_evidence_compare": {
      "candidate_wins": 0,
      "baseline_wins": 1,
      "ties": 0
    },
    "open_research": {
      "candidate_wins": 0,
      "baseline_wins": 1,
      "ties": 0
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
  "all_passed": false,
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
    "latency_p95_baseline_ms": 122062.0,
    "latency_p95_candidate_ms": 150766.0,
    "latency_p95_ratio": 1.2352,
    "tokens_total_baseline": null,
    "tokens_total_candidate": null,
    "tokens_total_ratio": null,
    "cases_with_latency_samples": 8,
    "cases_with_token_samples_baseline": 0,
    "cases_with_token_samples_candidate": 0
  },
  "multiseed": {
    "per_seed": [
      {
        "seed_index": 0,
        "mean_delta": -0.35,
        "pairwise_candidate_win_rate": 0.25,
        "cost_delta": {
          "latency_p95_baseline_ms": 122062.0,
          "latency_p95_candidate_ms": 150766.0,
          "latency_p95_ratio": 1.2352,
          "tokens_total_baseline": null,
          "tokens_total_candidate": null,
          "tokens_total_ratio": null,
          "cases_with_latency_samples": 8,
          "cases_with_token_samples_baseline": 0,
          "cases_with_token_samples_candidate": 0
        }
      },
      {
        "seed_index": 1,
        "mean_delta": -0.75,
        "pairwise_candidate_win_rate": 0.125,
        "cost_delta": {
          "latency_p95_baseline_ms": 122062.0,
          "latency_p95_candidate_ms": 150766.0,
          "latency_p95_ratio": 1.2352,
          "tokens_total_baseline": null,
          "tokens_total_candidate": null,
          "tokens_total_ratio": null,
          "cases_with_latency_samples": 8,
          "cases_with_token_samples_baseline": 0,
          "cases_with_token_samples_candidate": 0
        }
      },
      {
        "seed_index": 2,
        "mean_delta": -0.375,
        "pairwise_candidate_win_rate": 0.125,
        "cost_delta": {
          "latency_p95_baseline_ms": 122062.0,
          "latency_p95_candidate_ms": 150766.0,
          "latency_p95_ratio": 1.2352,
          "tokens_total_baseline": null,
          "tokens_total_candidate": null,
          "tokens_total_ratio": null,
          "cases_with_latency_samples": 8,
          "cases_with_token_samples_baseline": 0,
          "cases_with_token_samples_candidate": 0
        }
      }
    ],
    "mean_delta_min": -0.75,
    "mean_delta_max": -0.35,
    "mean_delta_median": -0.375,
    "mean_delta_spread": 0.4
  }
}
```

## mini_catalog_resolution_01 — PASS

winner=tie confidence=high

```json
{
  "pairwise": {
    "winner": "tie",
    "confidence": "high",
    "rationale": "Both the baseline and candidate answers correctly identified the work titled 'You Only Look Once: Unified, Real-Time Object Detection' with the same work ID. Both provided the same information regarding the year and venue, which is unknown. The responses are equally correct, complete, grounded, and useful. The candidate's response is slightly more formatted, but this does not add substantive value, hence the tie."
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
    "baseline_wall_s": 29.291,
    "candidate_wall_s": 34.606,
    "judge_wall_s": 6.523,
    "case_wall_s": 6.523
  },
  "latency_ms": {
    "baseline": 28794,
    "candidate": 34095
  },
  "usage_total_tokens": {
    "baseline": null,
    "candidate": null
  }
}
```


---

## mini_catalog_resolution_02 — PASS

winner=candidate confidence=high

```json
{
  "pairwise": {
    "winner": "candidate",
    "confidence": "high",
    "rationale": "The candidate answer is more complete and useful, providing a clearer distinction between YOLO and Faster R-CNN, and is better structured with bullet points. It also maintains better brevity discipline while being more informative."
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
    "baseline_wall_s": 71.602,
    "candidate_wall_s": 47.271,
    "judge_wall_s": 9.0,
    "case_wall_s": 9.0
  },
  "latency_ms": {
    "baseline": 71093,
    "candidate": 46763
  },
  "usage_total_tokens": {
    "baseline": null,
    "candidate": null
  }
}
```


---

## mini_dual_evidence_compare_01 — FAIL

winner=baseline confidence=high

```json
{
  "pairwise": {
    "winner": "baseline",
    "confidence": "high",
    "rationale": "The baseline correctly identifies that only one paper exists in the workspace, making a comparison impossible, and provides thorough evidence. The candidate incorrectly claims a comparison between YOLO and RT-DETR, despite RT-DETR not being in the workspace, and makes unsubstantiated claims about RT-DETR's performance."
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
    "baseline_wall_s": 51.086,
    "candidate_wall_s": 151.285,
    "judge_wall_s": 9.602,
    "case_wall_s": 9.602
  },
  "latency_ms": {
    "baseline": 50584,
    "candidate": 150766
  },
  "usage_total_tokens": {
    "baseline": null,
    "candidate": null
  }
}
```


---

## mini_open_research_01 — PASS

winner=baseline confidence=medium

```json
{
  "pairwise": {
    "winner": "baseline",
    "confidence": "medium",
    "rationale": "Both answers are well-grounded and correct, but the baseline provides a more comprehensive synthesis of the information, including more detailed comparisons and uncertainties. The candidate is slightly more concise but misses some details and nuances present in the baseline."
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
    "baseline_wall_s": 122.583,
    "candidate_wall_s": 70.794,
    "judge_wall_s": 5.887,
    "case_wall_s": 5.887
  },
  "latency_ms": {
    "baseline": 122062,
    "candidate": 70276
  },
  "usage_total_tokens": {
    "baseline": null,
    "candidate": null
  }
}
```


---

## mini_quote_evidence_01 — PASS

winner=tie confidence=high

```json
{
  "pairwise": {
    "winner": "tie",
    "confidence": "high",
    "rationale": "Both the baseline and candidate responses provide identical verbatim quotes from the YOLOv1 paper that support the claim of real-time detection performance. Both responses are fully correct, complete, grounded, and useful, with no unnecessary verbosity. The citations and tool traces are also identical, indicating no difference in quality or performance."
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
    "baseline_wall_s": 32.593,
    "candidate_wall_s": 44.715,
    "judge_wall_s": 8.978,
    "case_wall_s": 8.979
  },
  "latency_ms": {
    "baseline": 32085,
    "candidate": 44202
  },
  "usage_total_tokens": {
    "baseline": null,
    "candidate": null
  }
}
```


---

## mini_relation_tracing_01 — FAIL

winner=tie confidence=high

```json
{
  "pairwise": {
    "winner": "tie",
    "confidence": "high",
    "rationale": "Both responses correctly identify the inability to locate the YOLOv1 paper due to permission limitations and provide a similar explanation for the lack of results. Neither response provides a final answer or uses citations, and both are equally concise and useful given the constraints."
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
    "baseline_wall_s": 25.865,
    "candidate_wall_s": 14.702,
    "judge_wall_s": 6.352,
    "case_wall_s": 6.352
  },
  "latency_ms": {
    "baseline": 25354,
    "candidate": 14195
  },
  "usage_total_tokens": {
    "baseline": null,
    "candidate": null
  }
}
```


---

## mini_workspace_stats_01 — PASS

winner=tie confidence=high

```json
{
  "pairwise": {
    "winner": "tie",
    "confidence": "high",
    "rationale": "Both answers provide the same core information about the workspace containing 1 work and the inability to provide a breakdown by type due to permission restrictions. The phrasing and structure are nearly identical, with no meaningful differences in quality or content."
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
    "baseline_wall_s": 24.035,
    "candidate_wall_s": 24.705,
    "judge_wall_s": 8.481,
    "case_wall_s": 8.481
  },
  "latency_ms": {
    "baseline": 23521,
    "candidate": 24183
  },
  "usage_total_tokens": {
    "baseline": null,
    "candidate": null
  }
}
```


---

## mini_workspace_stats_02 — PASS

winner=tie confidence=high

```json
{
  "pairwise": {
    "winner": "tie",
    "confidence": "high",
    "rationale": "Both the baseline and candidate provided identical answers, correctly listing the single paper in the workspace `ws-pilot-od` and explaining how the list was scoped. Both responses were concise, accurate, and grounded in the workspace inspection. There is no discernible difference in quality or completeness between the two."
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
    "baseline_wall_s": 36.295,
    "candidate_wall_s": 31.94,
    "judge_wall_s": 6.675,
    "case_wall_s": 6.675
  },
  "latency_ms": {
    "baseline": 35782,
    "candidate": 31424
  },
  "usage_total_tokens": {
    "baseline": null,
    "candidate": null
  }
}
```
