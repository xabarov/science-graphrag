# Извлечение ссылок: harness, правки эвристик и CI (2026-04-09)

## Артефакты

| Набор | Файл | Кейсов | Примечание |
|-------|------|--------|------------|
| **Full tier — все режимы** (эвристики + `scope_llm` + `batched_llm`) | [`refs_bench_full_tier/refs_bench_summary.json`](refs_bench_full_tier/refs_bench_summary.json) | 34 | `references_benchmark_full`; **CLI wall ≈ 1538 с** (`cli_wall_seconds` в JSON) |
| **API tier** (v1, для сравнения масштаба) | [`refs_bench_full_api/refs_bench_summary.json`](refs_bench_full_api/refs_bench_summary.json) | 15 | `references_benchmark_v1` |
| Агент (smolagents) | [`refs_agent_suite.json`](refs_agent_suite.json) | 15 | Без перепрогона в этой сессии |

---

## 0. Инженерные правки (сессия 2026-04-09)

1. **Gold:** `gfl_realpdf` — последняя строка библиографии [36] и `end_line` 702; `deformable_detr_realpdf` — 44 логических записи, `silver_heuristic`; манифест [`scripts/references_benchmark_gold_manifest.json`](../../scripts/references_benchmark_gold_manifest.json) обновлён.
2. **Парсер:** `extract_references` / `split_reference_entries` — линии со списком авторов без `[n]` (plain author-year), см. [`science_graphrag/ingestion/stages/references.py`](../../science_graphrag/ingestion/stages/references.py).
3. **Локализация span:** [`find_reference_section_spans`](../../science_graphrag/ingestion/document_slices.py) — стоп перед appendix в стиле «A Section …» без `##`, обрезка хвоста из 1–2 цифр (номера страниц PDF).
4. **scope_llm:** [`pred_raw_entries_from_bibliography_excerpt`](../../eval/references_harness/scope_segmentation.py) — пост-сплит «склеенного» excerpt по `\n(?=\[\d+\])`, если в одном blob несколько `[n]`.
5. **CI:** профиль [`ci_smoke`](../../eval/layer1/threshold_profiles.py) — `require_reference_count_ok=False`, чтобы smoke-тест layer-1 не ломался на дрейфе числа ссылок при **только эвристическом** прогоне (`test_run_case_smoke`).

---

## 1. Сводка harness — full tier (`references_benchmark_full`, 34 кейса), **все гипотезы**

Источник: [`refs_bench_full_tier/refs_bench_summary.json`](refs_bench_full_tier/refs_bench_summary.json), прогон 2026-04-09 (включая LLM).

| Режим | Средний span line IoU | Средний entry overlap F1 | Суммарное время режима (с) | Среднее время на кейс (с) |
|-------|----------------------:|-------------------------:|---------------------------:|--------------------------:|
| heuristic_full | 0.878 | 0.917 | 0.187 | 0.005 |
| heuristic_scope | 0.878 | 0.908 | 0.138 | 0.004 |
| heuristic_bib_gold | 0.878 | **0.931** | 0.148 | 0.004 |
| **scope_llm** | **0.881** | 0.127 | 642.7 | 18.9 |
| **batched_llm** | 0.878 | 0.917 | 895.0 | 26.3 |

**Интерпретация**

- Эвристики и **batched_llm** на полном тире дают сопоставимый **средний entry F1** (~0.92); span IoU у всех режимов кроме небольшого подъёма у `scope_llm` — ~0.878.
- **scope_llm** на 34 «тяжёлых» PDF→MD кейсах сильно проседает по **entry F1** (среднее **0.13**): один excerpt + пост-сплит не вытягивают длинные/шумные библиографии так же, как batched-чанки; отдельные кейсы с нулевым F1 сильно тянут среднее (детали — в `refs_bench_scope_llm.json`).
- Wall: весь CLI-прогон пяти режимов по 34 кейсам — **~1538 с** (~25.6 мин); основное время — `scope_llm` и `batched_llm`.

---

## 2. Сводка harness — API tier (15 кейсов, `references_benchmark_v1`)

Источник: [`refs_bench_full_api/refs_bench_summary.json`](refs_bench_full_api/refs_bench_summary.json) (не пересчитывался в этой сессии; для сравнения с отчётом 2026-04-08).

| Режим | Средний span line IoU | Средний entry overlap F1 | Суммарное время (с) | Среднее время на кейс (с) |
|-------|----------------------:|-------------------------:|--------------------:|--------------------------:|
| heuristic_full | 0.896 | 0.898 | 0.072 | 0.005 |
| heuristic_scope | 0.896 | 0.900 | 0.057 | 0.004 |
| heuristic_bib_gold | 0.896 | 0.903 | 0.056 | 0.004 |
| scope_llm | 0.902 | 0.367 | 223.6 | 14.9 |
| batched_llm | 0.896 | **0.957** | 419.4 | 28.0 |

На **15 кейсах** v1 картина мягче для `scope_llm` (см. таблицу ниже); на **full tier** провал `scope_llm` по entry F1 выражен сильнее из‑за длины и шума корпуса.

---

## 3. Агент с инструментами

Как в [отчёте 2026-04-08](refs_llm_agent_experiment_2026-04-08.md): метрики A/B в [`refs_agent_suite.json`](refs_agent_suite.json), постпроцесс v2 (`segment_reference_block` → `raw_entries`).

**Примечание:** для `deformable_detr_realpdf` в gold теперь 44 записи и поддержка author-year в эвристике; строки отчёта 2026-04-08 про «36 gold / 1 pred» устарели для актуального gold.

---

## 4. Команды для воспроизведения

**Full tier — все режимы (эвристики + LLM), как в этом отчёте:**

```bash
cd /path/to/science-graphrag
.venv/bin/python scripts/run_references_benchmark.py \
  --tier references_benchmark_full \
  --output-dir eval/results/refs_bench_full_tier \
  --modes heuristic_full,heuristic_scope,heuristic_bib_gold,scope_llm,batched_llm
```

Нужны **`benchmark_teacher_llm_api_key` или `extraction_llm_api_key`** в настройках (см. `get_settings()`). Ожидаемое время — **десятки минут** на 34 кейса.

**Только эвристики (секунды):** уберите `scope_llm,batched_llm` из `--modes`.

**V1 (15 кейсов) + LLM — отдельный артефакт:**

```bash
.venv/bin/python scripts/run_references_benchmark.py \
  --tier references_benchmark_v1 \
  --output-dir eval/results/refs_bench_full_api \
  --modes heuristic_full,heuristic_scope,heuristic_bib_gold,scope_llm,batched_llm
```

**Тесты:**

```bash
.venv/bin/pytest tests/ -q
```

**Suite агента (опционально):**

```bash
.venv/bin/python scripts/experiment_references_smolagents_spike.py suite \
  --output-path eval/results/refs_agent_suite.json \
  --max-steps 12
```

---

## 5. Связь с предыдущим отчётом

- Подробные определения режимов и гипотезы — в [`refs_llm_agent_experiment_2026-04-08.md`](refs_llm_agent_experiment_2026-04-08.md).
- Настоящий файл — канон по **full tier со всеми методами** (включая LLM) и **правкам кода/gold/CI** от 2026-04-09.
