# Workspace-scoped retrieval live — Layer 2 gold pack

Created in **Phase 4** of `Corpus Gold Pack v1` (see `docs/analysis/corpus-gold-pack-v1-2026-04-25.md`).
Targets `BT2` (workspace-scoped retrieval, replacing the v1 single-paper / canned-answer benchmark).

## Layout

```
workspace_scoped_live/
├── README.md                                       ← this file
├── _workspaces.json                                ← 3 workspace definitions
├── case_tiers.json                                 ← tier `workspace_scoped_live_pilot`
├── ws_yolo_speed_question/{question.txt, gold.json}
├── ws_yolo_negative_mask_segmentation/...
├── ws_two_stage_proposal_evolution/...
├── ws_two_stage_negative_focal_loss/...
├── ws_full_anchor_free_overview/...
└── ws_full_corpus_negative_unrelated/...
```

Schema: `docs/specs/benchmark-gold-schemas-v1.md` §3.1 (workspaces) and §3.2 (case `gold.json`).

## Why v2 (and what was wrong with v1)

The v1 workspace pack (`tests/fixtures/benchmarks/retrieval/workspace_scoped/`) was **phantom-green**:

- All 4 v1 cases used a single workspace with a single paper (`yolov1`), so cross-paper isolation was never tested.
- Canned `answer_reference_text` was a substring of the paper's intro, so any retriever that returned the YOLO PDF and emitted the abstract would pass `rouge_l ≥ 0.18`.
- No `forbidden_corpus_work_ids` in v1 → workspace boundary leaks were undetectable.

Phase 4 fixes this with:

1. **3 distinct workspaces**, each non-trivial (`ws_yolo_family` 4 papers, `ws_two_stage` 7 papers, `ws_full_corpus` 35 papers).
2. **Both positive and negative cases per workspace**:
   - **positive** — multi-paper aggregation; expected citations from > 1 paper inside the workspace.
   - **negative** — question whose answer lives **outside** the workspace; runner must abstain or return empty.
3. **Strict `forbidden_corpus_work_ids`** with `forbidden_violation_gate: 0`. Validation enforces that every forbidden id is **outside** the workspace (otherwise the gate would be vacuous).

## Cases

| case_id                                  | workspace        | kind     | expected behaviour |
|------------------------------------------|------------------|----------|--------------------|
| ws_yolo_speed_question                   | ws_yolo_family   | positive | aggregate FPS across YOLO v1/v2/v3/X; ≥ 2 citations from inside ws |
| ws_yolo_negative_mask_segmentation       | ws_yolo_family   | negative | abstain — Mask R-CNN is OUT of ws |
| ws_two_stage_proposal_evolution          | ws_two_stage     | positive | trace RPN evolution across R-CNN / Fast R-CNN / Faster R-CNN |
| ws_two_stage_negative_focal_loss         | ws_two_stage     | negative | abstain — focal loss only in RetinaNet (OUT) |
| ws_full_anchor_free_overview             | ws_full_corpus   | positive | overview citing CornerNet / FCOS / ATSS / CenterNet |
| ws_full_corpus_negative_unrelated        | ws_full_corpus   | negative | abstain — BERT/LLM not in OD corpus |

3 positive + 3 negative; ratio 1:1 makes both recall (positive) and abstain-precision (negative) measurable.

## Workspaces

| workspace_id     | corpus_work_ids                                                                                                                          | size |
|------------------|------------------------------------------------------------------------------------------------------------------------------------------|------|
| ws_yolo_family   | yolov1, yolov2_realpdf, yolov3_realpdf, yolox_realpdf                                                                                    | 4    |
| ws_two_stage     | rcnn_realpdf, fast_rcnn_realpdf, faster_rcnn_realpdf, rfcn_realpdf, mask_rcnn_realpdf, cascade_rcnn_realpdf, libra_rcnn_realpdf          | 7    |
| ws_full_corpus   | `*` (all 35 papers in `tests/fixtures/benchmarks/layer1/`)                                                                                | 35   |

## Metrics (target for BT2 runner)

```
recall          (positive cases) — runner must return all `required: true` citations.
abstain_rate    (negative cases) — answer_metric.must_contain_any keyword present, expected_citations_min_count = 0.
forbidden_violation_count = 0   ← gate; ANY forbidden_corpus_work_id appearing in returned citations fails the case.
answer_rouge_l ≥ min_value      (positive cases only).
```

The BT2 runner itself is **not** part of Phase 4 — only the gold data is in scope here.

## Validation status

- `meta.validation_status` = `draft` for `_workspaces.json` and all 6 cases.
- `meta.extractor_pass` = `single_human_authored_2026-04-25`.
- All `corpus_work_id` references resolve to `tests/fixtures/benchmarks/layer1/<slug>/` directories.
- Phase 6 (LLM dual-validation) will spot-check `answer_reference_text` paraphrases.
