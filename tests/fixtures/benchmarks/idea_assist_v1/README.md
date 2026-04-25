# Idea-assist live — Layer 6 gold pack (Phase 5)

Created in **Phase 5** of `Corpus Gold Pack v1` (see `docs/analysis/corpus-gold-pack-v1-2026-04-25.md`).
Targets `BT10` (idea-assist quality on real corpus).

## Layout

```
idea_assist_v1/
├── README.md                                                ← this file
├── case_tiers.json                                          ← tier `idea_assist_live_pilot`
├── live_01_low_light_detector/{scenario.json, gold.json}
├── live_02_aerial_small_objects/...
├── live_03_medical_imaging_few_shot/...
└── live_04_realtime_video_streaming_anchor_free/...
```

Schema: `docs/specs/benchmark-gold-schemas-v1.md` §7.1.

## Why this pack exists

There were no live idea-assist fixtures in v0/v1; the runner had nothing to grade against beyond contract shape. Phase 5 introduces 4 live cases that exercise the idea-assist agent on real research-extension scenarios using the **same claim_ids that already exist in the Phase 2 claims gold pack** (`tests/fixtures/benchmarks/claims/`).

## Anti-phantom mechanics

1. **`supporting_claim_id_pool` references real claim_ids** from `claims/corpus_*_v2/gold.json` (single source of truth — 85 claim_ids in pool). Validation script verifies every id in `supporting_claim_id_pool` actually exists in claims gold; `supporting_claim_ids_min: 2` ensures the runner cites at least two corpus claims.
2. **`forbidden_substrings`** — verbatim phrases lifted from the corresponding paper articles. The agent must paraphrase, not copy. (Otherwise we get a "phantom-green idea" — a regurgitation of the paper abstract.)
3. **`max_rouge_l_against_evidence_quotes: 0.7`** — caps lexical overlap against the evidence quotes of supporting claims; forces real synthesis.
4. **`novelty_must_reference_gap: true`** — the proposed idea must address a gap explicit in at least one negative-polarity supporting claim (e.g. `yolov1_localization_error_negative`).

## Cases

| case_id                                           | seed_topic (short)                                                             | pool size | required gap-claim (negative polarity) |
|---------------------------------------------------|---------------------------------------------------------------------------------|-----------|----------------------------------------|
| live_01_low_light_detector                        | Real-time detector under low-light, 30+ FPS                                     | 5         | yolov1_localization_error_negative, yolov3_strict_iou_underperform_negative |
| live_02_aerial_small_objects                      | Detect <16 px vehicles in aerial imagery                                        | 5         | fpn_single_scale_small_objects_negative, dino_earlier_detr_slow_small_obj_negative, detr_small_obj_slow_train_negative |
| live_03_medical_imaging_few_shot                  | Adapt detector to colonoscopy with <200 annotated examples                      | 5         | mask_rcnn_pretraining_dependency_negative, rcnn_inference_2k_proposals_slow_negative |
| live_04_realtime_video_streaming_anchor_free      | Anchor-free detector exploiting temporal coherence in video                     | 5         | fcos_anchor_hyperparameter_burden_negative |

20 supporting_claim_id_pool entries across 4 cases (some overlap intentional — `yolov1_speed_45_155_fps`, `retinanet_focal_loss_definition`, `yolox_l_50ap_v100_speed` reused across topics).

## Metrics (target for BT10 runner — out of scope Phase 5)

```
supporting_claim_recall  : returned supporting_claim_ids ⊇ supporting_claim_ids_min ids from pool
forbidden_substring_count: = 0 in the generated hypothesis (gate)
rouge_l_against_evidence : ≤ max_rouge_l_against_evidence_quotes (= 0.7) (gate)
novelty_gap_referenced   : true if the generated hypothesis cites at least one negative-polarity supporting claim (advisory; LLM-judge in Phase 6)
```

A `reference_hypothesis_optional` is provided per case to anchor the LLM-judge in Phase 6 — it is **not** a target the runner must match (otherwise we regress to canned-answer phantom green).

## Validation status

- `meta.validation_status` = `draft` for all 4 cases.
- `meta.extractor_pass` = `single_human_authored_2026-04-25`.
- All `supporting_claim_id_pool` entries cross-validated against `tests/fixtures/benchmarks/claims/{corpus_*_v2,holdout_*_v1}/gold.json::expected_claims[].claim_id` (85 known ids).
- Phase 6 (LLM dual-validation) will spot-check `forbidden_substrings` (whether they truly appear in source articles) and `reference_hypothesis_optional` plausibility.
