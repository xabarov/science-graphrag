# Concept / Topic v2 — Layer 7 gold pack

Created in **Phase 3** of `Corpus Gold Pack v1` (see `docs/analysis/corpus-gold-pack-v1-2026-04-25.md`).
Targets `BT7` Path A (concept-extraction quality on real corpus, replacing the v1 substring-tautology benchmark).

## Layout

```
concept_topic/
├── README.md                          ← this file
├── concepts_frozen_v1.json            ← frozen list of 25 canonical concepts + aliases
├── corpus_yolov1_v2/gold.json
├── corpus_faster_rcnn_v2/gold.json
├── corpus_retinanet_focal_v2/gold.json
├── corpus_ssd_v2/gold.json
├── corpus_mask_rcnn_v2/gold.json
├── corpus_fpn_v2/gold.json
├── corpus_detr_v2/gold.json
├── corpus_cornernet_v2/gold.json
├── corpus_fcos_v2/gold.json
└── corpus_cascade_rcnn_v2/gold.json
```

Schemas: `docs/specs/benchmark-gold-schemas-v1.md` §8.1 (frozen list) and §8.2 (per-paper packs).

## Why v2 (and what was wrong with v1)

The v1 concept benchmark in `tests/fixtures/benchmarks/concept_v1/` was **phantom-green**:
the gold concept list was derived from the same heuristic the runner used to extract concepts,
so the runner was effectively grading itself. Phase 3 fixes this by:

1. **Frozen, hand-curated concept ontology** (`concepts_frozen_v1.json`, 25 concepts with aliases) — independent of any extractor.
2. **Both `present` and `absent` labels** — `present` measures recall, `absent` measures precision (false-positive concepts). v1 only had `present`, so a "return everything" extractor would score 1.0.
3. **Evidence quotes for `present`** (where verbatim text is available) and **rationale for `absent`** (why the concept does not apply).

## Frozen concept list (25)

Six families:

- **Proposal / pipeline:** `region_proposal`, `selective_search`, `roi_pooling`, `roi_align`, `mask_branch`
- **Stage type:** `one_stage_detector`, `two_stage_detector`, `anchor_based`, `anchor_free`, `set_prediction`, `keypoint_detection`, `centerness`
- **Backbones / multi-scale:** `backbone_resnet`, `backbone_darknet`, `feature_pyramid`, `compound_scaling`, `cascade_iou_progression`
- **Loss / post-proc:** `focal_loss`, `iou_loss`, `multi_task_loss`, `nms`
- **Architecture choice:** `transformer_decoder`
- **Classical / data:** `classical_dpm`, `handcrafted_features`, `coco_benchmark`

All 25 concepts are referenced by ≥ 1 pilot pack.

## Pilot coverage (10 papers)

| pack                              | corpus_work_id              | present | absent |
|-----------------------------------|-----------------------------|---------|--------|
| corpus_yolov1_v2                  | yolov1                      | 5       | 8      |
| corpus_faster_rcnn_v2             | faster_rcnn_realpdf         | 7       | 10     |
| corpus_retinanet_focal_v2         | retinanet_focal_realpdf     | 7       | 6      |
| corpus_ssd_v2                     | ssd_realpdf                 | 6       | 7      |
| corpus_mask_rcnn_v2               | mask_rcnn_realpdf           | 9       | 5      |
| corpus_fpn_v2                     | fpn_realpdf                 | 7       | 5      |
| corpus_detr_v2                    | detr_realpdf                | 6       | 11     |
| corpus_cornernet_v2               | cornernet_realpdf           | 5       | 7      |
| corpus_fcos_v2                    | fcos_realpdf                | 7       | 6      |
| corpus_cascade_rcnn_v2            | cascade_rcnn_realpdf        | 8       | 6      |
| **TOTAL**                         |                             | **67**  | **71** |

138 labels across 10 papers; ratio ≈ 1.06 absent : 1 present (good for both metrics).

## Metrics (target for BT7 Path A runner)

```
recall    = |concepts_present_returned ∩ concepts_present_gold| / |concepts_present_gold|
precision = 1 - |concepts_absent_gold ∩ concepts_returned| / |concepts_returned|
```

Realistic target band (per `corpus-gold-pack-v1-2026-04-25.md` §5 Phase 3):

```
recall    ∈ [0.50, 0.80]    ← anything ≥ 0.95 is suspicious (probably substring leak)
precision ∈ [0.70, 0.95]    ← anything = 1.00 is suspicious
```

The BT7 runner itself is **not** part of Phase 3 — only the gold data is in scope here.

## Validation status

- `meta.validation_status` = `draft` for all 10 packs and the frozen list.
- `meta.needs_human_review` = `true`.
- `meta.extractor_pass` = `single_human_authored_2026-04-25`.
- Phase 6 (LLM dual-validation) will add a second extractor pass and resolve disagreements.

## Notes on hard cases

- `cornernet_realpdf` and `fcos_realpdf` actually use a focal-loss-like formulation; in this draft they are conservatively listed under neither `present` nor `absent` (focal_loss). Phase 6 should adjudicate.
- `detr_realpdf` is interesting because it has no anchors and no NMS — both are listed as `absent` rather than as `anchor_free` `present`, since DETR uses learned object queries rather than the per-pixel anchor-free formulation pioneered by FCOS / CornerNet.
