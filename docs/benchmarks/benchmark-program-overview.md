# Обзор benchmark-программы science-graphrag

Этот документ — **входная точка** для человека со стороны и для команды: что мы мерим, зачем, какие наборы данных уже есть и куда движемся. Детали разнесены по связанным файлам ниже.

## Как читать пакет документов

1. [benchmark-dataset-inventory.md](benchmark-dataset-inventory.md) — **сколько** кейсов, **где** лежат фикстуры, какие тиры (`merge_safe`, `nightly`, `live`, …).
2. [benchmark-metrics-catalog.md](benchmark-metrics-catalog.md) — **какие метрики** у каждой семьи, что они означают, **какие значения** сейчас в сводке.
3. [benchmark-metrics-values.md](benchmark-metrics-values.md) — **таблицы чисел** по кейсам (F1, ROUGE-поля, graph P/R/F1 и т.д.; генерируется скриптом).
4. [benchmark-roadmap-ir-extraction.md](benchmark-roadmap-ir-extraction.md) — план по **чётким** задачам извлечения (как «IR с F1»).
5. [benchmark-roadmap-fuzzy-eval.md](benchmark-roadmap-fuzzy-eval.md) — план по **нечёткой** оценке (ROUGE, затем LLM-as-a-judge).
6. [../runbooks/benchmark-roadmap-checklist.md](../runbooks/benchmark-roadmap-checklist.md) — **чеклисты** для ежедневной работы.
7. [../runbooks/benchmark-gold-enrichment.md](../runbooks/benchmark-gold-enrichment.md) — обогащение **layer-1 gold** (regex + LLM, пилот → apply).

Уже существующие «канонические» документы не отменяются: стратегия, runbooks, спеки семейств — см. раздел «Ссылки на первоисточники».

## Зачем нам бенчмарки

Мы хотим развивать граф, извлечение и RAG **не на ощущениях**, а на воспроизводимых прогонах: есть эталон (`gold`), есть прогон, есть отчёт, есть порог «можно ли идти дальше».

Для этого в проекте разделены:

- **Core (жёсткий decision gate)** — то, что сейчас влияет на `GO / NO-GO` в сводке [`eval/results/benchmark-metrics-summary.md`](../../eval/results/benchmark-metrics-summary.md).
- **Advisory** — полезные сигналы качества, но **намеренно** не роняют основной gate, пока политика не изменится.

Подробнее: [../runbooks/benchmark-program-status.md](../runbooks/benchmark-program-status.md), [../runbooks/benchmark-decision-gate.md](../runbooks/benchmark-decision-gate.md).

## Полосы прогонов (lanes): reference, nightly, advisory

| Lane | Что это | Где смотреть | Комментарий |
|------|---------|--------------|-------------|
| **Reference** | Один стабильный кейс **YOLOv1** (merge_safe): layer-1 + graph + layer-2 semantic | три JSON в `eval/results/current-reference-*.json` | Регрессия «сдвинули промпт / пайплайн». Отпечатки промптов **могут отличаться** от nightly — это нормально, сравнивайте только внутри lane. |
| **Nightly** | Корпус **~30 real-PDF** (layer-1 `nightly_heavy`) и **~31** semantic (layer-2 `nightly_semantic`) | `current-llm-layer1-*.json`, `current-llm-layer2-*.json` | Основной сигнал по корпусу. Layer-1 authoritative: `--threshold-profile reporting_skip_f1_gates` ([benchmark-decision-gate.md](../runbooks/benchmark-decision-gate.md)) — Wave M: **контракт** включает `min_authorship_names_f1=0.7`, `min_sample_arxiv_f1=0.85`, `reference_count_range_factor=0.3`, `min_abstract_prefix_containment=0.7`; метрики `count_ok` / ROUGE-L остаются в JSON. |
| **Advisory** | Retrieval, claims, references resolution | секции в `benchmark-metrics-summary.md` | Не входят в `decision` (GO / NO-GO), пока политика не изменится. |

Полный **decision gate** (GO / CONDITIONAL-GO / NO-GO): только [`eval/results/benchmark-metrics-summary.json`](../../eval/results/benchmark-metrics-summary.md) после `scripts/aggregate_benchmark_metrics.py`.

## Семейства бенчмарков одной таблицей

