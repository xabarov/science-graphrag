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
