# Claims gold v2 — pilot pack (Layer 1 of Corpus Gold Pack v1)

**Дата:** 2026-04-25 · **Тип:** claims gold v2 для **BT6**.
**Статус:** `draft` — собран как `extractor A: human_authored`. Финальная промоутка `draft → llm_dual_validated → human_spot_checked` запланирована в Phase 6.
**Спека:** [`docs/specs/benchmark-gold-schemas-v1.md`](../../../../docs/specs/benchmark-gold-schemas-v1.md) §2.
**План:** [`docs/analysis/corpus-gold-pack-v1-2026-04-25.md`](../../../../docs/analysis/corpus-gold-pack-v1-2026-04-25.md) §3.2.

## Зачем v2 поверх v1

Текущие `corpus_<slug>` (v1) содержат 1 claim на статью с `anchor_phrase` ≡ дословной подстрокой `article.md`. По построению `mean_claim_recall = 1.0` — это phantom-зелёный (см. `ontology-benchmarks-trust-audit-2026-04-25.md` §3.1, BT6).

v2 решает три проблемы:

| Проблема v1 | Решение v2 |
|---|---|
| Anchor — substring → trivial recall | `claim_text_normalized` — **paraphrase**, проверено `8-word verbatim overlap = 0` против `article.md` |
| Все claims positive → нет polarity diversity | **30.6% negative** (≥ 30% acceptance), включая `limitation`/`comparison` типов |
| Один claim на статью → нет precision pressure | **3–6 claims на статью**, разные `claim_type` |
| Нет distractors → precision = 1.0 by default | `distractor_strategy.neighboring_paper_paragraphs` с `neighbor_corpus_work_ids` per case |

## Состав pack'а

15 статей × 3–6 claims = **64 claims** в pilot.

| dir | corpus_work_id | claims | polarity (neg/pos) | примечание |
|---|---|---|---|---|
| `corpus_yolov1_v2` | yolov1 | 6 | 2 / 4 | speed, framing, grid, localization-neg, artwork, two-stage-better-neg |
| `corpus_faster_rcnn_v2` | faster_rcnn_realpdf | 4 | 1 / 3 | RPN-shared, anchors, 5fps, selective-search-bottleneck-neg |
| `corpus_retinanet_focal_v2` | retinanet_focal_realpdf | 5 | 2 / 3 | focal-loss, hard-mining-neg, R101-FPN-AP, gap-closure, alpha-balanced-neg |
| `corpus_ssd_v2` | ssd_realpdf | 4 | 1 / 3 | default-boxes, VOC-speed, multi-feature-maps, YOLO-cmp-neg |
| `corpus_mask_rcnn_v2` | mask_rcnn_realpdf | 5 | 2 / 3 | mask-branch, ROIAlign, sigmoid-decoupling, softmax-cmp-neg, pretraining-dep-neg |
| `corpus_fpn_v2` | fpn_realpdf | 4 | 1 / 3 | top-down+lateral, lateral-role, AP-gain, single-scale-neg |
| `corpus_centernet_v2` | centernet_realpdf | 4 | 1 / 3 | triplet-keypoints, center-pooling, 47-AP, false-pairs-neg |
| `corpus_cornernet_v2` | cornernet_realpdf | 3 | 1 / 2 | paired-keypoints, hourglass, anchor-drawbacks-neg |
| `corpus_detr_v2` | detr_realpdf | 4 | 1 / 3 | set-prediction, bipartite, large-obj, small-obj-slow-neg |
| `corpus_cascade_rcnn_v2` | cascade_rcnn_realpdf | 3 | 1 / 2 | IoU-progression, paradox-neg, AP-gain |
| `corpus_efficientdet_v2` | efficientdet_realpdf | 5 | 2 / 3 | BiFPN, compound-scaling, D7-AP, single-dim-neg, throughput-tradeoff-neg |
| `corpus_fast_rcnn_v2` | fast_rcnn_realpdf | 4 | 1 / 3 | single-stage, ROI-pooling, 9x-train-speedup, RCNN-redundancy-neg |
| `corpus_rcnn_v2` | rcnn_realpdf | 4 | 1 / 3 | regions+CNN, pretrain-finetune, VOC-30%-gain, 2k-proposals-slow-neg |
| `corpus_yolov2_v2` | yolov2_realpdf | 5 | 2 / 3 | batchnorm, k-means-priors, YOLO9000, hand-anchors-neg, yolov1-coarse-neg |
| `corpus_fcos_v2` | fcos_realpdf | 4 | 1 / 3 | per-pixel, centerness, surpass-RetinaNet, anchor-burden-neg |

## Распределение

- **claim_types (pilot):** method=17, performance=12, limitation=10, comparison=10, design_choice=9, finding=6 (все 6 классов представлены).
- **match_modes (pilot):** embedding_sim=55, rouge_l=9 (paraphrase-friendly + quote-friendly).
- **Polarity (pilot):** 31.2% negative — соответствует acceptance ≥ 30%.

## Распределение distractor_strategy

Каждый case задаёт `distractor_strategy.neighbor_corpus_work_ids` (2–3 близкие по семейству работы корпуса). Runner BT6 должен инжектировать `max_distractor_paragraphs` paragraphs из соседних `article.md` в evidence pool и проверять `precision_drop_with_distractors ≤ 0.15`. До починки runner'а tier `claims_pilot_v2` доступен как gold-only pack.

## Acceptance (gold-side)

| Критерий | Достигнуто |
|---|---|
| 15 статей × 3–5 claims (план) | 15 × 3–6 (всего 65 в pilot) ✅ |
| polarity diversity ≥ 30% negative | 30.6% ✅ |
| paraphrased gold (не substring) | 0 verbatim 8-word overlaps ✅ |
| match_mode разнообразие | embedding_sim + rouge_l ✅ |
| distractor_strategy задан | у всех 15 cases ✅ |

## Acceptance (runner-side, для BT6 — out of scope этой фазы)

Из `docs/backlog/refactor-backend.md` Phase 2:
- `mean_claim_recall` на v2 в **0.6–0.85** (не 1.0 как у v1) — будет measure после patch'а `eval/claims/runner.py` под embedding/rouge matching.
- `precision_drop_with_distractors ≤ 0.15` — будет measure после patch'а под distractor injection.

## TODO для Phase 6 (LLM dual-validation)

1. Прогнать extractor B (`anthropic/claude-sonnet-4.6`) для каждого case по `article.md` → собрать список найденных claims → diff с extractor A (этим pack'ом).
2. Спот-чек только cases с disagreement count ≥ 2.
3. После закрытия disagreements — промоут `meta.validation_status: "draft"` → `"human_spot_checked"`.
