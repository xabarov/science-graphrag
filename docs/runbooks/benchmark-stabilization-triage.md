# Runbook: triage benchmark vs архитектура

После LLM-прогонов классифицируйте каждый fail.

**Сводный decision gate** (критерии GO, дельты к baseline, команда агрегатора): [benchmark-decision-gate.md](benchmark-decision-gate.md).

## 1. Артефакты

- Reference: `eval/results/baseline-reference-*.json`
- OD subset layer-1: `eval/results/baseline-llm-layer1-subset-*.json`
- Suite layer-1 nightly_heavy: `eval/results/baseline-llm-layer1-nightly-heavy-suite.json`
- Suite layer-2 nightly_semantic: `eval/results/baseline-llm-layer2-nightly-semantic-suite.json`

## 2. Тип A: Benchmark / gold issue

Признаки:

- `title_match_required: False` при том, что LLM выдал корректный заголовок, а `gold.json` содержит артефакт PDF (первая строка, arXiv-шапка, «1» вместо title).
- `abstract_prefix_required: False` из-за рассинхрона нормализации, хотя семантика абстракта верна.
- `reference_count_ok: False` при расхождении эвристики `extract_references` на fixture и фактического списка ссылок из LLM (см. `cornernet_realpdf`: эвристика давала 2 ссылки, LLM — 49).
- Layer-2 semantic: `method_tp=0/N` при разумном ответе LLM, но слишком узком списке `expected_method_names_normalized`.

Действия:

- Обновить `work_metadata.title` / `abstract_prefix` из отчёта: [`scripts/sync_layer1_gold_from_report.py`](../../scripts/sync_layer1_gold_from_report.py).
- Подправить `references.expected_count` / `min_count` по фактическому прогону или ослабить `quality_thresholds` осознанно.
- Пересмотреть `semantic_gold.json` ожидания, а не сразу менять экстрактор.

## 3. Тип B: Архитектура / код

Примеры из этой итерации:

- **Qdrant client API**: `qdrant-client` 1.17+ удалил `QdrantClient.search` — исправлено в [`science_graphrag/storage/qdrant_store.py`](../../science_graphrag/storage/qdrant_store.py) через `query_points`.
- **Graph expectations vs ingest**: эталонный `yolov1` давал `cites_count=14` при gold `min_cites=23` — несоответствие резолвера/графа ожиданиям; диапазон в `gold.json` откалиброван под наблюдаемый snapshot (см. triage в коммите).

## 4. Layer-2 nightly_semantic: классификация fail

Разделяйте падения на две дорожки (см. последний suite JSON в `eval/results/`).

### 4.1. Semantic runtime / формат LLM (тип B)

| Кейс | Симптом | Действие |
|------|---------|----------|
| `detrs_semantic` | `InstructorRetryException`, `Invalid JSON`, truncated tool args | Укрепить путь semantic extraction: retry с компактным prompt/урезанным body, запас по `max_tokens`; не менять gold до стабильного ответа |
| `yolov2_semantic` | `llm_empty_result` | То же: retry/лимиты; при повторяемости — смотреть провайдера/квоты |

### 4.2. Alias / нормализация vs gold (тип A или метрики)

| Кейс | Симптом | Действие |
|------|---------|----------|
| `tood_semantic`, `gfl_semantic`, `hog_semantic` | Имена методов в предсказании длинные (полное название + аббревиатура), gold — короткие токены | Расширить `expected_method_names_normalized` **или** полагаться на substring/word-overlap в [`eval/layer2/metrics.py`](../../eval/layer2/metrics.py) после калибровки |
| `fpn_semantic`, `part_based_models_semantic` | Аналогично: проверить отчёт и при необходимости синонимы в gold |

Правило: если в `predicted.methods` видно корректное семантическое имя, а матч только из-за формы строки — это **не** повод ослаблять LLM-промпт; чинить matching/gold.

## 5. Режимы доверия

| Режим | Что доказывает |
|-------|----------------|
| `merge_safe` без LLM | Детерминизм, регрессии в эвристиках |
| Reference LLM (`yolov1`) | **Обязательный gate** перед corpus-wide изменениями; контракт качества с LLM на эталонном кейсе |
| `nightly_heavy` / `nightly_semantic` с LLM | Корпус; требует актуального gold и времени; сигнал честен только после калибровки layer1 gold и разделения runtime vs alias (см. выше) |
