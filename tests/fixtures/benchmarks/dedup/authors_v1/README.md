# Dedup pack: authors_v1 (Layer 8 of Corpus Gold Pack v1)

**Дата:** 2026-04-25
**Тип:** dedup gold (entity_type=author), для **BT11** (см. `docs/analysis/ontology-benchmarks-trust-audit-2026-04-25.md` §5).
**Статус:** `draft` — записи собраны вручную из corpus catalog (`tests/fixtures/corpus/CATALOG.md` §4); требуется LLM dual-pass + spot-check.
**Спека:** [`../../../../../docs/specs/benchmark-gold-schemas-v1.md`](../../../../../docs/specs/benchmark-gold-schemas-v1.md) §9.

Этот pack — **образцовый**: на нём отрабатываются формат и runner, далее тиражируется на 4 других типа (institutions, venues, methods, datasets — см. `docs/analysis/corpus-gold-pack-v1-2026-04-25.md` §3.9).

---

## 1. Содержание

`gold.json` — 19 записей `records[]`, 6 кластеров `clusters[]`, 4 пары `negative_pairs[]`.

### 1.1 Кластеры (positive — что должно мерджиться)

| cluster_id | Authors / variants | Rationale |
|------------|-------------------|-----------|
| `cluster_redmon_joseph` | Joseph Redmon ↔ J. Redmon | YOLO papers; initial-form в bib references |
| `cluster_girshick_ross` | Ross Girshick ↔ R. Girshick ↔ Ross B. Girshick | R-CNN family + FPN + RetinaNet + YOLOv1 (co-author) + DPM (middle-initial form) |
| `cluster_he_kaiming` | Kaiming He ↔ K. He | SPPNet/Faster/Mask R-CNN/FPN/RetinaNet/R-FCN |
| `cluster_sun_jian` | Jian Sun ↔ J. Sun | SPPNet/Faster/R-FCN, позже YOLOX (MEGVII) |
| `cluster_dai_jifeng` | Jifeng Dai ↔ J. Dai | R-FCN, Deformable DETR |
| `cluster_lin_tsung_yi` | Tsung-Yi Lin ↔ T.-Y. Lin | FPN, RetinaNet (hyphenated-initial BibTeX form) |

### 1.2 Negative pairs (что **не** должно мерджиться — gate `false_merge_count = 0`)

| pair_id | Pair | Rationale |
|---------|------|-----------|
| `neg_zhang_xiangyu_vs_xinyu` | Xiangyu Zhang ↔ Xinyu Zhang | Разные имена, оба сворачиваются в `X. Zhang` на initial-matching |
| `neg_zhang_x_initial_unresolvable` | X. Zhang (без контекста) ↔ Xiangyu Zhang | Initial-only без affiliation/coauthors — должен идти в human review, а не auto-merge |
| `neg_lin_tsung_yi_vs_dahua` | Tsung-Yi Lin ↔ Dahua Lin | Разные люди с одинаковой фамилией; Tsung-Yi — FPN/RetinaNet (FAIR), Dahua — Libra R-CNN (CUHK) |
| `neg_feng_li_dn_detr_vs_unrelated` | Feng Li (DN-DETR cohort) ↔ Feng Li (unrelated) | Распространённое имя; для мерджа требуется coauthor-signature |

### 1.3 Что **намеренно** не покрыто в v1

- Транслитерация (например, kanji ↔ romaji) — нет в этом корпусе; будет добавлено для broader-corpus pack v2.
- ORCID-tie — большинство OD-статей не публикуют ORCID в bibliography; покрытие будет в pack v2.
- Suffix формы (Jr., Sr., II) — нет в корпусе.

---

## 2. Метрики (ожидаются от runner BT11)

| Метрика | Формула | Gate (advisory) |
|---------|---------|------------------|
| `pairwise_precision` | TP / (TP + FP), где FP — пары из `negative_pairs`, ошибочно объединённые | ≥ 0.9 |
| `pairwise_recall` | TP / (TP + FN), пары внутри `clusters` | ≥ 0.8 |
| `cluster_purity` | Σ max(\|cluster_i ∩ predicted_j\|) / N | ≥ 0.85 |
| `auto_merge_rate` | auto_merged_pairs / total_pairs_examined | report only (для оценки workload) |
| `false_merge_count` | количество merge на `negative_pairs` | **= 0** (gate) |

---

## 3. Acceptance pack'а

- [ ] LLM-dual extractor pass → `consistency_report.json` с list disagreements.
- [ ] Spot-check всех `clusters[].entity_ids` и `negative_pairs[].entity_ids` (особенно «J. Smith vs J. Smith»-аналоги в этом pack — Xinyu vs Xiangyu Zhang, Dahua vs Tsung-Yi Lin).
- [ ] Расширение records[] до **≥ 25 записей** (сейчас 19): добавить ≥ 1 ORCID-tied positive (если найдём в новых статьях) и ≥ 1 transliteration/diacritic кейс (Piotr Dollár — без диакритики vs с).
- [ ] Проставить `meta.validation_status: "human_spot_checked"`.
- [ ] Создать `consistency_report.json` (см. [§11.1 schema](../../../../../docs/specs/benchmark-gold-schemas-v1.md#111-consistency_reportjson-рядом-с-каждым-goldjson)).

---

## 4. Шаблон для остальных dedup типов

Структура полностью совпадает; меняется только `entity_type` и `context_attributes`:

| Pack | `entity_type` | Specific `context_attributes` |
|------|--------------|-------------------------------|
| `dedup/institutions_v1/` | `institution` | `country`, `ror_id`, `parent_institution_id` |
| `dedup/venues_v1/` | `venue` | `venue_year`, `venue_kind` (conference/journal/workshop) |
| `dedup/methods_v1/` | `method` | `introduced_in_corpus_work_id`, `task` |
| `dedup/datasets_v1/` | `dataset` | `version`, `task` |

Все используют один и тот же runner (`eval/dedup/<type>_runner.py`) с типо-параметризованным embed + threshold + LLM-judge (см. план §3.9).

---

## 5. Ссылки

- План: [`../../../../../docs/analysis/corpus-gold-pack-v1-2026-04-25.md`](../../../../../docs/analysis/corpus-gold-pack-v1-2026-04-25.md) §3.9
- Schema: [`../../../../../docs/specs/benchmark-gold-schemas-v1.md`](../../../../../docs/specs/benchmark-gold-schemas-v1.md) §9
- Trust audit (мотивация): [`../../../../../docs/analysis/ontology-benchmarks-trust-audit-2026-04-25.md`](../../../../../docs/analysis/ontology-benchmarks-trust-audit-2026-04-25.md) §3.9 + BT11
- Source authors (corpus catalog): [`../../../../corpus/CATALOG.md`](../../../../corpus/CATALOG.md) §4
