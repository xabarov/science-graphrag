# Claims benchmark suite

Cases: 10

Model: mistralai/mistral-small-3.2-24b-instruct
Layer-1 prompt fingerprint: sha256-20:210f7e16d3e0a07ad571
Semantic prompt fingerprint: sha256-20:19c459f1df53094b0a19

## corpus_cascade_rcnn_stages — PASS

```json
{
  "contract_only": false,
  "contract_passed": true,
  "passed": true,
  "claim_recall": 1.0,
  "claim_precision": 0.5,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 1,
  "predicted_count": 2,
  "matched_claim_ids": [
    "od_corpus_cascade_rcnn_increasing_iou_stages"
  ],
  "missing_claim_ids": [],
  "min_claim_recall": 1.0
}
```


---

## corpus_centernet_triplet — PASS

```json
{
  "contract_only": false,
  "contract_passed": true,
  "passed": true,
  "claim_recall": 1.0,
  "claim_precision": 0.5,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 1,
  "predicted_count": 2,
  "matched_claim_ids": [
    "od_corpus_centernet_triplet_keypoints"
  ],
  "missing_claim_ids": [],
  "min_claim_recall": 1.0
}
```


---

## corpus_cornernet_keypoints — PASS

```json
{
  "contract_only": false,
  "contract_passed": true,
  "passed": true,
  "claim_recall": 1.0,
  "claim_precision": 0.3333333333333333,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 1,
  "predicted_count": 3,
  "matched_claim_ids": [
    "od_corpus_cornernet_paired_keypoints"
  ],
  "missing_claim_ids": [],
  "min_claim_recall": 1.0
}
```


---

## corpus_detr_set_prediction — PASS

```json
{
  "contract_only": false,
  "contract_passed": true,
  "passed": true,
  "claim_recall": 1.0,
  "claim_precision": 0.2,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 1,
  "predicted_count": 5,
  "matched_claim_ids": [
    "od_corpus_detr_set_prediction_pipeline"
  ],
  "missing_claim_ids": [],
  "min_claim_recall": 1.0
}
```


---

## corpus_efficientdet_compound — PASS

```json
{
  "contract_only": false,
  "contract_passed": true,
  "passed": true,
  "claim_recall": 1.0,
  "claim_precision": 0.5,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 1,
  "predicted_count": 2,
  "matched_claim_ids": [
    "od_corpus_efficientdet_compound_scaling"
  ],
  "missing_claim_ids": [],
  "min_claim_recall": 1.0
}
```


---

## corpus_faster_rcnn_rpn_shared — PASS

```json
{
  "contract_only": false,
  "contract_passed": true,
  "passed": true,
  "claim_recall": 1.0,
  "claim_precision": 0.5,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 1,
  "predicted_count": 2,
  "matched_claim_ids": [
    "od_corpus_faster_rcnn_rpn_shared_features"
  ],
  "missing_claim_ids": [],
  "min_claim_recall": 1.0
}
```


---

## corpus_fpn_multiscale — PASS

```json
{
  "contract_only": false,
  "contract_passed": true,
  "passed": true,
  "claim_recall": 1.0,
  "claim_precision": 0.3333333333333333,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 1,
  "predicted_count": 3,
  "matched_claim_ids": [
    "od_corpus_fpn_multiscale_feature_pyramid"
  ],
  "missing_claim_ids": [],
  "min_claim_recall": 1.0
}
```


---

## corpus_mask_rcnn_mask_branch — PASS

```json
{
  "contract_only": false,
  "contract_passed": true,
  "passed": true,
  "claim_recall": 1.0,
  "claim_precision": 1.0,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 1,
  "predicted_count": 1,
  "matched_claim_ids": [
    "od_corpus_mask_rcnn_parallel_mask_branch"
  ],
  "missing_claim_ids": [],
  "min_claim_recall": 1.0
}
```


---

## corpus_retinanet_focal_imbalance — PASS

```json
{
  "contract_only": false,
  "contract_passed": true,
  "passed": true,
  "claim_recall": 1.0,
  "claim_precision": 0.3333333333333333,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 1,
  "predicted_count": 3,
  "matched_claim_ids": [
    "od_corpus_retinanet_class_imbalance"
  ],
  "missing_claim_ids": [],
  "min_claim_recall": 1.0
}
```


---

## corpus_ssd_single_network — PASS

```json
{
  "contract_only": false,
  "contract_passed": true,
  "passed": true,
  "claim_recall": 1.0,
  "claim_precision": 0.25,
  "claim_match_mode": "claim_id_or_normalized_text",
  "expected_count": 1,
  "predicted_count": 4,
  "matched_claim_ids": [
    "od_corpus_ssd_single_network"
  ],
  "missing_claim_ids": [],
  "min_claim_recall": 1.0
}
```