| Семейство | Что измеряем по-человечески | Где фикстуры | Роль сейчас | Где метрики и детали |
|-----------|----------------------------|--------------|-------------|----------------------|
| **Layer-1** | Насколько из текста статьи достаётся «скелет» работы: заголовок, год, DOI/arXiv, авторы, аффилиации, список ссылок | `tests/fixtures/benchmarks/layer1/` | **Core** | [benchmark-metrics-catalog.md](benchmark-metrics-catalog.md) |
| **Graph** | После ingest: связи в Neo4j, цитирование, дедуп-сигналы, ожидания по графу | те же `layer1` кейсы + `graph_expectations` в `gold.json` | **Core** | каталог + `docs/benchmarks/graph-level-eval-v1.md` |
| **Layer-2 semantic** | Узкий научный слой онтологии v1: **Method** и **Dataset** из текста | `tests/fixtures/benchmarks/layer2/` | **Core** | каталог + `docs/benchmarks/strategy-v1.md` |
| **Retrieval** | Ответ `POST /v1/query`: попали ли нужные чанки, есть ли след (`trace`), отпечатки чанков | `tests/fixtures/benchmarks/retrieval/` | **Advisory** | каталог + `docs/benchmarks/retrieval-eval-v1.md` |
| **Claims** | Задел под **утверждения из текста** (см. ниже) до полноценного графа `Claim`/`Evidence` | `tests/fixtures/benchmarks/claims/` | **Advisory** | каталог + `docs/benchmarks/ontology-claims-benchmark-v1.md` |
| **References resolution (v1 harness)** | Задел под «строка библиографии → канонический ключ» | `tests/fixtures/benchmarks/references_resolution/` | **Advisory** | каталог + `docs/specs/benchmark-family-references-resolution-v1.md` |
| **References harness (bibliography tooling)** | Отдельный контур сегментации/проверок библиографии на подмножестве layer1-кейсов | тиры в `tests/fixtures/benchmarks/layer1/case_tiers.json` | **Инструментальный / не gate** | код `eval/references_harness/` |

## Снимок «как сейчас» (по committed сводке)

Источник: [`eval/results/benchmark-metrics-summary.md`](../../eval/results/benchmark-metrics-summary.md) (генерируется `scripts/aggregate_benchmark_metrics.py`).

Актуальные поля `decision`, `failed_count` и advisory-блоки — **только в этом файле** после последнего прогона и агрегации. Обзор не дублирует числа, чтобы не расходиться с JSON.

Важно: **зелёный advisory** не означает автоматически «модель идеально понимает текст ответа» — у retrieval и claims часть прогонов **структурные** или **harness**, см. каталог метрик. Для retrieval добавлен опциональный слой **ROUGE-L ответа** (`answer_reference_text` / `min_answer_rouge_l` в gold), см. `eval/retrieval/metrics.py`.

## Что такое claims

**Claims** — это **утверждения из текста статьи**, которые мы хотим хранить как отдельные объекты (типа: «метод X быстрее Y на датасете Z»), с привязкой к источнику, чтобы потом строить evidence, сравнение работ и проверяемые ответы в RAG.

Сейчас в продуктовом ingestion claims **ещё не извлекаются «боевым» экстрактором** (стоит заглушка), а бенчмарк семьи `claims` держит **контракт и регрессии** на frozen gold. Подробности: `docs/specs/ontology-claims-v1.md`, `docs/benchmarks/ontology-claims-benchmark-v1.md`.

## Что уже «зрелое», а что пока scaffold

- **Зрелее всего:** связка **layer1 + graph + layer2** как core gate и большой корпус **~30 real-PDF** кейсов в `nightly_heavy` (плюс merge_safe эталоны).
- **Scaffold / следующий уровень:** `claims` (пока harness), `references_resolution` (synthetic harness), расширение в сторону **текстовой** оценки ответов и LLM-judge — см. roadmap-файлы.

## Ссылки на первоисточники

- Статус программы: [../runbooks/benchmark-program-status.md](../runbooks/benchmark-program-status.md)
- Правила GO/NO-GO: [../runbooks/benchmark-decision-gate.md](../runbooks/benchmark-decision-gate.md)
- Индекс старых benchmark-доков: [README.md](README.md)
- Стратегия eval: [strategy-v1.md](strategy-v1.md)
- Как расширять корпус: [benchmark-expansion-v1.md](benchmark-expansion-v1.md)
- Политика расширения онтологии: [../runbooks/benchmark-ontology-expansion-policy.md](../runbooks/benchmark-ontology-expansion-policy.md)
- Промоушен advisory → stronger gate: [../runbooks/benchmark-family-promotion-review.md](../runbooks/benchmark-family-promotion-review.md)
- Команды прогонов: [`eval/README.md`](../../eval/README.md)
