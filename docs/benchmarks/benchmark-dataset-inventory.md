# Инвентарь benchmark-датасетов (фикстуры)

Здесь — **учёт наборов кейсов** в репозитории: сколько папок с эталоном, какие **тиры** (подмножества для CI / nightly / live), откуда взяты тексты. Это не «внешний датасет Kaggle», а **наши frozen fixtures** под регрессии.

## Сводная таблица

| Корень фикстур | Файл эталона | Всего кейсов (папок) | Основные тиры | Комментарий |
|----------------|--------------|----------------------|---------------|---------------|
| `tests/fixtures/benchmarks/layer1/` | `gold.json` | **34** | `merge_safe` (**4**), `nightly_heavy` (**30**), плюс списки `references_benchmark_*` | ~30 статей — это `*_realpdf` в `nightly_heavy`; плюс merge_safe (в т.ч. `yolov1` markdown) |
| `tests/fixtures/benchmarks/layer2/` | `semantic_gold.json` | **32** | `smoke` / `merge_safe` (**1**), `nightly_semantic` (**31**) | Семантика к статьям из layer1 + смок `no_llm_smoke` |
| `tests/fixtures/benchmarks/retrieval/` | `gold.json` | **12** | `smoke` (**4**: mock contract + stub), `merge_safe_contract` (**3**), `strict_pilot` (**3**), `live_corpus_mini` (**5**) | `smoke` = contract-only mock; measurement — `strict_pilot` / `live_corpus_mini` |
| `tests/fixtures/benchmarks/claims/` | `gold.json` | **16** | `smoke` (**1**), см. `case_tiers.json` ниже | `claims_contract_shape` — smoke; остальное — advisory packs |
| `tests/fixtures/benchmarks/references_resolution/` | `gold.json` | **4** | `refs_merge_contract` (**1**), `refs_mini` (**3**), `refs_graph_stub` (**3**, дублирует mini) | Synthetic harness; тир `refs_graph_stub` — заготовка под graph-backed lane (см. runbook) |

Числа **34 / 32 / 12 / 16 / 4** получены подсчётом файлов эталонов в дереве на момент составления документа.

## Layer-1 (`tests/fixtures/benchmarks/layer1/`)

### Назначение

Каждый кейс — это `article.md` + `gold.json`: эталон того, что должно извлечься на **первом слое** (метаданные, авторы, ссылки, …) и что ожидается на графе (`graph_expectations`).

### Тиры (`case_tiers.json`)

Файл: [`tests/fixtures/benchmarks/layer1/case_tiers.json`](../../tests/fixtures/benchmarks/layer1/case_tiers.json).

| Тир | Размер | Смысл |
|-----|--------|--------|
| `smoke` | **4** (дублирует состав `merge_safe`) | Явная метка **contract / smoke** — не путать с measurement-корпусом; runbook: [benchmark-gold-enrichment.md](../runbooks/benchmark-gold-enrichment.md) |
| `merge_safe` | **4** | Быстрые и предсказуемые кейсы для коротких прогонов |
| `nightly_heavy` | **30** | Большие тексты из **реальных PDF→MD** (`*_realpdf`) — основной «корпус ~30 статей» для ночных прогонов |
| `references_benchmark_v1` | **15** | Подмножество layer1-кейсов для отдельного references-harness контура |
| `references_benchmark_full` | **34** | Расширенный список под тот же контур (по факту покрывает все layer1 `case_id` из тира) |

### Происхождение данных

- **`*_realpdf`**: корпус object-detection, скрипты и описание — `docs/benchmarks/object-detection-corpus.md`, инвентарь PDF↔case_id — `docs/benchmarks/object-detection-inventory.md`.
- **`yolov1`**, `doi_refs_heavy`, `arxiv_refs_heavy`, `noisy_layout_stub`**: специализированные эталоны под типовые сбои вёрстки/ссылках.

### Связанный код (не отдельная папка фикстур)

`eval/references_harness/` — вспомогательный контур на **тех же** layer1-статьях (сегментация библиографии и т.п.), тиры задаются в `case_tiers.json`.

## Layer-2 semantic (`tests/fixtures/benchmarks/layer2/`)

### Назначение

