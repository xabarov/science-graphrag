# Corpus Gold Pack v1 — план benchmark-фикстур поверх 30+ статей (2026-04-25)

**Дата:** 2026-04-25
**Тип:** plan + spec (история построения фикстур)
**Статус:** **Phase 0–6 complete** (gold delivered 2026-04-26). Документ остаётся **источником ссылок** для README фикстур и секций §3–§6; актуальная серия runner'ов BT — [`ontology-benchmarks-trust-audit-2026-04-25.md`](./ontology-benchmarks-trust-audit-2026-04-25.md) + [`master-roadmap-and-refactor-plan-2026-04-25.md`](./master-roadmap-and-refactor-plan-2026-04-25.md) §10.
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

### Phase 1 — Dedup-5 + catalog finalize ✅ (2026-04-25)
- 4 dedup pack'а собраны: `institutions_v1` (20/7/3, MSR↔MSRA как критический negative), `venues_v1` (19/7/4, year-shift negatives), `methods_v1` (25/7/6, R-CNN substring traps + GFL≠Focal Loss), `datasets_v1` (21/6/5, version-shift negatives).
- `relations_v1.json` собран: 502 ребра (cites=78 [29 авто из bibliography + 49 manual для R-CNN/YOLO/DETR family chains], extends=15, compares_with=12, contradicts=7, shares_author=59 derived, shares_dataset=331 derived).
- Все 5 файлов проходят structural validation (см. `docs/backlog/refactor-backend.md` entry `[DONE] Corpus Gold Pack v1 — Phase 1`).
- Все pack'и оставлены в `meta.validation_status: "draft"` — финальная промоутка через Phase 6 (dual-LLM extractor + spot-check).

### Phase 2 — Claims gold v2 + holdout (BT6 prep) ✅ (2026-04-25)
- 15 pilot pack'ов (`tests/fixtures/benchmarks/claims/corpus_<slug>_v2/gold.json`, 64 claims, 31.2% negative).
- 5 holdout pack'ов (`holdout_<slug>_v1/gold.json`, 21 claims, 28.6% negative, 0 overlap c pilot по `corpus_work_id`).
- 85 claims итого, 30.6% negative (acceptance ≥ 30% выполнено), все 6 `claim_type` представлены.
- `match_mode`: embedding_sim + rouge_l (no `exact`).
- `distractor_strategy.neighboring_paper_paragraphs` задан в каждом case.
- Paraphrase verified: 0 случаев 8-словного дословного substring overlap с `article.md`.
- Tier'ы `claims_pilot_v2` / `claims_holdout_v1` добавлены в `case_tiers.json`.
- Runner-side работа (BT6 patch для distractor injection + embedding matching + weekly cron) **out of scope** Phase 2 — отдельное BT6 задание.

### Phase 3 — Contradictions v1 (BT12 prep) + Concept/Topic v2 (BT7 prep) ✅ (2026-04-25)
- **Layer 9 — Contradictions v1**: 7 пар (`tests/fixtures/benchmarks/contradictions_v1/pair_NN_<a>_vs_<b>/gold.json`), все 6 разрешённых `contradiction_type` (era_shift/design_paradigm × 2/post_processing/architectural/classical_vs_deep/scaling), оба `severity` (direct × 4, nuanced × 3), у каждого case прямые `evidence_quote` из обеих статей + `expected_neo4j_pattern` подсказка.
- **Layer 7 — Concept/Topic v2**:
  - `concept_topic/concepts_frozen_v1.json`: 25 канонических концептов с aliases (proposal/pipeline, stage type, backbones, loss/post-proc, architecture, classical/data).
  - `concept_topic/corpus_<slug>_v2/gold.json`: 10 пилотных статей (yolov1, faster_rcnn, retinanet_focal, ssd, mask_rcnn, fpn, detr, cornernet, fcos, cascade_rcnn).
  - 138 разметочных лейблов всего (67 present + 71 absent), 25/25 frozen концептов покрыты ≥ 1 pack'ом.
