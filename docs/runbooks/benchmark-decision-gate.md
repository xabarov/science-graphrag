# Runbook: decision gate по метрикам benchmark

Цель: одним взглядом понять, **можно ли переходить к следующим шагам roadmap**, и какие блокеры остались (gold vs код vs runtime LLM).

## 1. Авторитетные артефакты (текущий прогон)

Используйте **эти** JSON как источник истины для gate (имена могут совпадать с `baseline-*`, но приоритет у последнего локального `current-*`):

| Lane | Файл |
|------|------|
| Reference layer-1 | [`eval/results/current-reference-layer1-yolov1.json`](../../eval/results/current-reference-layer1-yolov1.json) |
| Reference graph | [`eval/results/current-reference-graph-yolov1.json`](../../eval/results/current-reference-graph-yolov1.json) |
| Reference layer-2 semantic | [`eval/results/current-reference-layer2-yolov1-semantic.json`](../../eval/results/current-reference-layer2-yolov1-semantic.json) |
| Nightly layer-1 (`nightly_heavy`) | [`eval/results/current-llm-layer1-nightly-heavy-suite-after-prompt-fix.json`](../../eval/results/current-llm-layer1-nightly-heavy-suite-after-prompt-fix.json) |
| Nightly layer-2 (`nightly_semantic`) | [`eval/results/current-llm-layer2-nightly-semantic-suite.json`](../../eval/results/current-llm-layer2-nightly-semantic-suite.json) |

Для сравнения с предыдущим зафиксированным baseline в репозитории:

- [`eval/results/baseline-llm-layer1-nightly-heavy-suite.json`](../../eval/results/baseline-llm-layer1-nightly-heavy-suite.json)
- [`eval/results/baseline-llm-layer2-nightly-semantic-suite.json`](../../eval/results/baseline-llm-layer2-nightly-semantic-suite.json)

## 2. Автоматическая сводка

После прогонов обновите агрегированный отчёт:

```bash
.venv/bin/python scripts/aggregate_benchmark_metrics.py
```

### Перегенерация authoritative layer-1 nightly (`nightly_heavy`)

После изменений в `gold.json` (в т.ч. enrichment авторов / `quality_thresholds`) переснимите suite и агрегатор:

```bash
.venv/bin/science-graphrag-layer1-benchmark tests/fixtures/benchmarks/layer1 \
  --suite --tier nightly_heavy \
  --threshold-profile reporting_skip_f1_gates \
  --json-out eval/results/current-llm-layer1-nightly-heavy-suite-after-prompt-fix.json
.venv/bin/python scripts/aggregate_benchmark_metrics.py
.venv/bin/python scripts/generate_benchmark_metrics_tables.py
```

Профиль **`reporting_skip_f1_gates`** (Wave M): выставляет в контракте **`min_authorship_names_f1=0.7`**, **`min_sample_arxiv_f1=0.85`**, **`require_reference_count_ok=False`**, **`reference_count_range_factor=0.3`** (допустимый диапазон числа ссылок вокруг `expected_count`), **`require_abstract_prefix=False`**, **`min_abstract_prefix_containment=0.7`** (token containment префикса в полном abstract вместо хрупкого ROUGE-L gate). Метрики `count_ok`, ROUGE-L и F1 по-прежнему пишутся в JSON для диагностики.

Появятся:

- [`eval/results/benchmark-metrics-summary.json`](../../eval/results/benchmark-metrics-summary.json) — machine-readable;
- [`eval/results/benchmark-metrics-summary.md`](../../eval/results/benchmark-metrics-summary.md) — краткий human-readable (в т.ч. **decision** и дельты к baseline).

## 3. Критерии GO / CONDITIONAL-GO / NO-GO

- **NO-GO**: не зелёна **reference lane** (`yolov1` layer1 + graph + layer2 semantic), или отсутствуют ключевые JSON-артефакты.
- **CONDITIONAL-GO**: reference зелёная, но **nightly** ещё содержит fail — допустимо для движения по roadmap **если** каждый fail классифицирован (см. ниже) и нет необъяснимых регрессий относительно baseline.
- **GO** (строгий): reference зелёная и **оба** nightly suite полностью `all_passed` в JSON.