Эталон для извлечения **Method / Dataset** (ontology v1) из текста статьи.

### Тиры (`case_tiers.json`)

Файл: [`tests/fixtures/benchmarks/layer2/case_tiers.json`](../../tests/fixtures/benchmarks/layer2/case_tiers.json).

| Тир | Размер |
|-----|--------|
| `merge_safe` | **1** (`no_llm_smoke`) |
| `nightly_semantic` | **31** |

Тексты подтягиваются из соответствующих layer1-кейсов (см. `eval/README.md`).

## Retrieval (`tests/fixtures/benchmarks/retrieval/`)

### Назначение

Проверка **контракта** ответа `POST /v1/query`: trace, citations, иногда отпечатки чанков, иногда scope по `work_id`.

### Тиры (`case_tiers.json`)

Файл: [`tests/fixtures/benchmarks/retrieval/case_tiers.json`](../../tests/fixtures/benchmarks/retrieval/case_tiers.json).

| Тир | Размер | Режим данных |
|-----|--------|----------------|
| `merge_safe_contract` | **3** | Часто прогоняется с **`--mock-answer`** в CI (см. `eval/README.md`) |
| `strict_pilot` | **3** | То же по смыслу «контракт + fingerprints», пока часто mock |
| `live_corpus_mini` | **5** | **Живой** стек (нужны ingest + Qdrant + API), без mock |

Документ по live-tier: `docs/benchmarks/retrieval-live-tier-v1.md`.

## Claims (`tests/fixtures/benchmarks/claims/`)

### Назначение

Задел под **epistemic / claims** слой: список ожидаемых утверждений в `gold.json` и метрики покрытия.

### Тиры (`case_tiers.json`)

Файл: [`tests/fixtures/benchmarks/claims/case_tiers.json`](../../tests/fixtures/benchmarks/claims/case_tiers.json).

| Тир | Размер | Комментарий |
|-----|--------|----------------|
| `claims_merge_contract` | **1** | Дешёвый контракт |
| `claims_mini` | **5** | Мини-пак на выдержках из `layer1/yolov1` |
| `claims_corpus_v2_mini` | **5** | Выдержки из разных `*_realpdf` |
| `claims_pilot` | **10** | Расширенный пилотный пакет |
| `claims_pilot_train` | **8** | Пилот без кейсов с `benchmark_holdout: true` |

README фикстур: `tests/fixtures/benchmarks/claims/README.md`.

## References resolution (`tests/fixtures/benchmarks/references_resolution/`)

### Назначение

Проверка сопоставления **`raw_citation_span_id` → `canonical_key`** (DOI / arXiv / `work_id` и т.д.).

### Тиры

Файл: [`tests/fixtures/benchmarks/references_resolution/case_tiers.json`](../../tests/fixtures/benchmarks/references_resolution/case_tiers.json).

| Тир | Размер | Комментарий |
|-----|--------|-------------|
| `refs_merge_contract` | **1** | Контрактная форма |
| `refs_mini` | **3** | Мини-пак; пока **synthetic_predictions** внутри `gold.json` |
| `refs_graph_stub` | **3** | Те же три кейса, что `refs_mini`; в gold добавлено поле **`graph_stub_predictions`** (пока копия synthetic) — прогон с `--graph-stub-lane` у раннера |

Runbook: [../runbooks/benchmark-references-resolution-graph-lane.md](../runbooks/benchmark-references-resolution-graph-lane.md).

## Что из этого «под F1», а что «под fuzzy»

- **Ближе к чётким IR-style метрикам:** layer1 (идентификаторы, множества), graph (ожидаемые рёбра/счётчики), layer2 (имена сущностей), references_resolution (ключи), claims по `claim_id` / нормализованному тексту.
- **Ближе к fuzzy / текстовой оценке:** опционально **ROUGE-L ответа** в retrieval (`answer_reference_text` + `min_answer_rouge_l` в `gold.json`, см. `eval/retrieval/metrics.py`); «эквивалентность» claims формулировками, hypothesis/idea-assist — см. [benchmark-roadmap-fuzzy-eval.md](benchmark-roadmap-fuzzy-eval.md).

Дальше: [benchmark-metrics-catalog.md](benchmark-metrics-catalog.md).