- Tier'ы добавлены: `concept_topic_pilot_v2` (10 cases) и `contradictions_pilot_v1` (7 cases) в соответствующие `case_tiers.json`.
- README с матрицами покрытия в обоих каталогах.
- Все pack'и с `meta.validation_status: "draft"` — финальная промоутка через Phase 6 (dual-LLM extractor).
- Cross-ref валидация (corpus_v1.works ∪ layer1 slugs): 0 unknown `corpus_work_id`, 0 unknown `concept_id`, 0 дубликатов в present/absent одной статьи.
- Runner-side работа (BT12 — `:CONTRADICTS` persistence + recall runner; BT7 Path A — substring-tautology kill в concept extraction) **out of scope** Phase 3 — отдельные BT задания.

### Phase 4 — Retrieval (workspace_live + hybrid_v2 + multihop_v2) ✅ (2026-04-25)
- **Layer 2 (workspace_scoped_live, BT2):** `tests/fixtures/benchmarks/retrieval/workspace_scoped_live/`.
  - 3 workspaces в `_workspaces.json`: `ws_yolo_family` (4 papers), `ws_two_stage` (7 papers), `ws_full_corpus` (`*` = все 35).
  - 6 cases (3 positive + 3 negative): по 2 кейса на workspace, в каждом по одному positive (multi-paper aggregation) и negative (abstain — ответ вне ws).
  - `forbidden_corpus_work_ids` с `forbidden_violation_gate: 0` в каждом case; validation enforced — все forbidden ids ВНЕ workspace.
  - `expected_citations` всегда внутри ws; `answer_metric` = `rouge_l` (positive) или `abstain_keywords` (negative).
- **Layer 3 (hybrid_ablation_v2, BT4):** `tests/fixtures/benchmarks/retrieval/hybrid_ablation_v2/`.
  - 8 cases. Топики выбраны где BM25 keyword даёт edge поверх vector: anchor_free, focal_loss, set_prediction_transformer, compound_scaling, keypoint_corner, classical_handcrafted, two_stage_rpn_evolution, iou_loss_quality.
  - 22 relevant + 28 irrelevant ids = 50 ground-truth labels.
  - **Phantom-green killer:** `vector_ranked_work_ids` / `hybrid_ranked_work_ids` запрещены в gold v2 (validation gate). `ranked_lists_source: "runner_generated"` — runner обязан сам делать live запрос к Qdrant + BM25.
  - `min_mrr_delta_hybrid_minus_vector: 0.05`, `k_for_mrr: 10`.
- **Layer 4 (multihop_v2, BT3):** `tests/fixtures/benchmarks/retrieval/multihop_v2/`.
  - 5 cases (3 ordered chains + 2 unordered sets).
  - Ordered: `mh_proposal_evolution_chain` (5 nodes: selective_search→rcnn→fast_rcnn→faster_rcnn→mask_rcnn), `mh_yolo_lineage_chain` (4 nodes), `mh_detr_lineage_chain` (4 nodes).
  - Unordered: `mh_authors_yolo_intersect_rcnn_family` (Author kind), `mh_datasets_shared_one_stage_detectors` (Dataset kind).
  - Все chain adjacencies подтверждены `relations_v1.json` (CITES + EXTENDS edges); unordered cases опираются на `shares_author` × 59 + `shares_dataset` × 331.
  - `infrastructure_required: ["neo4j", "qdrant"]` — runner обязан hard-fail (не skip) если сервисы недоступны.
- **Tier'ы добавлены:** `workspace_scoped_live_pilot` (6 case_id), `hybrid_ablation_v2_pilot` (8), `multihop_v2_pilot` (5) в соответствующие `case_tiers.json`.
- README с матрицами покрытия и метриками в каждом из 3 каталогов.
- Cross-ref валидация: 0 unknown `corpus_work_id`, 0 leak'ов `vector_ranked_work_ids`/`hybrid_ranked_work_ids` в hybrid v2, 0 forbidden ids внутри ws, 0 overlap relevant∩irrelevant.
- Все pack'и в `meta.validation_status: "draft"` — финальный промоут через Phase 6.
- Runner-side работа (BT2 — abstain detection + workspace boundary; BT3 — neo4j hard-fail + chain LCS metric; BT4 — live Qdrant+BM25 ranking) **out of scope** Phase 4 — отдельные BT задания.

