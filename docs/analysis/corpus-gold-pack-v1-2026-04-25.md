# Corpus Gold Pack v1 — план benchmark-фикстур поверх 30+ статей (2026-04-25)

**Дата:** 2026-04-25
**Тип:** plan + spec (living doc до закрытия pack v1)
**Статус:** active
**Контекст:** [`ontology-benchmarks-trust-audit-2026-04-25.md`](ontology-benchmarks-trust-audit-2026-04-25.md) показал, что ~50% advisory-семейств зелёные «по построению»; почти каждое узкое место — это **отсутствие или слабость gold-фикстуры**, а не runner. Этот документ описывает, как заранее построить «золотой пакет» на базе уже подготовленного корпуса (35+ статей object-detection в `tests/fixtures/benchmarks/layer1/`), чтобы серия BT2..BT12 свелась к «инструментировать готовый gold», а не «исследовать домен на лету».
**Связь:** см. также `master-roadmap-and-refactor-plan-2026-04-25.md` (Track D), `ontology-benchmarks-roadmap-2026-04-24.md` (Wave M..T).

---

## 1. Что такое Corpus Gold Pack v1

Единая разметка **текущего** пилотного корпуса (35+ object-detection статей: R-CNN family, YOLO family, DETR family, single-stage detectors, исторические detectors) под потребности всей серии BT. Состоит из 9 связанных слоёв:

| # | Слой | Закрывает BT | Зависит от |
|---|------|-------------|------------|
| 0 | **Catalog** — единый каталог статей корпуса | фундамент для всех BT | — |
| 1 | **Claims gold v2 + holdout** | BT6 | 0 |
| 2 | **Workspace-scoped retrieval live** | BT2 | 0 |
| 3 | **Hybrid ablation v2** (gold = `relevant_work_ids`, ranked строит runner) | BT4 | 0 |
| 4 | **Multihop v2** (graph-traversal вопросы) | BT3 | 0 |
| 5 | **Agent-tools live** + **Multi-agent** | BT8, BT9 | 0, 4 |
| 6 | **Idea-assist live** | BT10 | 0, 1 |
| 7 | **Concept/Topic v2** (frozen list концептов) | BT7 (путь A) | 0 |
| 8 | **Dedup для 5 типов** (authors, institutions, venues, methods, datasets) | BT11 | 0 |
| 9 | **Contradictions v1** (реальные научные противоречия в корпусе) | BT12 | 0, 1 |

**Принцип**: gold размечается **поверх существующих статей** (не вводим новый корпус), с честной разметкой `validation_status` и обязательной `cross_reference` на конкретные `tests/fixtures/benchmarks/layer1/<slug>/article.md` (offset/quote).

---

## 2. Где лежит pack

