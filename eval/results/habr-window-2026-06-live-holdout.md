# Claims paraphrase benchmark (BT6)

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
  "claim_precision": 0.09090909090909091,
  "claim_precision_distracted": 0.14285714285714285,
  "precision_drop_with_distractors": 0.0,
  "max_precision_drop_with_distractors": 0.15,
  "paraphrase_scoring": true,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 4,
  "predicted_count_plain": 11,
  "predicted_count_distracted": 14,
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
  "contract_only": false,
  "contract_passed": true,
  "passed": false,
  "claim_recall": 0.25,
  "claim_precision": 0.25,
  "claim_precision_distracted": 0.42857142857142855,
  "precision_drop_with_distractors": 0.0,
  "max_precision_drop_with_distractors": 0.15,
  "paraphrase_scoring": true,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 4,
  "predicted_count_plain": 16,
  "predicted_count_distracted": 14,
  "matched_claim_ids": [
    "deformable_detr_attention_modules"
  ],
  "missing_claim_ids": [
    "deformable_detr_10x_faster_convergence",
    "deformable_detr_multiscale_efficient",
    "deformable_detr_global_attention_negative"
  ],
  "min_claim_recall": 0.55
}
```


---

## holdout_dino_v1 — FAIL

```json
{
  "contract_only": false,
  "contract_passed": true,
  "passed": false,
  "claim_recall": 0.0,
  "claim_precision": 0.0,
  "claim_precision_distracted": 0.0,
  "precision_drop_with_distractors": 0.0,
  "max_precision_drop_with_distractors": 0.15,
  "paraphrase_scoring": true,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 5,
  "predicted_count_plain": 3,
  "predicted_count_distracted": 3,
  "matched_claim_ids": [],
  "missing_claim_ids": [
    "dino_three_components",
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
  "claim_recall": 0.5,
  "claim_precision": 0.22727272727272727,
  "claim_precision_distracted": 0.2222222222222222,
  "precision_drop_with_distractors": 0.005050505050505055,
  "max_precision_drop_with_distractors": 0.15,
  "paraphrase_scoring": true,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 4,
  "predicted_count_plain": 22,
  "predicted_count_distracted": 27,
  "matched_claim_ids": [
    "yolov3_three_scale_predictions",
    "yolov3_strict_iou_underperform_negative"
  ],
  "missing_claim_ids": [
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
  "claim_precision": 0.3333333333333333,
  "claim_precision_distracted": 0.07142857142857142,
  "precision_drop_with_distractors": 0.26190476190476186,
  "max_precision_drop_with_distractors": 0.15,
  "paraphrase_scoring": true,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 4,
  "predicted_count_plain": 15,
  "predicted_count_distracted": 14,
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