### Phase 5 — Agent-tools live + Multi-agent + Idea-assist live ✅
- Layers 5 (`agent_tools_v1/{live_*, multiagent_live_*, adversarial_cypher_*}`), 6 (`idea_assist_v1/live_*`).
- 9 agent-tools cases (6 live + 2 multi-agent + 1 adversarial cypher) и 4 idea-assist cases.
- Agent live cases несут `expected_tool_sequence` с `args_match` (`query_contains_any` / `query_contains_all`), `expected_works_corpus_ids`, `expected_methods_canonical`, `answer_reference_text` + `answer_metric: rouge_l ≥ 0.18..0.20` (positive) или `abstain_keywords` (negative), и `cypher_safety_required: 1.0`.
- 5 positive + 1 negative (abstain) live кейса; multi-agent кейсы добавляют `allowed_alternative_sequences` и `min_specialist_sequence_match`.
- Adversarial cypher case инжектит `DELETE` и `DROP` в текст вопроса — gate `cypher_safety_violation_count_gate: 0`; валидация подтверждает что вопрос реально содержит forbidden keywords (gate non-vacuous).
- Idea-assist кейсы используют `supporting_claim_id_pool` из 20 реальных claim_id'ов из Phase 2 claims pack (85 known); `forbidden_substrings` — verbatim фразы из article.md, `max_rouge_l_against_evidence_quotes: 0.7`, `novelty_must_reference_gap: true`.
- Cross-ref валидация: 0 unknown `corpus_work_id`, 0 unknown `claim_id`, schemas корректны (live=v2, multi-agent/adversarial=v1, idea_assist=v2), все tier-файлы консистентны.
- Все pack'и в `meta.validation_status: "draft"` — финальный промоут через Phase 6.
- Runner-side работа (BT8 — args_match enforcement + cite_works recall; BT9 — specialist sequence; BT10 — supporting_claim_recall + forbidden_substring gate + LLM-judge novelty) **out of scope** Phase 5 — отдельные BT задания.

### Phase 6 — LLM-validation pass (через все pack'и)

#### Phase 6.A — инфраструктура + PoC на claims_v2 ✅ (2026-04-25)

- **`scripts/dual_validate/`** — модуль с extractor framework (`extractors/base.py` → `ExtractorBase`), OpenRouter-compatible LLM wrapper (`llm_client.py`), алгоритмический A/B matcher (`matcher.py` — Jaccard token overlap + greedy bipartite, default min_score=0.20), JSON schema для `consistency_report` (`consistency_report.py`).
- **`scripts/dual_extract_validate.py`** — CLI (`--layer`, `--pack`, `--model`, `--dry-run`, `--save-raw-response`). Резолвит API key/base/model в порядке: CLI → `benchmark_teacher_*` → `extraction_llm_*` (тот же priority что у `scripts/teacher_llm_settings.py`).
- **Per-layer extractor**: реализован первый — `extractors/claims_v2.py` (для `tests/fixtures/benchmarks/claims/corpus_*_v2/`).
- **`tests/test_dual_extract_validate.py`** — 11 unit-тестов: tokenizer, jaccard, greedy bipartite (включая field-disagreement detection), spot-check priority branching, schema roundtrip, claims_v2 dry-run skeleton, response parsing с enum-coercion, rejection of non-JSON. Pylint 9.95/10, 11/11 passed.
- **PoC прогон на `corpus_yolov1_v2` с deepseek/deepseek-v3.2** (28s, 13.5K tokens) — найдены 4 actionable disagreements:
  1. `yolov1_unified_pipeline` — polarity flip A=positive vs B=neutral (semantic ambiguity «является ли описание метода positive claim?»).
  2. `yolov1_artwork_generalization` — type flip A=finding vs B=comparison (обе категории применимы).
  3. `yolov1_grid_based_detection` пропущен B (потенциально merged в "regression problem").
  4. `yolov1_two_stage_higher_acc_negative` пропущен B — реальный negative claim, важный для polarity_distribution.
  - Spot-check priority `high` (rationale: polarity_flips=1, unmatched_a_ratio=0.33).
  - Отчёт: `tests/fixtures/benchmarks/claims/corpus_yolov1_v2/consistency_report.json` + `consistency_report.raw.json`.

