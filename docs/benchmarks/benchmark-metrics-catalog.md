# Каталог метрик benchmark-программы

Здесь разделены **смысл метрик** (что считаем) и **текущие зафиксированные значения** из committed сводки. Исходники формул — в `eval/*/metrics.py` и в JSON-отчётах прогонов.

## Где лежат «официальные» числа

| Артефакт | Назначение |
|----------|------------|
| [`eval/results/benchmark-metrics-summary.md`](../../eval/results/benchmark-metrics-summary.md) | Человекочитаемая сводка для gate и advisory |
| [`eval/results/benchmark-metrics-summary.json`](../../eval/results/benchmark-metrics-summary.json) | Машинный снимок: пути к артефактам, `failed_count`, роли семейств |
| `eval/results/current-*.json` | Сырые отчёты по suite / кейсу (перечислены в `authoritative_artifacts` внутри JSON-сводки) |
| [benchmark-metrics-values.md](benchmark-metrics-values.md) | **Таблицы числовых метрик** (F1, ROUGE-поля, recall/precision по кейсам) — генерируется из тех же JSON |

Сводка генерируется: `scripts/aggregate_benchmark_metrics.py`. Таблицы значений: `scripts/generate_benchmark_metrics_tables.py`.

---

## Layer-1 (извлечение «скелета» работы)

**Код:** [`eval/layer1/metrics.py`](../../eval/layer1/metrics.py), спека порогов — `eval/layer1/spec.py`.

### Что мерим

- **Метаданные** (`title`, `year`, `venue`, DOI/arXiv в тексте работы, префикс abstract и т.д.) — смесь **жёстких** проверок и **нормализации** строк.
- **Авторство** — множества имён / аффилиаций; где уместно — token-level F1, difflib-макро по авторам, ROUGE-L F1 для длинных полей (см. импорты `rouge_l_f1`, `multiset_token_f1` в `metrics.py`).
- **Ссылки (`ReferenceDraft`)** — множества идентификаторов (DOI, arXiv из текста сырой ссылки и полей), micro **P/R/F1** по пересечению множеств (`prf1_tp_fp_fn`).
- **Контракт** — булевы проверки структуры и обязательных полей в `gold.json` (пороги в `Layer1QualityThresholds`).

### Как читать отчёт

- Агрегаты по suite: `failed_count`, `all_passed`, гистограммы источников (`metadata_source`, `references_source`, …).
- Доп. сигнал: **`references_llm_failed_events`** — сколько раз упал LLM-контур на ссылках (не обязательно = провал кейса, но важный сигнал деградации).

---

## Graph (после ingest)

**Код:** [`eval/graph_v1/metrics.py`](../../eval/graph_v1/metrics.py).

### Что мерим

- **Ожидания по графу** из `gold.graph_expectations` (если блок задан):
  - **P/R/F1** по множеству `expected_cited_arxiv_ids` vs фактические `cited_arxiv_ids` в снимке Neo4j (те же `prf1_tp_fp_fn`, что в layer1).
  - **Диапазоны и инварианты:** число `cites`, `authorships`, `institutions`, лимиты на «лишние» fingerprint-дубликаты работ, нарушения dedup, число рёбер «связанных версий» — всё как **range / cap checks**.

### Как читать отчёт

- Если `graph_expectations` нет — кейс помечается как без графовых ожиданий (`has_expectations: false`), проверки не давят на gate.

---

## Layer-2 semantic (Method / Dataset)

**Код:** [`eval/layer2/metrics.py`](../../eval/layer2/metrics.py).

### Что мерим

- **Recall-oriented** покрытие gold-строк предсказанными именами/алиасами с порогом уверенности.
- **Precision** по предсказанным токенам (штраф за лишние сущности).
- Матчинг намеренно **не только exact**: допускаются вложенность коротких фраз, Jaccard по словам для длинных названий (см. `_gold_matches_pred_token`).

### Как читать отчёт

- Поля вида `precision_methods`, `recall_methods_num` / `recall_methods_denom`, аналогично для datasets, итог `passed` по порогам спеки.

---

## Retrieval (`POST /v1/query`)

**Код:** [`eval/retrieval/metrics.py`](../../eval/retrieval/metrics.py).

### Что мерим сейчас

Структурные сигналы **grounding**; опционально — **ROUGE-L** по тексту ответа.

| Сигнал | Смысл |
|--------|--------|
| `hit_count` vs `min_hit_count` | Достаточно ли чанков попало в trace |
| `required_chunk_fingerprints` | Каждый требуемый fingerprint должен встретиться среди citation chunk fingerprints |
| `work_id` | Соответствие `retrieval_trace.filter_work_id` эталону (scoped прогоны) |
| `contract_only` | Только форма trace + список citations (дешёвый smoke) |
| `answer_reference_text` | (Опционально) эталонный фрагмент для сравнения с полем `answer` |
| `answer_rouge_l` | ROUGE-L F1 между `answer_reference_text` и ответом (если эталон задан) |
| `min_answer_rouge_l` | (Опционально) порог: при заданном эталоне ответ должен набрать ≥ порога, иначе `passed=false` |