Поле `decision` в `benchmark-metrics-summary.json` кодирует это правило автоматически.

## 4. Классификация остаточных fail

| Тип | Признаки в JSON | Типичный фикс |
|-----|-----------------|---------------|
| Benchmark / gold | `abstract_prefix_required: false` при согласованном title; `reference_count_ok` при устаревшем `expected_count` в gold | обновить `gold.json`, `sync_layer1_gold_from_report.py` |
| Architecture / runtime | `llm_failed`, `llm_empty_result`, `InstructorRetryException` в `extraction_notes` / логах | retry, промпты, лимиты токенов, устойчивость instructor |
| Смешанный | suite красный, но single-case retest зелёный после правки gold | перепрогнать suite после коммита gold |

## 5. Снимок состояния (по последней генерации summary)

Актуальные цифры всегда в [`benchmark-metrics-summary.md`](../../eval/results/benchmark-metrics-summary.md). На момент введения runbook типичный паттерн был:

- **Reference**: все три кейса `passed`.
- **Layer-1 nightly**: после синхронизации layer-1 gold и authoritative rerun suite — `failed_count: 0`; при этом `references_llm_failed_events` может оставаться > 0 за счёт fallback на heuristic.
- **Layer-2 nightly**: после `nano_retry` suite `nightly_semantic` зелёный (`failed_count: 0`); single-case retest `yolov1_semantic` также `passed=True`.

Single-case retest после правок gold (если лежат в `eval/results/retest-*.json`) агрегатор перечисляет отдельно — это подтверждение, что suite нужно **перепрогнать** после коммита фикстур.

## 6. Gate между Wave A и Wave B–D

Волны работ по roadmap описаны в [roadmap-next-waves.md](roadmap-next-waves.md). **Wave A (Phase 4)** — обязательный **decision gate** перед тем, как считать завершёнными следующие волны:

| Состояние `decision` в `benchmark-metrics-summary` | Wave B (Phase 3 semantic) | Wave C (Phase 5/6 e2e) | Wave D (Phase 7 pilot) |
|------------------------------------------------------|---------------------------|-------------------------|--------------------------|
| **NO-GO** | не начинать до зелёной reference lane и наличия артефактов | не начинать | не начинать |
| **CONDITIONAL-GO** | допускается, если каждый nightly fail **классифицирован** (gold vs runtime) и задокументирован | допускается при том же условии + осознанные риски по API/UI | допускается только с явным списком blockers в pilot package |
| **GO** | можно | можно | можно (при выполнении [pilot-checklist.md](pilot-checklist.md)) |

**Reference lane** (`yolov1`: layer-1 + graph + layer-2 semantic) должна оставаться зелёной при любых массовых изменениях gold/промптов; см. [benchmark-stabilization-baseline.md](benchmark-stabilization-baseline.md).

## 7. Связь с roadmap (параллельные треки)

Пока **reference** стабильна, допустимо **параллельно** вести документацию Phase 2, доработки ingestion и подготовку контрактов Phase 5/6 — но **закрепление** Wave B/C/D в смысле «готово к следующему этапу» опирается на таблицу выше и на сводку агрегатора. Остаточный долг nightly закрывается через gold/runtime — см. [benchmark-stabilization-triage.md](benchmark-stabilization-triage.md).

## 8. Retrieval / citation family (advisory) и связанные артефакты

Семейство `POST /v1/query` **не входит** в автоматический `decision` (GO / CONDITIONAL-GO / NO-GO): оно не может «уронить» gate при красном retrieval-only прогоне, пока политика явно не переведёт lane в blocking. **Исключение:** production **claims** lane (Wave O) после promotion участвует в `decision_gate` — см. §8.1 и `scripts/aggregate_benchmark_metrics.py`.