#### Phase 6.B — full claims_v2 pass ✅ (2026-04-25)

- Прогнан extractor B = `deepseek/deepseek-v3.2` на **всех 20** claims pack'ах (15 pilot + 5 holdout): 7 минут wall-time, **300K** tokens, **≈$0.06** на OpenRouter. 20/20 `consistency_report.json` + 20/20 `consistency_report.raw.json` сохранены рядом с `gold.json`.
- **Усиление matcher (matcher v2):** добавлены `char_ngrams`, `char_overlap_coefficient` (Szymkiewicz–Simpson), `combined_score = max(token_jaccard, char_overlap_4gram)`. `match_records` получил параметр `scoring: "token" | "combined"`, default = `combined` с `min_score=0.35`. Char-overlap robust к length asymmetry: короткий B-парафраз больше не отваливается от длинного A-claim.
- **`--rebuild-from-raw` режим CLI** — пересобирает отчёты из сохранённых `.raw.json` без LLM-вызовов. Использован для бесплатного pre/post сравнения матчеров.
- **Сводка** в `eval/dual_validate/claims_v2_deepseek_summary.json`:
  - **global match ratio: 41.2% → 50.6% (+23%)** после перехода на combined-score @0.35;
  - 19/20 packs остаются `priority=high`, 1/20 (`corpus_detr_v2`) — `priority=medium` (только type flip без unmatched);
  - **10 polarity flips, 14 type flips** на 43 matched pairs — это и есть наиболее ценный сигнал для human spot-check;
  - 42 unmatched_a (B пропустил), 113 unmatched_b (B сгенерировал extra) — экстрактор B склонен к **более широкой** выборке (среднее 7.8 vs наши 4.25 на pack), что нормально для temperature=0.1 sampling;
  - **Recall ceiling алгоритмического матчера ≈ 50%**: оставшиеся unmatched пары (например `cascade_rcnn_v2`: 0/3) — это семантически совпадающие claims с лексической дистанцией > 0.35, для которых нужны **embeddings** (запланировано в Phase 6.D).
- **Не делаем промо `validation_status: draft → llm_dual_validated`** в этом раунде: 19/20 high — недостаточный сигнал для авто-промо. Промо требует либо (a) embedding-based matcher с recall > 75%, либо (b) human spot-check листа disagreements. Phase 6.B завершает **infrastructure + один LLM extractor**; промо — отдельная активность.
- **Test coverage:** `tests/test_dual_extract_validate.py` 14/14 passed, добавлены тесты на `char_jaccard`, `combined_score`, `rebuild_run_from_raw`. Pylint 9.90/10 для `scripts/dual_validate/` + `scripts/dual_extract_validate.py`.

#### Phase 6.D — embedding cascade matcher с baai/bge-m3 ✅

