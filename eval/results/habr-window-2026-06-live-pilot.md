# Claims paraphrase benchmark (BT6)

Cases: 15

Model: mistralai/mistral-small-3.2-24b-instruct
Layer-1 prompt fingerprint: sha256-20:210f7e16d3e0a07ad571
Semantic prompt fingerprint: sha256-20:19c459f1df53094b0a19

## corpus_cascade_rcnn_v2 — PASS

```json
{
  "contract_only": false,
  "contract_passed": true,
  "passed": true,
  "claim_recall": 0.6666666666666666,
  "claim_precision": 0.25,
  "claim_precision_distracted": 0.2727272727272727,
  "precision_drop_with_distractors": 0.0,
  "max_precision_drop_with_distractors": 0.15,
  "paraphrase_scoring": true,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 3,
  "predicted_count_plain": 12,
  "predicted_count_distracted": 11,
  "matched_claim_ids": [
    "cascade_rcnn_iou_progression",
    "cascade_rcnn_ap_gain_2_4"
  ],
  "missing_claim_ids": [
    "cascade_rcnn_quality_paradox_negative"
  ],
  "min_claim_recall": 0.55
}
```


---

## corpus_centernet_v2 — FAIL

```json
{
  "contract_only": false,
  "contract_passed": true,
  "passed": false,
  "claim_recall": 0.5,
  "claim_precision": 0.3,
  "claim_precision_distracted": 0.2222222222222222,
  "precision_drop_with_distractors": 0.07777777777777778,
  "max_precision_drop_with_distractors": 0.15,
  "paraphrase_scoring": true,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 4,
  "predicted_count_plain": 10,
  "predicted_count_distracted": 9,
  "matched_claim_ids": [
    "centernet_triplet_keypoints",
    "centernet_47_ap_coco"
  ],
  "missing_claim_ids": [
    "centernet_center_pooling_filter",
    "centernet_cornernet_false_pairs_negative"
  ],
  "min_claim_recall": 0.55
}
```


---

## corpus_cornernet_v2 — FAIL

```json
{
  "contract_only": false,
  "contract_passed": true,
  "passed": false,
  "claim_recall": 0.3333333333333333,
  "claim_precision": 0.09090909090909091,
  "claim_precision_distracted": 0.125,
  "precision_drop_with_distractors": 0.0,
  "max_precision_drop_with_distractors": 0.15,
  "paraphrase_scoring": true,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 3,
  "predicted_count_plain": 11,
  "predicted_count_distracted": 16,
  "matched_claim_ids": [
    "cornernet_paired_keypoints"
  ],
  "missing_claim_ids": [
    "cornernet_hourglass_backbone",
    "cornernet_anchor_design_drawbacks_negative"
  ],
  "min_claim_recall": 0.55
}
```


---

## corpus_detr_v2 — FAIL

```json
{
  "contract_only": false,
  "contract_passed": true,
  "passed": false,
  "claim_recall": 0.5,
  "claim_precision": 0.3125,
  "claim_precision_distracted": 0.3125,
  "precision_drop_with_distractors": 0.0,
  "max_precision_drop_with_distractors": 0.15,
  "paraphrase_scoring": true,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 4,
  "predicted_count_plain": 16,
  "predicted_count_distracted": 16,
  "matched_claim_ids": [
    "detr_set_prediction_pipeline",
    "detr_match_faster_rcnn_large_obj"
  ],
  "missing_claim_ids": [
    "detr_bipartite_matching_no_nms",
    "detr_small_obj_slow_train_negative"
  ],
  "min_claim_recall": 0.55
}
```


---

## corpus_efficientdet_v2 — FAIL

```json
{
  "contract_only": false,
  "contract_passed": true,
  "passed": false,
  "claim_recall": 0.2,
  "claim_precision": 0.75,
  "claim_precision_distracted": 0.8181818181818182,
  "precision_drop_with_distractors": 0.0,
  "max_precision_drop_with_distractors": 0.15,
  "paraphrase_scoring": true,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 5,
  "predicted_count_plain": 12,
  "predicted_count_distracted": 11,
  "matched_claim_ids": [
    "efficientdet_d7_55_ap_efficient"
  ],
  "missing_claim_ids": [
    "efficientdet_bifpn_weighted",
    "efficientdet_compound_scaling",
    "efficientdet_single_dim_scaling_negative",
    "efficientdet_throughput_tradeoff_negative"
  ],
  "min_claim_recall": 0.55
}
```


