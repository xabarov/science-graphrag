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
  "claim_precision": 0.1111111111111111,
  "claim_precision_distracted": 0.1111111111111111,
  "precision_drop_with_distractors": 0.0,
  "max_precision_drop_with_distractors": 0.15,
  "paraphrase_scoring": true,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 4,
  "predicted_count_plain": 9,
  "predicted_count_distracted": 9,
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
  "claim_precision": 0.6,
  "claim_precision_distracted": 0.6,
  "precision_drop_with_distractors": 0.0,
  "max_precision_drop_with_distractors": 0.15,
  "paraphrase_scoring": true,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 4,
  "predicted_count_plain": 10,
  "predicted_count_distracted": 10,
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
  "predicted_count_plain": 16,
  "predicted_count_distracted": 15,
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
  "claim_recall": 0.75,
  "claim_precision": 0.15384615384615385,
  "claim_precision_distracted": 0.0,
  "precision_drop_with_distractors": 0.15384615384615385,
  "max_precision_drop_with_distractors": 0.15,
  "paraphrase_scoring": true,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 4,
  "predicted_count_plain": 26,
  "predicted_count_distracted": 1,
  "matched_claim_ids": [
    "yolov3_three_scale_predictions",
    "yolov3_logistic_per_class",
    "yolov3_strict_iou_underperform_negative"
  ],
  "missing_claim_ids": [
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
  "claim_recall": 0.75,
  "claim_precision": 0.4090909090909091,
  "claim_precision_distracted": 0.0,
  "precision_drop_with_distractors": 0.4090909090909091,
  "max_precision_drop_with_distractors": 0.15,
  "paraphrase_scoring": true,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 4,
  "predicted_count_plain": 22,
  "predicted_count_distracted": 1,
  "matched_claim_ids": [
    "yolox_decoupled_head",
    "yolox_anchor_free_simota",
    "yolox_l_50ap_v100_speed"
  ],
  "missing_claim_ids": [
    "yolox_coupled_head_conflict_negative"
  ],
  "min_claim_recall": 0.55
}
```