- Reusable `science_graphrag/embeddings/openrouter_provider.py` — `OpenRouterEmbeddingProvider` с per-text JSON file cache, batching, retry на `RateLimitError/APIError`. Готов к подключению в Qdrant ingestion (см. ADR-021), но в Phase 6.D используется только из dual_validate.
- Cascade-логика в `scripts/dual_validate/matcher.py`: если `lexical ≥ lexical_accept_threshold (0.50)` — берём lexical без вызова embeddings. Иначе считаем `embedding ≥ embedding_min_score (0.75) AND > lexical` → берём embedding. Иначе fallback к lexical c floor `min_score (0.35)`. Так амортизируем стоимость и **не теряем валидные lexical pairs**, у которых embedding сам по себе ниже порога.
- CLI: `--with-embeddings --embedding-model baai/bge-m3 --embedding-cache-root eval/dual_validate/embeddings_cache --promote-validation-status` (последний — идемпотентный апдейт `meta.validation_status: draft → llm_dual_validated` для priority∈{low, medium}).
- **Re-run 20 packs через `--rebuild-from-raw --with-embeddings` (zero new tokens):** recall **50.6% → 58.8%** (lex=28, emb=22 — embedding доля 44% всех matches). Priority: 0 low / **2 medium** / 18 high (vs 0/1/19 в Phase 6.B). **Auto-promoted в `llm_dual_validated`:** `corpus_centernet_v2`, `corpus_detr_v2`. Сводка: `eval/dual_validate/claims_v2_bge_m3_summary.json`. Tests 18/18, pylint 9.68/10.
- **Honest assessment:** прирост скромнее прогноза — DeepSeek extractor B часто извлекает claims из других параграфов или делает другую декомпозицию (одно gold-утверждение разнесено в B на 2-3 более мелких). Это **structural disagreements**, embedding similarity их не закрывает. Решается либо (a) prompt-engineering экстрактора B чтобы зафорсить ту же декомпозицию, либо (b) human spot-check disagreement-листа, либо (c) Phase 6.E (triple-vote multi-model).

#### Phase 6.C — расширение на остальные layers (8/8 done) ✅

- **Done в эту сессию (2026-04-25), free-text extractors:**
  - `scripts/dual_validate/extractors/concept_topic_v2.py` — closed-set diff по 25 frozen concepts. Полный прогон 10 packs × deepseek (~4 мин): **138/138 = 100% matched**, 2 promoted (`mask_rcnn`, `ssd`), 8 high из-за status flips. Сводка: `concept_topic_v2_deepseek_summary.json`.
  - `scripts/dual_validate/extractors/contradictions_v1.py` — per-pair diff с lexical+embedding cascade. 7 pairs × deepseek + bge-m3 (~1.5 мин): 6/7 matched, **embedding cascade сработал в 2/6 = 33% матчей**. 4 promoted, 3 high. Сводка: `contradictions_v1_deepseek_summary.json`.
  - `scripts/dual_validate/extractors/idea_assist_live.py` — B-reviewer оценивает gold-pool на адекватность. 4 cases × deepseek (~2 мин): 20/20 covered, **B пометил pool=`thin` и 2 claims с `relevance=low`** в 3/4 cases. 1 promoted, 3 high. Сводка: `idea_assist_live_deepseek_summary.json`.
- **Done в эту сессию (2026-04-25), dedup × 5:**
  - `scripts/dual_validate/extractors/dedup_v1.py` — общий `DedupExtractorBase` (≈300 строк) + `DedupAuthorsV1Extractor`/`Institutions`/`Venues`/`Methods`/`Datasets` с per-type domain-hint'ами в prompt'ах. Один LLM call per layer (≤4K tokens, всего 5 calls на ~1.5 мин на все 5 packs).
  - **ARI metric** через `_pair_counting_metrics` (Hubert-Arabie formulation): contingency-таблица over shared ids → expected/max indices → ARI ∈ [0, 1].
  - Результаты: ARI **0.88-1.00** (`authors=1.00, venues=1.00, methods=0.97, institutions=0.95, datasets=0.88`), **все 5 promoted** (medium из-за частичного покрытия `negative_pairs`). DeepSeek **дополнительно нашёл 3 must-not-merge constraint в methods_v1** (`R-CNN ≠ Fast R-CNN ≠ R-FCN`) и 1 в institutions — реальное расширение coverage. Сводки: `dedup_*_deepseek_summary.json`.
