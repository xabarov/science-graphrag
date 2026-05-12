# Agent v3 quality judge — judge_pilot

Cases: 13  seeds: 3

```json
{
  "case_count": 13,
  "mean_weighted_score_baseline": 5.2346,
  "mean_weighted_score_candidate": 5.4923,
  "mean_delta": 0.2577,
  "pairwise_candidate_win_rate": 0.3846,
  "pairwise_baseline_win_rate": 0.0769,
  "pairwise_tie_rate": 0.5385,
  "hard_fail_count_baseline": 2,
  "hard_fail_count_candidate": 1,
  "family_breakdown": {
    "catalog_resolution": {
      "candidate_wins": 0,
      "baseline_wins": 0,
      "ties": 2
    },
    "dual_evidence_compare": {
      "candidate_wins": 2,
      "baseline_wins": 0,
      "ties": 0
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
      "candidate_wins": 1,
      "baseline_wins": 1,
      "ties": 0
    },
    "workspace_stats": {
      "candidate_wins": 1,
      "baseline_wins": 0,
      "ties": 1
    },
    "multi_workspace_inspect": {
      "candidate_wins": 0,
      "baseline_wins": 0,
      "ties": 1
    },
    "negative_case_refusal": {
      "candidate_wins": 0,
      "baseline_wins": 0,
      "ties": 1
    },
    "quote_evidence_grounding": {
      "candidate_wins": 1,
      "baseline_wins": 0,
      "ties": 0
    }
  },
  "all_passed": false,
  "branch_outcome_schema": "branch_outcome_v1",
  "cases_with_any_branch_non_ok": 0,
  "baseline_status_counts": {
    "ok": 13
  },
  "candidate_status_counts": {
    "ok": 13
  },
  "error_kind_counts": {},
  "baseline_timeout_cases": [],
  "candidate_timeout_cases": [],
  "baseline_error_cases": [],
  "candidate_error_cases": [],
  "cost_delta": {
    "latency_p95_baseline_ms": 236755.0,
    "latency_p95_candidate_ms": 228895.0,
    "latency_p95_ratio": 0.9668,
    "tokens_total_baseline": null,
    "tokens_total_candidate": null,
    "tokens_total_ratio": null,
    "cases_with_latency_samples": 13,
    "cases_with_token_samples_baseline": 0,
    "cases_with_token_samples_candidate": 0
  },
  "multiseed": {
    "per_seed": [
      {
        "seed_index": 0,
        "mean_delta": 0.3808,
        "pairwise_candidate_win_rate": 0.5385,
        "cost_delta": {
          "latency_p95_baseline_ms": 236755.0,
          "latency_p95_candidate_ms": 228895.0,
          "latency_p95_ratio": 0.9668,
          "tokens_total_baseline": null,
          "tokens_total_candidate": null,
          "tokens_total_ratio": null,
          "cases_with_latency_samples": 13,
          "cases_with_token_samples_baseline": 0,
          "cases_with_token_samples_candidate": 0
        }
      },
      {
        "seed_index": 1,
        "mean_delta": 0.3923,
        "pairwise_candidate_win_rate": 0.4615,
        "cost_delta": {
          "latency_p95_baseline_ms": 236755.0,
          "latency_p95_candidate_ms": 228895.0,
          "latency_p95_ratio": 0.9668,
          "tokens_total_baseline": null,
          "tokens_total_candidate": null,
          "tokens_total_ratio": null,
          "cases_with_latency_samples": 13,
          "cases_with_token_samples_baseline": 0,
          "cases_with_token_samples_candidate": 0
        }
      },
      {
        "seed_index": 2,
        "mean_delta": 0.2577,
        "pairwise_candidate_win_rate": 0.3846,
        "cost_delta": {
          "latency_p95_baseline_ms": 236755.0,
          "latency_p95_candidate_ms": 228895.0,
          "latency_p95_ratio": 0.9668,
          "tokens_total_baseline": null,
          "tokens_total_candidate": null,
          "tokens_total_ratio": null,
          "cases_with_latency_samples": 13,
          "cases_with_token_samples_baseline": 0,
          "cases_with_token_samples_candidate": 0
        }
      }
    ],
    "mean_delta_min": 0.2577,
    "mean_delta_max": 0.3923,
    "mean_delta_median": 0.3808,
    "mean_delta_spread": 0.1346
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
    "rationale": "Both the baseline and candidate answers provide identical information regarding the title, year, venue, and work ID of the paper closest to 'You Only Look Once' object detection. Both responses are correct, complete, grounded, well-synthesized, useful, and concise. There are no discernible differences in quality or content between the two answers."
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
    "baseline_wall_s": 21.862,
    "candidate_wall_s": 21.368,
    "judge_wall_s": 6.792,
    "case_wall_s": 6.792
  },
  "latency_ms": {
    "baseline": 21357,
    "candidate": 20874
  },
  "usage_total_tokens": {
    "baseline": null,
    "candidate": null
  }
}
```