### Ограничение (важно для интерпретации)

Полноценный LLM-judge и богатый корпус текстовых эталонов — в [benchmark-roadmap-fuzzy-eval.md](benchmark-roadmap-fuzzy-eval.md). В committed артефактах поля `answer_reference_text` могут отсутствовать — тогда оценка остаётся структурной.

---

## Claims (ontology claims v1)

**Код:** [`eval/claims/metrics.py`](../../eval/claims/metrics.py).

### Что мерим

| Метрика | Смысл |
|---------|--------|
| `claim_recall` | Доля эталонных `expected_claims`, для которых найдено совпадение по режиму матчинга |
| `claim_precision` | Доля предсказаний, которые «привязаны» к какому-либо эталонному ряду |
| `claim_match_mode` | `claim_id` (строго) или `claim_id_or_normalized_text` (подстрока по нормализованному тексту) |
| `min_claim_recall` | Порог из gold; `passed` если recall ≥ порога |
| `contract_only` | Только проверка формы payload |

### Экстрактор (harness vs production)

По умолчанию CLI использует **anchor harness** (`extract_claims_anchor_harness`). Путь ingestion: **`--extractor production`** → `science_graphrag.ingestion.claims.stub.extract_claims_stub` (пока заглушка). Политика и holdout: [../runbooks/benchmark-claims-extractor-policy.md](../runbooks/benchmark-claims-extractor-policy.md).

### Ограничение

Семья **advisory**; прогон идёт через **deterministic harness** (список предсказаний сравнивается с gold), а не через полный production-pipeline извлечения claims из графа. Это осознанный этап Wave H1.

---

## References resolution (v1 harness)

**Код:** [`eval/references_resolution/metrics.py`](../../eval/references_resolution/metrics.py).

### Что мерим

| Метрика | Смысл |
|---------|--------|
| `resolution_recall` | Доля `expected_resolutions`, где `(raw_citation_span_id → canonical_key)` совпал с предсказанием |
| `resolution_precision` | Среди уникальных предсказанных span_id — доля верно сопоставленных |
| `min_resolution_recall` | Порог из gold |
| `contract_only` | Все предсказания — непустые dict с обоими ключами |

### Ограничение

Пока это **structural scoring harness**; не заменяет полноценный graph-backed resolver в Neo4j. Заготовка lane: **`--graph-stub-lane`** + поле `graph_stub_predictions` в gold (см. [../runbooks/benchmark-references-resolution-graph-lane.md](../runbooks/benchmark-references-resolution-graph-lane.md)). Спека: [`docs/specs/benchmark-family-references-resolution-v1.md`](../specs/benchmark-family-references-resolution-v1.md).

---

## References harness (библиография, отдельный контур)

**Код:** [`eval/references_harness/metrics.py`](../../eval/references_harness/metrics.py).

Инструментальные метрики на подмножестве layer1-кейсов (тиры в `layer1/case_tiers.json`). **Не** смешивать с семьёй `references_resolution` в сводке gate.

---

## Committed current values (снимок сводки)

Ниже — состояние на момент последней генерации [`eval/results/benchmark-metrics-summary.md`](../../eval/results/benchmark-metrics-summary.md). При обновлении артефактов перегенерируйте сводку и правьте документ только если меняется **смысл** метрик, не вручную числа.

### Decision gate (core)

| Поле | Значение |
|------|----------|
| `decision` | `GO` |
| `reason` | `all_nightly_passed` |
| Reference lane (YOLOv1): layer1 + graph + layer2_semantic | все **`passed=True`** |
| Layer-1 nightly (`nightly_heavy`, 30 кейсов) | `failed_count` = **0** |
| Layer-2 nightly (`nightly_semantic`, 31 кейс в отчёте) | `failed_count` = **0** |
| `references_llm_failed_events` (layer1 nightly) | **4** (диагностический счётчик) |

### Advisory families

| Блок | Сводка |
|------|--------|
| Retrieval: `merge_safe_contract_mock`, `strict_pilot_mock`, `live_corpus_mini` | все `all_passed=True`, `failed_count=0` |
| Claims: contract + mini + corpus_v2_mini + pilot | все `all_passed=True`, `failed_count=0` |
| References resolution: contract + mini | все `all_passed=True`, `failed_count=0` |

### Baseline deltas

В JSON/MD сводки есть секция **`deltas`**: сравнение текущего nightly с сохранённым baseline по спискам упавших кейсов (`resolved` / `new_regressions`). Используйте для отчётов о прогрессе, не как отдельную «метрику продукта».

---

## Навигация

- Состав датасетов: [benchmark-dataset-inventory.md](benchmark-dataset-inventory.md)
- IR-roadmap: [benchmark-roadmap-ir-extraction.md](benchmark-roadmap-ir-extraction.md)
- Fuzzy-roadmap: [benchmark-roadmap-fuzzy-eval.md](benchmark-roadmap-fuzzy-eval.md)