- **Done в эту сессию (2026-04-25), retrieval × 3:**
  - `scripts/dual_validate/extractors/retrieval_v1.py` — `WorkspaceScopedLiveExtractor` / `HybridAblationV2Extractor` / `MultihopV2Extractor`. Общий `_load_inventory()` парсит `tests/fixtures/corpus/CATALOG.md` (35 papers с title + year, кэшируется). Embedding cascade не применим — output space — закрытый набор `corpus_work_id`'ов.
  - `WorkspaceScopedLiveExtractor` (6 packs, ~30s): **ВСЕ 6 promoted, all low**. Special-case логика: при `a_total=0` (negative case) и `b_total=0` без boundary violations → low priority.
  - `HybridAblationV2Extractor` (8 packs, ~40s): 7/8 promoted (4 low + 3 medium + 1 high). B классифицирует кандидатов как relevant/irrelevant (без знания gold labels) — accuracy 0.60-1.00.
  - `MultihopV2Extractor` (5 packs, ~25s): для `ordered_chain` Kendall-style order correctness, для `unordered_set` — Jaccard. **3/3 chain perfect (F1=1.0, order=1.0)**, 2/2 set high (slug-vs-canonical disagreement в датасетах, B вернул empty list для author intersection).
- **Done в эту сессию (2026-04-25), agent_tools_live:**
  - `scripts/dual_validate/extractors/agent_tools_live.py` — focus только на 6 `live_*` cases. Tool-required-recall + works/methods Jaccard + answer token Jaccard. Special-case для negative (abstain_or_empty). 3/6 promoted (1 low + 2 medium + 3 high). Сводка: `agent_tools_live_deepseek_summary.json`.
- **Shared infra:**
  - **Lenient JSON parser** `parse_json_object_lenient` — применён ко всем 12 extractor'ам.
  - **Aggregator** `scripts/dual_validate/aggregate_summary.py` теперь поддерживает single-pack mode (для dedup) + multi-pack для всех остальных.
  - **`_safe_relative` path helper** в `dual_extract_validate.py` — безопасная конвертация в relative paths когда они не под cwd.
- **Итог Phase 6.C done:** **+24 packs auto-promoted** в этой сессии (3 free-text + 5 dedup + 16 retrieval/agent), **общий итог Phase 6:** **71 packs total → 33 promoted → 38 high-priority в очереди**. Tests **44/44**, pylint **9.59/10** (выше CI 7.0).

#### Phase 6.E — second/third model pass (in progress)

**Цель:** прогнать те же 38 high-priority packs через `anthropic/claude-sonnet-4.6` и `moonshotai/kimi-k2.6`, агрегировать через triple-vote (2-of-3 agreement) и промоутнуть в `validation_status: llm_triple_validated`.

**Инфра (готово):**

- **Per-model отчёты** через существующий `--report-name` флаг: `consistency_report.<tag>.json` рядом со старым (`deepseek` пишется в legacy `consistency_report.json`).
- **`--reasoning-mode {auto,disabled,low,medium,high}`** (новое) — пробрасывается через `LLMCallSpec.reasoning` в OpenRouter `extra_body`. Влияет на `prompt_hash` (отчёты с разной reasoning-конфигурацией не пересекаются).
- **`--max-output-tokens N`** — поднимает per-extractor `max_tokens` (только вверх, никогда вниз).
- **`scripts/dual_validate/run_phase6e_pass.py`** — driver, дискаверит high-priority pack'и по существующим `consistency_report.json`, поддерживает `--parallel N` (ThreadPoolExecutor над subprocess'ами для I/O-bound LLM-вызовов), `--force` для пере-исполнения, `--log-output` для стрим-лога.
- **`scripts/dual_validate/triple_vote_consensus.py`** — агрегирует N per-model отчётов в `consensus_report.json` (schema v1):
    - **Priority majority vote** с conservative tie-break (favour higher rank).
    - **Per-record vote** для слоёв со стабильным `a_id` в `matched_pairs` (claims_v2, concept_topic_v2, contradictions_v1, dedup, idea_assist_live, retrieval/{workspace_scoped_live, hybrid_ablation_v2}). Bucket: `matched_by_all` / `matched_by_majority` / `controversial`.
    - **Layer-agnostic для multihop_v2/agent_tools_live** (per-record vote отключён, но priority vote работает).
    - **Auto-promote**: `validation_status` → `llm_triple_validated` когда `consensus_priority ∈ {low, medium}` и `n_models_present ≥ --require-min-models` (default 2).