---

## mini_catalog_resolution_02 — PASS

winner=tie confidence=high

```json
{
  "pairwise": {
    "winner": "tie",
    "confidence": "high",
    "rationale": "Both the baseline and candidate correctly identify that the only paper in the workspace `ws-pilot-od` is *You Only Look Once: Unified, Real-Time Object Detection*, which is a single-stage detector and not a Faster R-CNN style two-stage detector. Both answers are equally correct, complete, grounded, and useful, with no unnecessary verbosity. The tool traces and citations are identical, indicating the same reasoning process was followed."
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
    "baseline_wall_s": 35.469,
    "candidate_wall_s": 39.341,
    "judge_wall_s": 7.147,
    "case_wall_s": 7.147
  },
  "latency_ms": {
    "baseline": 34953,
    "candidate": 38813
  },
  "usage_total_tokens": {
    "baseline": null,
    "candidate": null
  }
}
```


---

## mini_dual_evidence_compare_01 — PASS

winner=candidate confidence=medium

```json
{
  "pairwise": {
    "winner": "candidate",
    "confidence": "medium",
    "rationale": "The candidate provides a more structured comparison, explicitly detailing both similarities and differences between YOLO and RT-DETR, which aligns better with the user's request for a balanced comparison. Both answers are correct and well-grounded, but the candidate's synthesis is more comprehensive and clearer, making it more useful. The candidate also maintains brevity without sacrificing coverage, enhancing its readability and effectiveness."
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
    "baseline_wall_s": 237.257,
    "candidate_wall_s": 229.41,
    "judge_wall_s": 7.167,
    "case_wall_s": 7.167
  },
  "latency_ms": {
    "baseline": 236755,
    "candidate": 228895
  },
  "usage_total_tokens": {
    "baseline": null,
    "candidate": null
  }
}
```


---

## mini_open_research_01 — PASS

winner=tie confidence=high

```json
{
  "pairwise": {
    "winner": "tie",
    "confidence": "high",
    "rationale": "Both the baseline and candidate answers provide comprehensive, accurate, and well-grounded summaries of the YOLO paper's findings regarding one-stage vs. two-stage detectors. They cover key points such as speed, accuracy trade-offs, architectural differences, and uncertainties. The candidate is slightly more concise, but both are equally useful and complete."
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
    "baseline_wall_s": 80.492,
    "candidate_wall_s": 223.088,
    "judge_wall_s": 7.645,
    "case_wall_s": 7.645
  },
  "latency_ms": {
    "baseline": 79976,
    "candidate": 222553
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
    "rationale": "Both the baseline and candidate answers provide accurate, complete, and well-grounded verbatim quotes from the main paper that support the claim that YOLOv1 is a real-time detector. Both answers are concise and directly address the user's request for quotes with citations. The differences in the quotes selected are minor and do not impact the overall quality or usefulness of the answers."
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
    "baseline_wall_s": 75.816,
    "candidate_wall_s": 25.688,
    "judge_wall_s": 5.258,
    "case_wall_s": 5.259
  },
  "latency_ms": {
    "baseline": 75309,
    "candidate": 25181
  },
  "usage_total_tokens": {
    "baseline": null,
    "candidate": null
  }
}
```


---

## mini_relation_tracing_01 — FAIL

winner=baseline confidence=high

```json
{
  "pairwise": {
    "winner": "baseline",
    "confidence": "high",
    "rationale": "The baseline answer provides a clear explanation of the citation chain structure and acknowledges the absence of citing papers, while the candidate fails to deliver any substantive answer due to tool access issues. The baseline's groundedness and correctness are superior, making it the clear winner."
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
    "baseline_wall_s": 64.482,
    "candidate_wall_s": 10.766,
    "judge_wall_s": 7.727,
    "case_wall_s": 7.727
  },
  "latency_ms": {
    "baseline": 63976,
    "candidate": 10267
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
    "rationale": "Both the baseline and candidate provide the same correct information about the workspace containing 1 work and the unavailability of a breakdown by work type. Both answers are concise, grounded, and useful, with no significant differences in quality or completeness."
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
    "baseline_wall_s": 10.863,
    "candidate_wall_s": 8.378,
    "judge_wall_s": 5.765,
    "case_wall_s": 5.765
  },
  "latency_ms": {
    "baseline": 10366,
    "candidate": 7872
  },
  "usage_total_tokens": {
    "baseline": null,
    "candidate": null
  }
}
```


---

## mini_workspace_stats_02 — PASS

winner=candidate confidence=medium