- **Где смотреть:** секция *Retrieval family (advisory)* в [`eval/results/benchmark-metrics-summary.md`](../../eval/results/benchmark-metrics-summary.md) (генерируется агрегатором из JSON-артефактов ниже).
- **Артефакты по умолчанию (mock, CI-safe):**
  - merge-safe contract: [`eval/results/current-retrieval-merge-safe-mock.json`](../../eval/results/current-retrieval-merge-safe-mock.json)
  - strict pilot (fingerprint gold, mock): [`eval/results/current-retrieval-strict-pilot-mock.json`](../../eval/results/current-retrieval-strict-pilot-mock.json)
- **Live mini-tier (при наличии файла):** [`eval/results/current-retrieval-live-corpus-mini.json`](../../eval/results/current-retrieval-live-corpus-mini.json) — поднимается в сводке агрегатора; по-прежнему advisory.
- **Workspace-scoped retrieval (Wave P, advisory):** [`eval/results/current-retrieval-workspace-scoped.json`](../../eval/results/current-retrieval-workspace-scoped.json) — tier `workspace_scoped`; перед live-прогоном: `scripts/seed_benchmark_workspaces.py` + Qdrant backfill; `--retrieval-workspace-scoped-json`.
- **Retrieval LLM-judge pilot (Wave P, advisory):** [`eval/results/current-retrieval-judge-pilot.json`](../../eval/results/current-retrieval-judge-pilot.json) — `science-graphrag-retrieval-judge-benchmark` поверх JSON runner; `--retrieval-judge-json`; не влияет на `decision`.
- **Claims (при наличии файлов):** [`eval/results/current-claims-merge-contract.json`](../../eval/results/current-claims-merge-contract.json), [`eval/results/current-claims-mini-suite.json`](../../eval/results/current-claims-mini-suite.json), [`eval/results/current-claims-corpus-v2-mini.json`](../../eval/results/current-claims-corpus-v2-mini.json), [`eval/results/current-claims-pilot-suite.json`](../../eval/results/current-claims-pilot-suite.json) — см. [`benchmark-pilot-advisory-runs.md`](benchmark-pilot-advisory-runs.md); **advisory** (harness / merge contract).
- **Claims — production LLM lane (Wave O, core gate):** [`eval/results/current-claims-production-pilot.json`](../../eval/results/current-claims-production-pilot.json) — `science-graphrag-claims-benchmark --suite --tier claims_pilot --extractor production`; **входит** в `decision_gate` (см. §8.1); сводка: секция *Claims production lane* в `benchmark-metrics-summary.md`; путь: `--claims-production-json`.
- **References resolution (при наличии файлов):** [`eval/results/current-references-resolution-contract.json`](../../eval/results/current-references-resolution-contract.json), [`eval/results/current-references-resolution-mini.json`](../../eval/results/current-references-resolution-mini.json) — см. [`benchmark-family-references-resolution-v1.md`](../specs/benchmark-family-references-resolution-v1.md).
- **References resolution — graph lane (Neo4j, опционально):** [`eval/results/current-references-resolution-graph.json`](../../eval/results/current-references-resolution-graph.json) — прогон `science-graphrag-references-resolution-benchmark … --resolver graph` на поднятом стеке; **advisory**, не влияет на `decision`. Снимок в агрегаторе: `--refs-graph-json` (по умолчанию путь выше).
- **Concept / ResearchTopic (Wave N, ontology v1.5):** [`eval/results/current-concept-topic-mini.json`](../../eval/results/current-concept-topic-mini.json) — suite `science-graphrag-concept-topic-benchmark --suite --tier concept_topic_mini` (harness по `anchor_phrase`); **advisory**, **без** узлов `:Concept` / `:ResearchTopic` в production Neo4j. Сводка в агрегаторе: секция *Concept / ResearchTopic family*; путь по умолчанию переопределяется флагом `--concept-topic-json`. Спека: [`semantic-concept-topic-v1.md`](../specs/extraction/semantic-concept-topic-v1.md), ADR: [`013-concept-research-topic-ontology-v1-5.md`](../adr/013-concept-research-topic-ontology-v1-5.md).
- **Живой pilot / nightly (retrieval):** после захвата реальных `chunk_fingerprint` на подписанном корпусе обновляйте фикстуры в `tests/fixtures/benchmarks/retrieval/` и при необходимости пути в агрегаторе; см. [retrieval-eval-v1.md](../benchmarks/retrieval-eval-v1.md), [user-journeys-retrieval-v1.md](user-journeys-retrieval-v1.md).
- **Live mini-tier (`live_corpus_mini`):** пять вопросов с замороженными отпечатками на пилотном корпусе — см. [retrieval-live-tier-v1.md](../benchmarks/retrieval-live-tier-v1.md); по-прежнему **advisory**, без `--mock-answer`.

