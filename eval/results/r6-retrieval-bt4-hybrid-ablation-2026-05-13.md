# Hybrid ablation retrieval benchmark (BT4, advisory)

Cases: 8

Model: mistralai/mistral-small-3.2-24b-instruct
Layer-1 prompt fingerprint: sha256-20:210f7e16d3e0a07ad571
Semantic prompt fingerprint: sha256-20:19c459f1df53094b0a19

## ha_anchor_free — FAIL

```json
{
  "passed": false,
  "mrr_vector": 0.0,
  "mrr_hybrid": 0.0,
  "mrr_delta": 0.0,
  "mrr_delta_per_mode": {
    "vector": 0.0,
    "hybrid": 0.0
  },
  "hybrid_regression": false,
  "min_mrr_delta_hybrid_minus_vector": 0.05,
  "mrr_k": 10,
  "relevant_count": 4,
  "vector_hit_count": 5,
  "hybrid_hit_count": 5,
  "uuid_aware_mode": true
}
```


---

## ha_classical_handcrafted — FAIL

```json
{
  "passed": false,
  "mrr_vector": 0.0,
  "mrr_hybrid": 0.0,
  "mrr_delta": 0.0,
  "mrr_delta_per_mode": {
    "vector": 0.0,
    "hybrid": 0.0
  },
  "hybrid_regression": false,
  "min_mrr_delta_hybrid_minus_vector": 0.05,
  "mrr_k": 10,
  "relevant_count": 2,
  "vector_hit_count": 5,
  "hybrid_hit_count": 5,
  "uuid_aware_mode": true
}
```


---

## ha_compound_scaling — FAIL

```json
{
  "passed": false,
  "mrr_vector": 0.0,
  "mrr_hybrid": 0.0,
  "mrr_delta": 0.0,
  "mrr_delta_per_mode": {
    "vector": 0.0,
    "hybrid": 0.0
  },
  "hybrid_regression": false,
  "min_mrr_delta_hybrid_minus_vector": 0.05,
  "mrr_k": 10,
  "relevant_count": 1,
  "vector_hit_count": 5,
  "hybrid_hit_count": 5,
  "uuid_aware_mode": true
}
```


---

## ha_focal_loss — FAIL

```json
{
  "passed": false,
  "mrr_vector": 0.0,
  "mrr_hybrid": 0.0,
  "mrr_delta": 0.0,
  "mrr_delta_per_mode": {
    "vector": 0.0,
    "hybrid": 0.0
  },
  "hybrid_regression": false,
  "min_mrr_delta_hybrid_minus_vector": 0.05,
  "mrr_k": 10,
  "relevant_count": 2,
  "vector_hit_count": 5,
  "hybrid_hit_count": 5,
  "uuid_aware_mode": true
}
```


---

## ha_iou_loss_quality — FAIL

```json
{
  "passed": false,
  "mrr_vector": 0.0,
  "mrr_hybrid": 0.0,
  "mrr_delta": 0.0,
  "mrr_delta_per_mode": {
    "vector": 0.0,
    "hybrid": 0.0
  },
  "hybrid_regression": false,
  "min_mrr_delta_hybrid_minus_vector": 0.05,
  "mrr_k": 10,
  "relevant_count": 3,
  "vector_hit_count": 5,
  "hybrid_hit_count": 5,
  "uuid_aware_mode": true
}
```


---

## ha_keypoint_corner — FAIL

```json
{
  "passed": false,
  "mrr_vector": 0.0,
  "mrr_hybrid": 0.0,
  "mrr_delta": 0.0,
  "mrr_delta_per_mode": {
    "vector": 0.0,
    "hybrid": 0.0
  },
  "hybrid_regression": false,
  "min_mrr_delta_hybrid_minus_vector": 0.05,
  "mrr_k": 10,
  "relevant_count": 2,
  "vector_hit_count": 5,
  "hybrid_hit_count": 5,
  "uuid_aware_mode": true
}
```


---

## ha_set_prediction_transformer — FAIL

```json
{
  "passed": false,
  "mrr_vector": 0.0,
  "mrr_hybrid": 0.0,
  "mrr_delta": 0.0,
  "mrr_delta_per_mode": {
    "vector": 0.0,
    "hybrid": 0.0
  },
  "hybrid_regression": false,
  "min_mrr_delta_hybrid_minus_vector": 0.05,
  "mrr_k": 10,
  "relevant_count": 5,
  "vector_hit_count": 5,
  "hybrid_hit_count": 5,
  "uuid_aware_mode": true
}
```


---

## ha_two_stage_rpn_evolution — FAIL

```json
{
  "passed": false,
  "mrr_vector": 0.0,
  "mrr_hybrid": 0.0,
  "mrr_delta": 0.0,
  "mrr_delta_per_mode": {
    "vector": 0.0,
    "hybrid": 0.0
  },
  "hybrid_regression": false,
  "min_mrr_delta_hybrid_minus_vector": 0.05,
  "mrr_k": 10,
  "relevant_count": 3,
  "vector_hit_count": 5,
  "hybrid_hit_count": 5,
  "uuid_aware_mode": true
}
```
