# Claims benchmark suite

Cases: 5

Model: mistralai/mistral-small-3.2-24b-instruct
Layer-1 prompt fingerprint: sha256-20:210f7e16d3e0a07ad571
Semantic prompt fingerprint: sha256-20:19c459f1df53094b0a19

## holdout_atss_v1 — PASS

```json
{
  "contract_only": false,
  "contract_passed": true,
  "passed": true,
  "claim_recall": 0.25,
  "claim_precision": 0.125,
  "claim_precision_distracted": 0.125,
  "precision_drop_with_distractors": 0.0,
  "max_precision_drop_with_distractors": 0.15,
  "paraphrase_scoring": true,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 4,
  "predicted_count_plain": 8,
  "predicted_count_distracted": 8,
  "matched_claim_ids": [
    "atss_essential_difference_finding"
  ],
  "missing_claim_ids": [
    "atss_adaptive_sample_selection",
    "atss_retinanet_matches_fcos",
    "atss_arch_alone_no_advantage_negative"
  ],
  "min_claim_recall": 0.22
}
```


---

## holdout_deformable_detr_v1 — FAIL

```json
{
  "passed": false,
  "contract_only": false,
  "contract_passed": false,
  "request_error": "per_case_timeout_exceeded (120.0s)"
}
```


---

## holdout_dino_v1 — FAIL

```json
{
  "contract_only": false,
  "contract_passed": true,
  "passed": false,
  "claim_recall": 0.2,
  "claim_precision": 0.058823529411764705,
  "claim_precision_distracted": 0.0,
  "precision_drop_with_distractors": 0.058823529411764705,
  "max_precision_drop_with_distractors": 0.15,
  "paraphrase_scoring": true,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 5,
  "predicted_count_plain": 17,
  "predicted_count_distracted": 17,
  "matched_claim_ids": [
    "dino_three_components"
  ],
  "missing_claim_ids": [
    "dino_swinl_63ap",
    "dino_detr_scaling_overcomes_classical",
    "dino_earlier_detr_slow_small_obj_negative",
    "dino_classical_pipelines_scaling_negative"
  ],
  "min_claim_recall": 0.55
}
```


---

## holdout_yolov3_v1 — FAIL

```json
{
  "contract_only": false,
  "contract_passed": true,
  "passed": false,
  "claim_recall": 0.25,
  "claim_precision": 0.125,
  "claim_precision_distracted": 0.20833333333333334,
  "precision_drop_with_distractors": 0.0,
  "max_precision_drop_with_distractors": 0.15,
  "paraphrase_scoring": true,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 4,
  "predicted_count_plain": 16,
  "predicted_count_distracted": 24,
  "matched_claim_ids": [
    "yolov3_strict_iou_underperform_negative"
  ],
  "missing_claim_ids": [
    "yolov3_three_scale_predictions",
    "yolov3_logistic_per_class",
    "yolov3_speed_vs_retinanet"
  ],
  "min_claim_recall": 0.55
}
```


---

## holdout_yolox_v1 — FAIL

```json
{
  "contract_only": false,
  "contract_passed": true,
  "passed": false,
  "claim_recall": 0.5,
  "claim_precision": 0.5,
  "claim_precision_distracted": 0.1,
  "precision_drop_with_distractors": 0.4,
  "max_precision_drop_with_distractors": 0.15,
  "paraphrase_scoring": true,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 4,
  "predicted_count_plain": 10,
  "predicted_count_distracted": 10,
  "matched_claim_ids": [
    "yolox_decoupled_head",
    "yolox_l_50ap_v100_speed"
  ],
  "missing_claim_ids": [
    "yolox_anchor_free_simota",
    "yolox_coupled_head_conflict_negative"
  ],
  "min_claim_recall": 0.55
}
```