**Claims / epistemic (Wave H1):** семья `eval/claims/` и фикстуры `tests/fixtures/benchmarks/claims/` — в основном **advisory** (harness / contract); **production lane** Wave O — в **core** `decision_gate` (см. §8.1). Документация: [ontology-claims-benchmark-v1.md](../benchmarks/ontology-claims-benchmark-v1.md), [benchmark-program-status.md](benchmark-program-status.md).

**References resolution (v1 harness):** семья `eval/references_resolution/` и фикстуры `tests/fixtures/benchmarks/references_resolution/` — **advisory**; см. [benchmark-family-references-resolution-v1.md](../specs/benchmark-family-references-resolution-v1.md).

### 8.1 Promotion: claims production extractor → core (Wave O)

**Статус:** production lane **promoted to core** — `claims_production_family.role = core` в агрегаторе; `_decision_gate` требует наличия артефакта `current-claims-production-pilot.json`, `summary.all_passed = true` и средний `claim_recall ≥ 0.8` (при отсутствии файла — **CONDITIONAL-GO**, если иначе GO).

Историческое условие стабилизации (см. [`benchmark-family-promotion-review.md`](benchmark-family-promotion-review.md)):

- **7 ночей подряд** tier `claims_pilot` зелёный с `--extractor production`, `claim_recall ≥ 0.8` без правки gold.
- Harness lane (`--extractor harness`) остаётся зелёным (регрессионный якорь).

Остальные claims-артефакты (merge contract, mini, harness pilot) остаются **advisory**.

### 8.2 Promotion: references resolution graph lane → core

Условие (см. также [`benchmark-family-promotion-review.md`](benchmark-family-promotion-review.md)):

- **7 ночей подряд** suite `refs_mini` (или расширенный tier после freeze) **зелёный** с `--resolver graph` и актуальным пилотным Neo4j (те же `expected_resolutions`, предсказания из live resolver).
- Нет хронических **infra** fail (Bolt timeout, пустая БД без fixture works).

После выполнения — review по чеклисту promotion, обновление [`benchmark-program-status.md`](benchmark-program-status.md), при необходимости включение lane в blocking `decision` (отдельное решение мейнтейнеров).

Если в будущем retrieval станет **blocking** lane, зафиксируйте это здесь и в `scripts/aggregate_benchmark_metrics.py` (критерии fail/pass и preconditions корпуса).

### 8.3 Promotion roadmap: retrieval workspace-scoped + LLM-judge → core (Wave P)

Пока **не** в `_decision_gate`. Условие для смены политики (после review по [`benchmark-family-promotion-review.md`](benchmark-family-promotion-review.md)):

- **14 ночей подряд:** suite `workspace_scoped` зелёная (`summary.all_passed = true`) на зафиксированном пилотном стеке (Neo4j workspaces `ws-pilot-*` + Qdrant `workspace_ids` после `scripts/seed_benchmark_workspaces.py`).
- **14 ночей подряд:** judge pilot `mean_weighted_score ≥ 4.5/6` в [`eval/results/current-retrieval-judge-pilot.json`](../../eval/results/current-retrieval-judge-pilot.json) (запуск `science-graphrag-retrieval-judge-benchmark` поверх `current-retrieval-live-corpus-mini.json` или согласованного входа).

**Митигация overfit judge:** держать **~30% holdout** кейсов вне nightly snapshot (`eval/results/current-retrieval-judge-holdout.json`, недельный прогон), не подмешивать holdout в текущий judge pilot при тюнинге промпта/модели.

После выполнения — чеклист в promotion-review, обновление [`benchmark-program-status.md`](benchmark-program-status.md), явное включение lane в `aggregate_benchmark_metrics._decision_gate` (только решение мейнтейнеров).