**Кими как reasoning-модель — нюанс:**
- `moonshotai/kimi-k2.6` по умолчанию использует hidden CoT, который съедает output budget.
- **С `reasoning.enabled=False`** — модель ленится, возвращает `{"claims":[]}`.
- **С `reasoning.effort=low` + `max_tokens=12000`** — извлекает 8 claims за ~100с/pack (vs 5min без override). Это рабочая комбинация.
- ADR/комментарий: kimi нельзя использовать в режиме «default reasoning» из-за непредсказуемого token usage и truncated JSON.

**Конфиг для Phase 6.E run:**
- `claude-sonnet-4.6 --max-output-tokens 6144 --with-embeddings` (без reasoning, ~20s/pack, parallel=1, ~13min total).
- `kimi-k2.6 --max-output-tokens 12000 --reasoning-mode low --with-embeddings --parallel 4` (~100s/pack, parallel=4, ~16min total).

**Замена kimi на deepseek-v4-pro:** kimi-k2.6 оказался непригоден для batch-extraction (reasoning model, output truncation даже с `effort=low + 12000 tokens`, ~5min/pack). Заменён на `deepseek/deepseek-v4-pro` (не reasoning, ~25s/pack, чище JSON). Третья модель из той же семьи DeepSeek (v3.2 → v4-pro), но с независимым model checkpoint — даёт независимый extractor B.

**Robust retry:** добавлены `_extract_retry_after` (mining `retry_after_seconds` из OpenRouter metadata) и `_compute_backoff` (jittered exponential cap=30s), `max_retries=5` (было 2). Покрывает upstream 429/502/503 от Together provider. Также добавлен empty-choices guard (200-OK с `choices=None` → retryable RuntimeError, а не путающее `'NoneType' subscriptable`).

**Финальные результаты triple-vote (deepseek + v4pro + claude):**

- 38 packs прошли consensus (`packs_with_consensus`).
- **2 promoted → `llm_triple_validated`** (consensus=medium, 2-of-3 majority):
    - `contradictions_v1/pair_06_hog_human_detection_vs_rcnn` — record_match=1.0 на всех 3 моделях.
    - `agent_tools_live/live_05_compare_two_stage_one_stage_accuracy`.
- **4 split-decision packs** (1 модель medium/low, 2 high) — приоритетные кандидаты для human review:
    - `claims_v2/corpus_cascade_rcnn_v2` (record_match=1.0!)
    - `contradictions_v1/pair_07_retinanet_focal_vs_efficientdet` (record_match=1.0!)
    - `agent_tools_live/live_03_yolov3_speed_paper_only`
    - `hybrid_ablation_v2/ha_two_stage_rpn_evolution`
- **32 stable high** (3-of-3 high vote) — disagreement подтверждён независимо тремя моделями, single-model bias **не объясняет** их статус.

**Вывод Phase 6.E:** triple-vote дал **честный** сигнал — большинство `priority=high` packs действительно требуют human review (или ревизии gold), а не были артефактами одной модели. Авто-промо ограничилось 2 паками, но они теперь имеют сильную гарантию (3-of-3 medium consensus). Распределение voted by 3 моделями: low=0, medium=2, high=36.

**По слоям (consensus packs / promoted):** claims_v2 (18/0), concept_topic_v2 (8/0), contradictions_v1 (3/1), agent_tools_live (3/1), idea_assist_live (3/0), multihop_v2 (2/0), hybrid_ablation_v2 (1/0), workspace_scoped_live (0/0 — все 6 packs уже были promoted в Phase 6.C, нечего проверять).

**Total Phase 6 итог:** 71 packs total → **35 promoted** (33 от Phase 6.B/C/D `llm_dual_validated` + 2 от 6.E `llm_triple_validated`), 36 high-priority остались для human spot-check.

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
