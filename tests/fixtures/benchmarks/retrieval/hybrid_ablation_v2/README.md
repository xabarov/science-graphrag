# Hybrid ablation v2 — Layer 3 gold pack

Created in **Phase 4** of `Corpus Gold Pack v1` (see `docs/analysis/corpus-gold-pack-v1-2026-04-25.md`).
Targets `BT4` (hybrid-vs-vector retrieval ablation, replacing the v1 fully-synthetic benchmark).

## Layout

```
hybrid_ablation_v2/
├── README.md                                  ← this file
├── case_tiers.json                            ← tier `hybrid_ablation_v2_pilot`
├── ha_anchor_free/{question.txt, gold.json}
├── ha_focal_loss/...
├── ha_set_prediction_transformer/...
├── ha_compound_scaling/...
├── ha_keypoint_corner/...
├── ha_classical_handcrafted/...
├── ha_two_stage_rpn_evolution/...
└── ha_iou_loss_quality/...
```

Schema: `docs/specs/benchmark-gold-schemas-v1.md` §4.1.

## Why v2 (and what was wrong with v1)

The v1 hybrid_ablation pack (`tests/fixtures/benchmarks/retrieval/hybrid_ablation/`) was **phantom-green by construction**:

- Every v1 case carried hardcoded `vector_ranked_work_ids` and `hybrid_ranked_work_ids` arrays with synthetic ids (`rel_alpha`, `rel_beta`, `noise_doc`).
- The runner just compared the two precomputed lists — no actual Qdrant / BM25 query was ever executed.
- The ablation passed for any value of the search engine, including a search engine that did nothing.

Phase 4 fixes this with:

1. **No `vector_ranked_work_ids` / `hybrid_ranked_work_ids` in gold.** v2 schema (`schema_version: 2`) bans these keys; runner must produce them live by querying the seeded corpus.
2. `ranked_lists_source: "runner_generated"` is required in every case.
3. `relevant_corpus_work_ids` and `irrelevant_corpus_work_ids` are real-corpus ids from `tests/fixtures/benchmarks/layer1/<slug>/`.
4. Each case targets a topic where **keyword (BM25) signal should help over pure vector** (rare technical phrases, named architectures, specific loss formulations) — so a real `min_mrr_delta_hybrid_minus_vector ≥ 0.05` is a meaningful test.

## Cases

| case_id                          | topic                                                  | relevant (count) | irrelevant (count) |
|----------------------------------|--------------------------------------------------------|------------------|--------------------|
| ha_anchor_free                   | anchor-free dense detection                            | 4                | 3                  |
| ha_focal_loss                    | focal loss for class imbalance                         | 2                | 3                  |
| ha_set_prediction_transformer    | DETR-family set prediction with transformer           | 5                | 3                  |
| ha_compound_scaling              | compound depth/width/resolution scaling               | 1                | 4                  |
| ha_keypoint_corner               | keypoint-based detection (corners / centers)           | 2                | 4                  |
| ha_classical_handcrafted         | pre-deep classical detectors (HOG, DPM)                | 2                | 4                  |
| ha_two_stage_rpn_evolution       | Faster R-CNN / R-FCN style RPN training                | 3                | 4                  |
| ha_iou_loss_quality              | IoU/GIoU loss + quality-aware classification           | 3                | 3                  |

8 cases, 22 relevant + 28 irrelevant ids = 50 ground-truth labels.
Topics are deliberately chosen so that BM25 keyword match (e.g. "focal loss", "Selective Search", "compound scaling") should give hybrid an MRR edge over a pure dense embedding retriever.

## Metrics (target for BT4 runner)

```
mrr@10_vector  = MRR over runner.vector_ranked_work_ids @ k_for_mrr=10
mrr@10_hybrid  = MRR over runner.hybrid_ranked_work_ids @ k_for_mrr=10
delta          = mrr@10_hybrid − mrr@10_vector
gate           : delta ≥ min_mrr_delta_hybrid_minus_vector (= 0.05)
```

`runner_modes` in each gold = `["vector", "hybrid"]` — runner must produce both ranked lists.

The BT4 runner itself is **not** part of Phase 4 — only the gold data is in scope here.

## Validation status

- `meta.validation_status` = `draft` for all 8 cases.
- `meta.extractor_pass` = `single_human_authored_2026-04-25`.
- 0 cases contain `vector_ranked_work_ids` or `hybrid_ranked_work_ids` (validated by Phase 4 validation script — phantom-green leak gate).
- All `corpus_work_id` references resolve to `tests/fixtures/benchmarks/layer1/<slug>/`.
- Relevant ∩ irrelevant = ∅ in every case.