---

## corpus_fast_rcnn_v2 — FAIL

```json
{
  "contract_only": false,
  "contract_passed": true,
  "passed": false,
  "claim_recall": 0.25,
  "claim_precision": 0.047619047619047616,
  "claim_precision_distracted": 0.19047619047619047,
  "precision_drop_with_distractors": 0.0,
  "max_precision_drop_with_distractors": 0.15,
  "paraphrase_scoring": true,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 4,
  "predicted_count_plain": 21,
  "predicted_count_distracted": 21,
  "matched_claim_ids": [
    "fast_rcnn_9x_train_speedup"
  ],
  "missing_claim_ids": [
    "fast_rcnn_single_stage_multitask",
    "fast_rcnn_roi_pooling_shared_features",
    "fast_rcnn_rcnn_redundancy_negative"
  ],
  "min_claim_recall": 0.55
}
```


---

## corpus_faster_rcnn_v2 — FAIL

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
  "expected_count": 4,
  "predicted_count_plain": 9,
  "predicted_count_distracted": 15,
  "matched_claim_ids": [],
  "missing_claim_ids": [
    "faster_rcnn_rpn_shared_features",
    "faster_rcnn_speed_5fps_sota",
    "faster_rcnn_anchor_boxes",
    "faster_rcnn_selective_search_bottleneck"
  ],
  "min_claim_recall": 0.55
}
```


---

## corpus_fcos_v2 — FAIL

```json
{
  "contract_only": false,
  "contract_passed": true,
  "passed": false,
  "claim_recall": 0.5,
  "claim_precision": 0.17647058823529413,
  "claim_precision_distracted": 0.125,
  "precision_drop_with_distractors": 0.05147058823529413,
  "max_precision_drop_with_distractors": 0.15,
  "paraphrase_scoring": true,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 4,
  "predicted_count_plain": 17,
  "predicted_count_distracted": 16,
  "matched_claim_ids": [
    "fcos_per_pixel_prediction",
    "fcos_surpass_retinanet_no_anchors"
  ],
  "missing_claim_ids": [
    "fcos_centerness_branch",
    "fcos_anchor_hyperparameter_burden_negative"
  ],
  "min_claim_recall": 0.55
}
```


---

## corpus_fpn_v2 — FAIL

```json
{
  "contract_only": false,
  "contract_passed": true,
  "passed": false,
  "claim_recall": 0.5,
  "claim_precision": 0.2222222222222222,
  "claim_precision_distracted": 0.25,
  "precision_drop_with_distractors": 0.0,
  "max_precision_drop_with_distractors": 0.15,
  "paraphrase_scoring": true,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 4,
  "predicted_count_plain": 9,
  "predicted_count_distracted": 8,
  "matched_claim_ids": [
    "fpn_topdown_lateral_pyramid",
    "fpn_faster_rcnn_ap_gain"
  ],
  "missing_claim_ids": [
    "fpn_lateral_connections_role",
    "fpn_single_scale_small_objects_negative"
  ],
  "min_claim_recall": 0.55
}
```


---

## corpus_mask_rcnn_v2 — FAIL

```json
{
  "contract_only": false,
  "contract_passed": true,
  "passed": false,
  "claim_recall": 0.4,
  "claim_precision": 0.2777777777777778,
  "claim_precision_distracted": 0.3125,
  "precision_drop_with_distractors": 0.0,
  "max_precision_drop_with_distractors": 0.15,
  "paraphrase_scoring": true,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 5,
  "predicted_count_plain": 18,
  "predicted_count_distracted": 16,
  "matched_claim_ids": [
    "mask_rcnn_parallel_mask_branch",
    "mask_rcnn_roialign_quantization_fix"
  ],
  "missing_claim_ids": [
    "mask_rcnn_decoupled_per_class_sigmoid",
    "mask_rcnn_softmax_mask_competition_negative",
    "mask_rcnn_pretraining_dependency_negative"
  ],
  "min_claim_recall": 0.55
}
```


---

## corpus_rcnn_v2 — PASS

```json
{
  "contract_only": false,
  "contract_passed": true,
  "passed": true,
  "claim_recall": 0.75,
  "claim_precision": 0.29411764705882354,
  "claim_precision_distracted": 0.17857142857142858,
  "precision_drop_with_distractors": 0.11554621848739496,
  "max_precision_drop_with_distractors": 0.15,
  "paraphrase_scoring": true,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 4,
  "predicted_count_plain": 17,
  "predicted_count_distracted": 28,
  "matched_claim_ids": [
    "rcnn_region_proposals_with_cnn_features",
    "rcnn_pretrain_finetune_recipe",
    "rcnn_voc_30pct_relative_gain"
  ],
  "missing_claim_ids": [
    "rcnn_inference_2k_proposals_slow_negative"
  ],
  "min_claim_recall": 0.55
}
```


---

## corpus_retinanet_focal_v2 — FAIL

```json
{
  "contract_only": false,
  "contract_passed": true,
  "passed": false,
  "claim_recall": 0.2,
  "claim_precision": 0.047619047619047616,
  "claim_precision_distracted": 0.09090909090909091,
  "precision_drop_with_distractors": 0.0,
  "max_precision_drop_with_distractors": 0.15,
  "paraphrase_scoring": true,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 5,
  "predicted_count_plain": 21,
  "predicted_count_distracted": 11,
  "matched_claim_ids": [
    "retinanet_focal_loss_definition"
  ],
  "missing_claim_ids": [
    "retinanet_hard_mining_insufficient",
    "retinanet_resnet101_fpn_ap",
    "retinanet_imbalance_root_cause",
    "retinanet_alpha_balanced_alone_negative"
  ],
  "min_claim_recall": 0.55
}
```


---

## corpus_ssd_v2 — PASS

```json
{
  "contract_only": false,
  "contract_passed": true,
  "passed": true,
  "claim_recall": 0.5,
  "claim_precision": 0.14285714285714285,
  "claim_precision_distracted": 0.2857142857142857,
  "precision_drop_with_distractors": 0.0,
  "max_precision_drop_with_distractors": 0.15,
  "paraphrase_scoring": true,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 4,
  "predicted_count_plain": 28,
  "predicted_count_distracted": 28,
  "matched_claim_ids": [
    "ssd_default_boxes_multiscale",
    "ssd_300_voc_speed"
  ],
  "missing_claim_ids": [
    "ssd_multiple_feature_maps",
    "ssd_yolo_localization_negative"
  ],
  "min_claim_recall": 0.22
}
```


---

## corpus_yolov1_v2 — PASS

```json
{
  "contract_only": false,
  "contract_passed": true,
  "passed": true,
  "claim_recall": 0.5,
  "claim_precision": 0.29411764705882354,
  "claim_precision_distracted": 0.2,
  "precision_drop_with_distractors": 0.09411764705882353,
  "max_precision_drop_with_distractors": 0.15,
  "paraphrase_scoring": true,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 6,
  "predicted_count_plain": 17,
  "predicted_count_distracted": 15,
  "matched_claim_ids": [
    "yolov1_unified_pipeline",
    "yolov1_speed_45_155_fps",
    "yolov1_localization_error_negative"
  ],
  "missing_claim_ids": [
    "yolov1_grid_based_detection",
    "yolov1_artwork_generalization",
    "yolov1_two_stage_higher_acc_negative"
  ],
  "min_claim_recall": 0.32
}
```


---

## corpus_yolov2_v2 — FAIL

```json
{
  "contract_only": false,
  "contract_passed": true,
  "passed": false,
  "claim_recall": 0.2,
  "claim_precision": 0.05555555555555555,
  "claim_precision_distracted": 0.04,
  "precision_drop_with_distractors": 0.015555555555555552,
  "max_precision_drop_with_distractors": 0.15,
  "paraphrase_scoring": true,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 5,
  "predicted_count_plain": 18,
  "predicted_count_distracted": 25,
  "matched_claim_ids": [
    "yolov2_batchnorm_dropout_replace"
  ],
  "missing_claim_ids": [
    "yolov2_dimension_priors_kmeans",
    "yolov2_yolo9000_joint_training",
    "yolov2_handpicked_anchors_negative",
    "yolov2_yolov1_coarse_grid_negative"
  ],
  "min_claim_recall": 0.55
}
```