```json
{
  "pairwise": {
    "winner": "candidate",
    "confidence": "medium",
    "rationale": "Both answers correctly identify the single paper in the workspace and provide the same citation. The candidate slightly improves on completeness by explicitly stating the inspection method (`mode=papers`) and matches the baseline in all other aspects. The difference is minor but consistent enough to favor the candidate."
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
    "baseline_wall_s": 24.281,
    "candidate_wall_s": 15.114,
    "judge_wall_s": 7.481,
    "case_wall_s": 7.481
  },
  "latency_ms": {
    "baseline": 23776,
    "candidate": 14591
  },
  "usage_total_tokens": {
    "baseline": null,
    "candidate": null
  }
}
```


---

## pilot_catalog_extra_01 — FAIL

winner=candidate confidence=high

```json
{
  "pairwise": {
    "winner": "candidate",
    "confidence": "high",
    "rationale": "The candidate provides a more accurate and complete comparison of how two works use region proposal networks, directly addressing the user's request for a comparison. It correctly identifies and contrasts the use of RPN in Faster R-CNN with the reliance on external proposals in R-FCN, supported by relevant citations. The baseline, while correct in its description of Faster R-CNN, fails to compare it with another work that uses region proposals, instead incorrectly comparing it with YOLO, which does not use region proposals at all."
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
    "baseline_wall_s": 68.636,
    "candidate_wall_s": 65.447,
    "judge_wall_s": 8.342,
    "case_wall_s": 8.342
  },
  "latency_ms": {
    "baseline": 68130,
    "candidate": 64935
  },
  "usage_total_tokens": {
    "baseline": null,
    "candidate": null
  }
}
```


---

## pilot_multi_workspace_01 — PASS

winner=tie confidence=high

```json
{
  "pairwise": {
    "winner": "tie",
    "confidence": "high",
    "rationale": "Both answers correctly identify that ws-pilot-od contains 1 paper and ws-pilot-alt does not exist, making comparison impossible. The responses are identical in content, structure, and clarity, with no meaningful differences in quality or information provided."
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
    "baseline_wall_s": 13.788,
    "candidate_wall_s": 14.048,
    "judge_wall_s": 7.366,
    "case_wall_s": 7.366
  },
  "latency_ms": {
    "baseline": 13275,
    "candidate": 13514
  },
  "usage_total_tokens": {
    "baseline": null,
    "candidate": null
  }
}
```


---

## pilot_negative_refusal_01 — PASS

winner=tie confidence=high

```json
{
  "pairwise": {
    "winner": "tie",
    "confidence": "high",
    "rationale": "Both answers correctly identify the empty workspace and lack of access to external resources, providing clear and concise refusals without attempting to fabricate information. The responses are equally correct, complete, and grounded, with no unnecessary verbosity or omissions."
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
    "baseline_wall_s": 20.567,
    "candidate_wall_s": 15.661,
    "judge_wall_s": 6.907,
    "case_wall_s": 6.907
  },
  "latency_ms": {
    "baseline": 20047,
    "candidate": 15164
  },
  "usage_total_tokens": {
    "baseline": null,
    "candidate": null
  }
}
```


---

## pilot_quote_grounding_01 — PASS

winner=candidate confidence=high

```json
{
  "pairwise": {
    "winner": "candidate",
    "confidence": "high",
    "rationale": "The candidate answer is superior in all aspects. It provides a more structured and detailed response, clearly enumerating key contributions of YOLO with precise citations. The baseline answer is correct but less organized and slightly less comprehensive. Both answers are well-grounded in the provided citations, but the candidate's synthesis and presentation are notably better."
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
    "baseline_wall_s": 56.546,
    "candidate_wall_s": 165.615,
    "judge_wall_s": 9.769,
    "case_wall_s": 9.769
  },
  "latency_ms": {
    "baseline": 56034,
    "candidate": 165105
  },
  "usage_total_tokens": {
    "baseline": null,
    "candidate": null
  }
}
```


---

## pilot_relation_extra_01 — FAIL

winner=candidate confidence=high

```json
{
  "pairwise": {
    "winner": "candidate",
    "confidence": "high",
    "rationale": "The candidate directly answers the user's question by identifying a concrete citation relationship involving YOLOv1 and provides clear evidence of verification through workspace tools. The baseline fails to address the specific request about YOLOv1 and instead discusses an indirect citation link, which does not meet the user's requirements."
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
    "baseline_wall_s": 85.213,
    "candidate_wall_s": 159.117,
    "judge_wall_s": 8.244,
    "case_wall_s": 8.244
  },
  "latency_ms": {
    "baseline": 84693,
    "candidate": 158601
  },
  "usage_total_tokens": {
    "baseline": null,
    "candidate": null
  }
}
```
