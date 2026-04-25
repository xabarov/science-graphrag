# Multihop retrieval v2 — Layer 4 gold pack

Created in **Phase 4** of `Corpus Gold Pack v1` (see `docs/analysis/corpus-gold-pack-v1-2026-04-25.md`).
Targets `BT3` (graph-traversal multihop retrieval, replacing the v1 N-hop neighbourhood benchmark).

## Layout

```
multihop_v2/
├── README.md                                            ← this file
├── case_tiers.json                                      ← tier `multihop_v2_pilot`
├── mh_proposal_evolution_chain/{question.txt, gold.json}
├── mh_yolo_lineage_chain/...
├── mh_detr_lineage_chain/...
├── mh_authors_yolo_intersect_rcnn_family/...
└── mh_datasets_shared_one_stage_detectors/...
```

Schema: `docs/specs/benchmark-gold-schemas-v1.md` §5.1.

## Why v2 (and what was wrong with v1)

The v1 multihop pack (`tests/fixtures/benchmarks/retrieval/multihop_v1/`) was **phantom-green when the infrastructure was down**:

- Every v1 case used a single `center_work_id` + `expected_neighbor_work_ids` shape.
- The runner exited cleanly with `infrastructure_skipped: true` whenever Neo4j was unreachable, and the test still reported `passed`.
- No checks that the actual `:CITES` / `:EXTENDS` traversal was executed.

Phase 4 fixes this with:

1. **`infrastructure_required: ["neo4j", ...]`** in every case — runner must hard-fail (not skip) when those services are missing.
2. Two question kinds: `ordered_chain` (multi-hop temporal evolution chains) and `unordered_set` (graph aggregation queries).
3. **All chains are anchored in `tests/fixtures/corpus/relations_v1.json`** (Phase 1 output) — every adjacent chain pair has an `extends` and/or `cites` edge in the relations file. Runner failures therefore can't be blamed on missing ground-truth edges.

## Cases

### Ordered chains (3 cases)

| case_id                            | chain                                                                                | hops | edge types |
|------------------------------------|--------------------------------------------------------------------------------------|------|------------|
| mh_proposal_evolution_chain        | selective_search → rcnn → fast_rcnn → faster_rcnn → mask_rcnn                        | 4    | CITES + EXTENDS |
| mh_yolo_lineage_chain              | yolov1 → yolov2 → yolov3 → yolox                                                     | 3    | EXTENDS + CITES |
| mh_detr_lineage_chain              | detr → deformable_detr → dn_detr → dino                                              | 3    | EXTENDS + CITES |

Metric: `chain_order_correctness = LCS(returned_chain, expected_chain) / |expected_chain|`, gate `≥ 0.7..0.8`.

### Unordered sets (2 cases)

| case_id                                       | node_kind | expected canonical names           | min_recall | min_precision |
|-----------------------------------------------|-----------|------------------------------------|------------|---------------|
| mh_authors_yolo_intersect_rcnn_family         | Author    | Ross Girshick, Ali Farhadi          | 0.5        | 0.6           |
| mh_datasets_shared_one_stage_detectors        | Dataset   | MS COCO, PASCAL VOC, ImageNet       | 0.6        | 0.6           |

Metric: standard `recall = |returned ∩ expected| / |expected|`, `precision = |returned ∩ expected| / |returned|`.

## Anchor in relations_v1.json

All 3 ordered chains were validated against `tests/fixtures/corpus/relations_v1.json`:

```
selective_search ↔ rcnn       : cites
rcnn             ↔ fast_rcnn  : cites + extends (fast_rcnn EXTENDS rcnn)
fast_rcnn        ↔ faster_rcnn: cites + extends + shares_author
faster_rcnn      ↔ mask_rcnn  : cites + extends (mask_rcnn EXTENDS faster_rcnn)

yolov1     ↔ yolov2: cites + extends + shares_author
yolov2     ↔ yolov3: cites + extends + shares_author
yolov3     ↔ yolox : cites + extends

detr             ↔ deformable_detr: cites + extends
deformable_detr  ↔ dn_detr        : cites
dn_detr          ↔ dino           : cites + extends + shares_author
```

Unordered cases use derived edges (`shares_author`, `shares_dataset` × 59 + 331 in relations_v1).

## Metrics (target for BT3 runner)

```
ordered_chain   : chain_order_correctness ≥ min_chain_order_correctness
unordered_set   : recall ≥ min_recall AND precision ≥ min_precision
neo4j_traversal_executed = true   ← gate; if infrastructure_required services unreachable, FAIL (not skip)
```

The BT3 runner itself is **not** part of Phase 4 — only the gold data is in scope here.

## Validation status

- `meta.validation_status` = `draft` for all 5 cases.
- `meta.extractor_pass` = `single_human_authored_2026-04-25`.
- All `corpus_work_id` references resolve to `tests/fixtures/benchmarks/layer1/<slug>/`.
- All chain adjacencies have at least one CITES or EXTENDS edge in `tests/fixtures/corpus/relations_v1.json`.