Гибрид: каталог отдельно, pack'и — рядом с runner'ами своих family (минимум вмешательства в текущие runner'ы).

```
tests/fixtures/
├── corpus/
│   ├── CATALOG.md                      # единый каталог (Layer 0)
│   ├── corpus_v1.json                  # машиночитаемая выжимка каталога
│   └── relations_v1.json               # межстатейные связи (Layer 9 source)
└── benchmarks/
    ├── claims/
    │   ├── case_tiers.json             # +tier "claims_pilot_v2", "claims_holdout_v1"
    │   ├── corpus_<slug>_v2/           # Layer 1
    │   └── holdout_<slug>_v1/          # Layer 1 holdout
    ├── retrieval/
    │   ├── workspace_scoped_live/      # Layer 2
    │   ├── hybrid_ablation_v2/         # Layer 3 (gold без ranked)
    │   └── multihop_v2/                # Layer 4
    ├── agent_tools_v1/
    │   ├── live_<NN>_<topic>/          # Layer 5 live cases
    │   └── multiagent_<NN>_<topic>/    # Layer 5 multi-agent (расширяем существующие)
    ├── idea_assist_v1/
    │   └── live_<NN>_<topic>/          # Layer 6
    ├── concept_topic/
    │   ├── concepts_frozen_v1.json     # Layer 7 frozen list
    │   └── corpus_<slug>_v2/           # Layer 7
    ├── dedup/                          # NEW
    │   ├── authors_v1/                 # Layer 8
    │   ├── institutions_v1/
    │   ├── venues_v1/
    │   ├── methods_v1/
    │   └── datasets_v1/
    └── contradictions_v1/              # Layer 9
        └── pair_<NN>_<topic>/
```

JSON-схемы для всех слоёв: [`docs/specs/benchmark-gold-schemas-v1.md`](../specs/benchmark-gold-schemas-v1.md).

---

## 3. Слои детально

### 3.1 Layer 0 — Catalog (фундамент)

**Артефакты:**

- `tests/fixtures/corpus/CATALOG.md` — человекочитаемый обзор: для каждой статьи строка с `corpus_work_id`, заголовком, годом, авторами, primary stage (one-stage / two-stage / transformer / classical), методами (canonical names), датасетами, ключевыми claims (3–5 на статью), ссылками на цитируемые статьи **внутри** корпуса.
- `tests/fixtures/corpus/corpus_v1.json` — машиночитаемая выжимка (используется runner'ами и LLM-валидатором).
- `tests/fixtures/corpus/relations_v1.json` — межстатейные связи: `cites[]`, `extends[]`, `compares_with[]`, `contradicts[]`. Это «семантический индекс», на котором стоят Layer 4 (multihop), Layer 8 (dedup кросс-сличение методов/авторов), Layer 9 (contradictions).

**Заполнение**: я делаю draft на основе `article.md`/`gold.json` каждой папки `layer1/<slug>/`. LLM-валидатор отдельно собирает свой draft независимо (другой extractor) — расхождения пишутся в `consistency_report.json`. Spot-check тебе.

**Acceptance:**
- Каталог покрывает **все** 35+ статей в `tests/fixtures/benchmarks/layer1/*_realpdf/` + `yolov1` + `arxiv_refs_heavy` + `doi_refs_heavy`.
- `corpus_v1.json` валидируется JSON-схемой; ни одного `corpus_work_id` без `slug`/`title`/`year`/`primary_stage`.
- `relations_v1.json` содержит ≥ 60 рёбер (типичный детектор цитирует 5–15 предшественников из корпуса).

### 3.2 Layer 1 — Claims gold v2 + holdout (BT6)

**Что меняется vs текущего:**
- Текущий `corpus_<slug>` имеет 1 expected_claim с `anchor_phrase`, дословно присутствующим в `article.md` → recall=1.0 тривиально.
- v2 вводит:
  - **3–5 claims на статью** разнообразных типов: `performance_positive`, `performance_negative`, `method`, `finding`, `limitation` (см. distribution в §3.2.2).
  - **paraphrased gold**: `expected_claim_text` ≠ дословной фразе; matching через `match_mode: "embedding_sim"` (cos ≥ 0.75) или `"rouge_l"` (≥ 0.5).
  - **distractor-чанки**: в `article_text` runner добавляет случайные параграфы из соседних статей корпуса (определяется через `corpus_v1.json`); gold содержит `distractor_strategy: "neighboring_paper_paragraphs"`, чтобы поведение было воспроизводимо.
  - **polarity diversity**: ≥ 30% claims с `polarity: "negative"` (e.g. «X не превосходит Y», «при низком разрешении точность падает»).
  - **claim_type diversity**: ≥ 4 типа покрыты в pilot tier.

**Holdout (новый tier `claims_holdout_v1`):**
- 5 кейсов из 5 статей **вне** `claims_pilot` и `claims_pilot_train`.
- Прогон еженедельно (CI cron `weekly`), не в ночном.

**Acceptance:**
- 15 статей × 3–5 claims ≈ 50–75 claim-кейсов в pilot v2; 5 кейсов в holdout.
- `mean_claim_recall` на v2 в **реалистичном диапазоне 0.6–0.85** (не 1.0); `mean_claim_precision` ≥ 0.7.
- Извлечение из чанка **с distractor** даёт `precision_drop_with_distractors ≤ 0.15`.
- В core `claims_production` family возвращается **CONDITIONAL** до 7 ночей зелёного на v2 + holdout.

### 3.3 Layer 2 — Workspace-scoped retrieval live (BT2)

**Workspaces** (3 штуки, описаны в `_workspaces.json`):
- `ws_yolo_family`: `yolov1`, `yolov2_realpdf`, `yolov3_realpdf`, `yolox_realpdf`.
- `ws_two_stage`: `rcnn_realpdf`, `fast_rcnn_realpdf`, `faster_rcnn_realpdf`, `rfcn_realpdf`, `mask_rcnn_realpdf`, `cascade_rcnn_realpdf`, `libra_rcnn_realpdf`.
- `ws_full_corpus`: все статьи (для negative — должен возвращать всё, без forbidden).

**Кейсы (6):**
1. `ws_yolo_speed_question` (`ws_yolo_family`): «what real-time gains did YOLO models report?» → reference содержит численные цифры из YOLO papers; `forbidden_work_ids` = все two-stage.
2. `ws_yolo_anchor_history` (`ws_yolo_family`): «when did YOLO move to anchor-based and back?» → reference: YOLOv2 (anchors) → YOLOv1/YOLOv3 history; forbidden — all DETR/FCOS.
3. `ws_two_stage_evolution` (`ws_two_stage`): «how did region proposals evolve from R-CNN to Faster R-CNN?» → reference покрывает Selective Search → SPP → ROI pooling → RPN; forbidden — YOLO family.
4. `ws_two_stage_speed_problem` (`ws_two_stage`): «why was R-CNN slow?» → reference: per-region CNN forward pass; forbidden — single-stage.
5. `ws_full_corpus_anchor_free_overview` (`ws_full_corpus`): «what are anchor-free detectors?» → reference: CornerNet, FCOS, CenterNet; forbidden = ∅.
6. `ws_full_corpus_negative_unrelated` (`ws_full_corpus`): «what is BERT?» → reference: «no detector in this workspace addresses BERT directly»; ожидаемое поведение — empty/abstain.

**Метрики:**
- `forbidden_work_id_violation_count == 0` (gate).
- `min_answer_rouge_l ≥ 0.18` против `answer_reference_text`.
- `min_citation_count ≥ 2` (кроме negative-кейса 6, где `expected_citations: []`).

**Acceptance:** 6/6 при поднятом стеке; артефакт `current-retrieval-workspace-scoped-live.json` имеет `runtime_mode: "live"`.

### 3.4 Layer 3 — Hybrid ablation v2 (BT4)

**Что меняется:** `gold.json` каждой `ha_NN/` теряет `vector_ranked_work_ids`/`hybrid_ranked_work_ids` (они генерируются runner'ом из живого Qdrant) и оставляет только `relevant_work_ids[]`.

**8 кейсов, темы:**
1. `ha_two_stage_before_2017` — relevant: rcnn, fast_rcnn, faster_rcnn, sppnet.
2. `ha_first_feature_pyramid` — relevant: fpn, retinanet (FPN-based), libra_rcnn.
3. `ha_anchor_free` — relevant: cornernet, centernet, fcos, atss.
4. `ha_real_time_one_stage` — relevant: yolov1, yolov2, yolov3, ssd, yolox.
5. `ha_transformer_detection` — relevant: detr, deformable_detr, dn_detr, dino.
6. `ha_focal_loss` — relevant: retinanet (главный); irrelevant: ssd, yolov2 (single-stage без focal).
7. `ha_multi_stage_cascade` — relevant: cascade_rcnn, libra_rcnn (refinement); irrelevant: yolov1, ssd.
8. `ha_set_prediction_no_nms` — relevant: detr, deformable_detr; irrelevant: rcnn, faster_rcnn (используют NMS).

**Метрика:** `mrr_hybrid - mrr_vector ≥ 0.05` advisory (после починки).

### 3.5 Layer 4 — Multihop v2 (BT3)

**5 кейсов** на graph-traversal (`MENTIONS_METHOD`/`USES_DATASET`/`CITES`/`AFFILIATED_WITH` из onthology):

1. `mh_yolov1_cited_methods`: «какие методы цитируются в YOLOv1?» → expected `method_node_ids`: Selective Search, OverFeat, R-CNN, DPM, Sliding window.
2. `mh_shared_datasets_two_stage_vs_transformer`: «какие датасеты общие у Faster R-CNN и DETR?» → expected: PASCAL VOC, MS COCO.
3. `mh_authors_in_both_one_and_two_stage`: «авторы с публикациями и в one-stage, и в two-stage detectors» → expected: Ross Girshick (R-CNN, Mask R-CNN, YOLO), Kaiming He (Mask R-CNN, FPN, RetinaNet).
4. `mh_methods_using_focal_loss`: «методы, использующие focal loss или его варианты» → expected: RetinaNet, GFL (generalized focal loss), ATSS (использует focal-style).
5. `mh_evolution_chain_proposals`: «эволюция метода region proposal от 2014 к 2017» → expected ordered chain: Selective Search → R-CNN → SPP-net → Fast R-CNN → Faster R-CNN (RPN).

**Метрики:** `precision`, `recall`, `chain_order_correctness` (для упорядоченных кейсов).

### 3.6 Layer 5 — Agent-tools live + multi-agent (BT8, BT9)

**Live (8 кейсов)** — расширение `agent_tools_v1/agent_case_*` на live runtime:
- `live_01_who_introduced_focal_loss` → ожидаемая последовательность: `vector_search` → `cypher_query(method=focal_loss)` → `cite_works`. `expected_methods: ["focal_loss"]`, `expected_works ⊃ ["retinanet_focal_realpdf"]`.
- `live_02_first_anchor_free_detector` → `vector_search` + `cypher_query`; `expected_works ⊃ ["cornernet_realpdf"]`.
- `live_03_compare_yolov1_vs_ssd` → comparative reasoning.
- `live_04_authors_of_detr` → `cypher_query` + `cite_authors`.
- `live_05_datasets_used_by_efficientdet` → `cypher_query` (USES_DATASET).
- `live_06_method_chain_yolov1_to_yolox` → multi-hop.
- `live_07_negative_question_no_match` → ожидается graceful empty.
- `live_08_adversarial_cypher_attempt` → запрос содержит конструкции типа «MERGE» в тексте; gate `cypher_safety = 1.0`.

**Multi-agent (5 кейсов)** — расширение `multiagent_*`:
- expected_specialist_sequence: `retrieval_specialist → graph_specialist → writer` для большинства; для simple lookup допустимо `retrieval_specialist → writer`.
- метрика `_specialist_sequence_match ≥ 0.7` advisory.

**Acceptance:** оба артефакта `runtime_mode: "live"`, `latency_p95_ms > 1`; `agent_tools_judge_pilot.json` существует с `mean_weighted_score ≥ 4.0/6` advisory.

### 3.7 Layer 6 — Idea-assist live (BT10)

**8 live-кейсов**, для каждого:
- `seed_topic` (по корпусу): «improve real-time detector under low-light», «reduce DETR convergence epochs», «end-to-end detector without NMS for embedded», и т.д.
- `supporting_claim_ids[]` (≥ 2 из corpus_v1) — заранее известные claims, на которые гипотеза должна опираться.
- `forbidden_substrings[]`: фразы из исходных статей, которые если попадают в гипотезу — это пересказ, не идея (например: дословная формулировка abstract'а).
- `min_supporting_claim_count: 2`.
- `reference_hypothesis` (опционально, для qualitative judge): пример «честной» гипотезы.

**Усиленные метрики (BT10):**
- `_score_no_plagiarism = 0` если ROUGE-L > 0.7 с любой `evidence_quote` или `seed_topic`.
- `_score_novelty` награждает только если `novelty_hint` ссылается на gap в `supporting_claim_ids`.

### 3.8 Layer 7 — Concept/Topic v2 (BT7 путь A)

**`concepts_frozen_v1.json`** — frozen список ~25 концептов корпуса:
```
region_proposal, anchor_based, anchor_free, set_prediction,
multi_scale_features, feature_pyramid, attention, self_attention,
focal_loss, iou_loss, l1_smooth_loss, nms, soft_nms,
end_to_end_training, two_stage, one_stage, transformer_decoder,
encoder_decoder, ROI_pooling, ROI_align, deformable_convolution,
keypoint_heatmap, compound_scaling, knowledge_distillation,
positive_negative_mining
```

Для каждой статьи (10 пилотных) gold отмечает `concepts_present[]` — какие концепты реально обсуждаются (по верификации спот-чек'ом); `concepts_absent[]` — критично для precision (модель не должна видеть лишнего).

**Acceptance:** recall в **реалистичном** 0.5–0.8 (не 1.0); precision ≥ 0.8.

### 3.9 Layer 8 — Dedup для 5 типов (BT11)

Все 5 pack'ов следуют одному формату (см. [§3.2 Dedup schema](../specs/benchmark-gold-schemas-v1.md#32-dedup-pack-schema)):
- `records[]` — карточки сущностей с поверхностными вариациями написания;
- `clusters[]` — массивы `entity_id` той же сущности;
- `negative_pairs[]` (новое vs текущего): пары, которые **не** должны мерджиться (это закрывает «нет false-positive»).

**Содержание (примеры из реального корпуса):**

#### 3.9.1 `dedup/authors_v1/`
- 5–7 кластеров:
  - `Joseph Redmon` ↔ `J. Redmon` (positive).
  - `Ross Girshick` ↔ `R. Girshick` (positive).
  - `Kaiming He` ↔ `K. He` (positive).
  - `Jian Sun` ↔ `J. Sun` (positive, важный — много работ).
  - `Xiangyu Zhang` ↔ `X. Zhang` (positive, ambiguous initials).
- `negative_pairs[]`: `Xiangyu Zhang` ≠ `Xinyu Zhang` (разные); `J. Smith` (statistician) ≠ `J. Smith` (vision researcher).

#### 3.9.2 `dedup/institutions_v1/`
- Кластеры: MSR ↔ Microsoft Research; FAIR ↔ Facebook AI Research ↔ Meta AI; UW ↔ University of Washington; «MIT» ↔ «Massachusetts Institute of Technology»; «AI2» ↔ «Allen Institute for AI».
- Negative: «Microsoft Research Asia» ≠ «Microsoft Research» (разные подразделения; решение — не мерджить или мерджить с указанием — фиксируем в gold).

#### 3.9.3 `dedup/venues_v1/`
- Кластеры: «CVPR 2014» ↔ «CVPR'14» ↔ «Conf on Computer Vision and Pattern Recognition»; ICCV varianty; ECCV; NeurIPS ↔ NIPS (та же конференция, переименована — известный кейс).
- Negative: CVPR 2014 ≠ CVPR 2017 (год разный — НЕ кластер); ICCV ≠ CVPR (разные конференции).

#### 3.9.4 `dedup/methods_v1/`
- Positive: «R-CNN» ↔ «Region-based CNN» ↔ «RCNN»; «FPN» ↔ «Feature Pyramid Network»; «SSD» ↔ «Single Shot Detector»; «DETR» ↔ «DEtection TRansformer».
- Negative (важно!): «Faster R-CNN» ≠ «Mask R-CNN»; «YOLOv1» ≠ «YOLOv2»; «R-CNN» ≠ «Fast R-CNN» (это разные статьи и методы — поверхностно похожие имена).

#### 3.9.5 `dedup/datasets_v1/`
- Positive: «PASCAL VOC» ↔ «VOC» ↔ «Pascal Visual Object Classes»; «MS COCO» ↔ «COCO» ↔ «Microsoft COCO»; «ImageNet» ↔ «ILSVRC».
- Negative: «PASCAL VOC 2007» ≠ «PASCAL VOC 2012» (разные splits, методология сравнения требует разных); COCO 2014 ≠ COCO 2017.

**Метрики per-type:** `pairwise_precision`, `pairwise_recall`, `cluster_purity`, `auto_merge_rate`, `false_merge_count` (gate = 0 для negative_pairs).

**Acceptance:** `pairwise_precision ≥ 0.9`, `pairwise_recall ≥ 0.8` per type, advisory.

### 3.10 Layer 9 — Contradictions v1 (BT12)

**5–7 пар противоречий**, каждая — реальное научное расхождение в корпусе с точными цитатами:

| pair_id | claim A (work) | claim B (work) | тип противоречия |
|---------|----------------|----------------|------------------|
| `c01_two_stage_vs_one_stage_accuracy` | «two-stage detectors are more accurate than one-stage» (Faster R-CNN, 2015) | «one-stage detectors with focal loss match two-stage accuracy» (RetinaNet, 2017) | era-shift |
| `c02_anchor_based_vs_anchor_free` | «anchor design is critical for detection performance» (Faster R-CNN / SSD) | «anchor-free detection achieves comparable accuracy» (FCOS, CornerNet) | design-paradigm |
| `c03_nms_required_vs_set_prediction` | «non-maximum suppression is essential post-processing» (almost all CNN detectors) | «set prediction with bipartite matching removes need for NMS» (DETR) | post-processing |
| `c04_external_proposals_vs_rpn` | «high-quality external proposals (Selective Search) needed» (R-CNN) | «RPN integrated in network is faster and equally accurate» (Faster R-CNN) | architectural |
| `c05_depth_vs_compound_scaling` | «deeper backbones improve detection accuracy» (early ResNet-based detectors) | «compound scaling (depth + width + resolution) is more efficient» (EfficientDet) | scaling |
| `c06_handcrafted_vs_learned_features` | «handcrafted features (HOG) sufficient for detection» (HOG paper, 2005) | «learned CNN features dramatically outperform HOG» (R-CNN, 2014) | classical-vs-deep |

Каждая пара содержит:
- `claim_a_id`, `claim_a_text`, `claim_a_quote` (offset в article.md), `claim_a_work_id`.
- `claim_b_id`, ... аналогично.
- `evidence_quotes[]` — поддерживающие цитаты из обеих статей.
- `contradiction_type`: `era_shift | design_paradigm | post_processing | architectural | scaling | classical_vs_deep`.
- `severity`: `direct | nuanced` (direct = прямое отрицание; nuanced = условие переменилось со временем).

**Метрика:** `contradiction_pair_recall` — какую долю пар runner Layer 9 находит автоматически.

**Acceptance:** 3/5 advisory; persistence через `Neo4jGraphStore.upsert_contradiction()` (см. BT12 в trust audit).

---

## 4. LLM-validated workflow (валидация без ручной разметки каждого кейса)

Поскольку выбран `llm_assisted` режим — каждый pack проходит **двойную независимую разметку**, и пользователь делает только spot-check на расхождениях.

### 4.1 Принцип

```
Source: tests/fixtures/benchmarks/layer1/<slug>/article.md
       + tests/fixtures/corpus/corpus_v1.json (для cross-paper layers)
       │
       ├──► Extractor A (claude/gpt-5 prompt v1, тех же seeds) ──► gold_draft_a.json
       │
       └──► Extractor B (alternate model / different prompt) ────► gold_draft_b.json
                                  │
                                  ▼
                          consistency_diff.py
                                  │
                                  ├──► consistency_report.json
                                  │     • exact_match_count
                                  │     • semantic_match_count (через embedding cos ≥ 0.85)
                                  │     • disagreement_cases[]
                                  │
                                  ▼
                          ручной spot-check (только disagreements)
                                  │
                                  ▼
                          gold.json (final, validated)
                          + validation_report.md
```

### 4.2 Что считается disagreement

- В Layer 1 (claims): один extractor нашёл claim, другой — нет; либо `polarity` различается; либо `claim_type` различается; либо `match_mode` (paraphrase vs exact) различается.
- В Layer 9 (contradictions): один extractor пометил пару как `direct`, другой — как `nuanced`, либо один не нашёл пару вовсе.
- В Layer 7 (concepts): один пометил концепт `present`, другой `absent`.
- В Layer 8 (dedup): один пометил пару как `duplicate`, другой — как `negative`.
- В Layer 0 (catalog): расхождения в `methods[]`, `datasets[]`, `cites[]` ≥ 1 элемент.

### 4.3 Что **не** требует spot-check

- Acronym expansion (FAIR ↔ Facebook AI Research) и аналогичные тривиальные dedup-кейсы.
- Layer 3 (hybrid ablation) — gold чисто фактологический (relevant work_ids), не семантический; одной разметки достаточно.
- Layer 4 (multihop) — gold выводится из `relations_v1.json` детерминированно; ручная проверка только связей в каталоге.

### 4.4 Артефакты валидации

Каждый pack содержит:
- `validation_report.md` с заголовком (модели, дата, версии prompt'ов, кол-во disagreements, кол-во spot-check'ов).
- `consistency_report.json` (машиночитаемая выжимка).
- В каждом `gold.json` поле `meta.validation_status`: `"draft" | "llm_dual_validated" | "human_spot_checked"`.

---

## 5. Порядок работ (фазы)

Сессии (~1 фаза = 1 сессия), каждая закрывается отдельным PR:

### Phase 0 — Foundation (текущая сессия, 2026-04-25)
1. Этот план.
2. JSON-схемы [`benchmark-gold-schemas-v1.md`](../specs/benchmark-gold-schemas-v1.md).
3. `tests/fixtures/corpus/CATALOG.md` + `corpus_v1.json` skeleton (полная таблица всех статей; `relations_v1.json` начнём с CITES — известны из gold_enrichment).
4. **Образцовый pack**: `tests/fixtures/benchmarks/dedup/authors_v1/` (полный gold + README) — служит шаблоном.
5. Backlog entries по оставшимся pack'ам.
6. Обновить trust-audit doc (раздел BT0 / BT-Prep).

### Phase 1 — Dedup-5 + catalog finalize
- Остальные 4 dedup pack'а (institutions, venues, methods, datasets).
- `relations_v1.json` дополнен `extends`, `compares_with`.

### Phase 2 — Claims gold v2 + holdout (BT6 prep)
- 15 статей × 3–5 claims; pilot v2 + holdout_v1.
- Включая paraphrased + distractor flag в schema.

### Phase 3 — Contradictions v1 (BT12 prep) + Concept/Topic v2 (BT7 prep)
- 5–7 пар противоречий с цитатами.
- Frozen list концептов и разметка для 10 статей.

### Phase 4 — Retrieval (workspace_live + hybrid_v2 + multihop_v2)
- Layers 2, 3, 4. Можно за одну сессию — формат у трёх близкий.

### Phase 5 — Agent-tools live + Multi-agent + Idea-assist live
- Layers 5, 6.

### Phase 6 — LLM-validation pass (через все pack'и)
- Прогнать extractor B на всём, собрать `consistency_report.json` для каждого, выдать тебе короткий отчёт «вот N disagreements на spot-check».

---

## 6. Acceptance — Corpus Gold Pack v1 закрыт

1. Все 9 layers существуют как файлы в указанных путях.
2. Каждый pack имеет `meta.validation_status: "human_spot_checked"`.
3. JSON-схемы `docs/specs/benchmark-gold-schemas-v1.md` валидируют каждый `gold.json` (CI step `pytest tests/eval/test_gold_schemas.py`).
4. Trust audit обновлён: §3 раздел про phantom-зелёные family содержит ссылку «replaced by Corpus Gold Pack v1, see ...».
5. Backlog `docs/backlog/refactor-backend.md` содержит entries `[DONE]` для каждой завершённой Phase.

---

## 7. Что **не** входит в этот план

- Написание/правка runner'ов (это работа BT2..BT12, после готового gold).
- Изменения production-кода (`science_graphrag/ingestion/`, `science_graphrag/agent/`) — кроме `Hypothesis`/`Contradictions` persistence в Phase 3 как опционального шага.
- Расширение корпуса новыми статьями — pack v1 строится **на том корпусе, что уже есть**. Если потом корпус расширится (medical/social science papers), будет pack v2.

---

## 8. Связи

- [`ontology-benchmarks-trust-audit-2026-04-25.md`](ontology-benchmarks-trust-audit-2026-04-25.md) — мотивация и BT-задачи.
- [`ontology-benchmarks-roadmap-2026-04-24.md`](ontology-benchmarks-roadmap-2026-04-24.md) — Wave M..T контракты, к которым этот pack привязан.
- [`master-roadmap-and-refactor-plan-2026-04-25.md`](master-roadmap-and-refactor-plan-2026-04-25.md) — Track D (Benchmarks).
- [`docs/specs/benchmark-gold-schemas-v1.md`](../specs/benchmark-gold-schemas-v1.md) — JSON-схемы для всех слоёв.
- `tests/fixtures/corpus/CATALOG.md` — каталог корпуса (Layer 0).
- `tests/fixtures/benchmarks/dedup/authors_v1/README.md` — образцовый pack (шаблон формата).
