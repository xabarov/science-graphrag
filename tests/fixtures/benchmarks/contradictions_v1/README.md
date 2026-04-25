# Contradictions v1 — Layer 9 gold pack

Created in **Phase 3** of `Corpus Gold Pack v1` (see `docs/analysis/corpus-gold-pack-v1-2026-04-25.md`).
Targets `BT12` (Contradictions runner / `:CONTRADICTS` graph relation extraction).

## Layout

```
contradictions_v1/
├── README.md                                   ← this file
├── pair_01_faster_rcnn_vs_retinanet_focal/gold.json
├── pair_02_faster_rcnn_vs_fcos/gold.json
├── pair_03_faster_rcnn_vs_cornernet/gold.json
├── pair_04_faster_rcnn_vs_detr/gold.json
├── pair_05_rcnn_vs_faster_rcnn/gold.json
├── pair_06_hog_human_detection_vs_rcnn/gold.json
└── pair_07_retinanet_focal_vs_efficientdet/gold.json
```

Schema: `docs/specs/benchmark-gold-schemas-v1.md` §10.1.

## Coverage matrix

| pair | type            | severity | claim_a (work)             | claim_b (work)               |
|------|-----------------|----------|----------------------------|------------------------------|
| c01  | era_shift       | nuanced  | faster_rcnn_realpdf        | retinanet_focal_realpdf      |
| c02  | design_paradigm | direct   | faster_rcnn_realpdf        | fcos_realpdf                 |
| c03  | design_paradigm | direct   | faster_rcnn_realpdf        | cornernet_realpdf            |
| c04  | post_processing | direct   | faster_rcnn_realpdf        | detr_realpdf                 |
| c05  | architectural   | nuanced  | rcnn_realpdf               | faster_rcnn_realpdf          |
| c06  | classical_vs_deep | direct | hog_human_detection_realpdf | rcnn_realpdf                |
| c07  | scaling         | nuanced  | retinanet_focal_realpdf    | efficientdet_realpdf         |

All six allowed `contradiction_type` values from §10.1 are covered (`era_shift`, `design_paradigm`, `post_processing`, `architectural`, `scaling`, `classical_vs_deep`).
Both severity levels are present (`direct` × 4, `nuanced` × 3).

## Cross-references

- All `corpus_work_id` values in `claim_a` / `claim_b` resolve to `tests/fixtures/benchmarks/layer1/<slug>/article.md`.
- Each pair carries an `expected_neo4j_pattern` hint that BT12 runner / persistence layer should produce.
- The set of pairs mirrors the 7 `contradicts` edges in `tests/fixtures/corpus/relations_v1.json` (Phase 1 output) — Phase 3 expands those edges into full case files with direct quotations from both papers.

## Validation status

- `meta.validation_status`: `draft` for all 7 pairs.
- `meta.needs_human_review`: `true`.
- `meta.extractor_pass`: `single_human_authored_2026-04-25` (single pass; Phase 6 will add LLM dual-validation).
- All evidence quotes are taken verbatim from the corresponding `article.md` (prepared during Layer 1 of `Corpus Gold Pack v1`).

## Acceptance for BT12 runner (downstream)

From `docs/analysis/corpus-gold-pack-v1-2026-04-25.md` §5 Phase 3:

```
contradiction_pair_recall ≥ 0.6  (advisory, not gate)
neo4j_persistence_check  : every found pair must materialise as :CONTRADICTS edge in Neo4j
false_positive_subtype   : ≤ 1 misclassified subtype across all 7 pairs
```

The runner itself (BT12) is **not** part of Phase 3 — only the gold data is in scope here.
