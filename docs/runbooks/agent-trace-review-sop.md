# Agent Trace Review SOP (`trace-review-v1`)

Стандартный порядок отсмотра надежности для runtime-изменений в agent chat.

Цель: любой агент/разработчик запускает одинаковый цикл проверки без ручного
описания шагов, с артефактами JSON/MD, пригодными для PR и регрессии.

## 0) Когда запускать

- Любая правка в:
  - `science_graphrag/agent/graph/*`
  - `science_graphrag/agent/context/*`
  - `science_graphrag/agent/tool_*`
  - `science_graphrag/api/agent_v2.py`
- Любой rollout-флаг, меняющий route/tools/compaction/timeout behavior.

### 0.1) Hotspot CI reminder (Wave G)

PR по hotspot-путям запускает workflow `agent-sse-contract`, который печатает
GitHub Actions notice с напоминанием про операторский trace-review. Это **не**
замена live acceptance: CI собирает synthetic quick artifact, а владелец изменения
выбирает профиль ниже и прикладывает live JSON/MD к PR или release notes.

Hotspot scope:

- `science_graphrag/agent/graph/**`
- `science_graphrag/agent/tool_*`
- `science_graphrag/agent/runtime*.py`
- `science_graphrag/agent/**` при изменениях supervisor/subagent/context boundary
- `science_graphrag/api/agent_v2.py` и `science_graphrag/api/agent_v2_modules/**`

### 0.2) Profile / suite matrix

`profile` и `suite` — разные оси. `profile` задаёт стоимость/глубину запуска,
`suite` задаёт набор кейсов и acceptance-строгость.

| Класс изменения | Минимум | Когда повышать |
|-----------------|---------|----------------|
| Документация, тесты schema/compare без runtime поведения | `--profile quick --suite default` или только unit tests | Если меняются thresholds/verdict schema — добавить baseline compare на fixture JSON |
| `tool_*`, tool routing, validation, permissions | `--profile default --suite default --with-trace-audit` + compare | Если меняется loop policy/tool fanout — `--suite acceptance` |
| `agent/graph/**`, supervisor route plan, specialist handoff | `--profile default --suite acceptance` | Если меняется child lifecycle/subagent flags — `--profile heavy --suite acceptance` |
| `runtime*.py`, deadlines, salvage, stream lifecycle | `--profile default --suite acceptance --with-phoenix --with-db-audit` | При latency/timeout риске — paired baseline/candidate compare |
| Compaction/context behavior | `--profile default --suite default --with-compaction-turns N` | Перед default-on — `--suite acceptance` + compaction merge |
| Writer handoff/synthesis | `--profile default --suite acceptance` + `writer_oscillation_count_max` gate | При shadow/default-on решении — paired baseline/candidate compare |

### 0.3) Blocking vs advisory fields (Wave G)

Merge-blocking для runtime PR, если не оговорён operator waiver:

- `final_answer_missing_count > 0`
- `missing_span_count` вырос относительно baseline (`new_missing_spans`)
- `tool_loop_repeat_max > 3`
- `subagent_lifecycle_missing_count > 0` на `suite=acceptance`
- `writer_oscillation_count_max > 1`
- `latency_p95_ms` drift `>= 50%` относительно baseline

Advisory drift: не игнорировать, но трактовать через compare/runbook, а не как
автоматический hard fail без контекста:

- `latency_p95_ms` drift `>= 25%` и `< 50%`
- `compaction_churn_score`
- `shortlist_ratio_avg`
- `unnecessary_tool_calls_avg`
- `side_llm_cache_read_ratio_avg` для gated/off фичей
- `post_compact_paper_sources_restored_total` (Wave H §H1) — advisory drift при
  снижении на тех же `compaction_event_count`. Hard fail только с явным
  `--paper-sources-restored-fail-on-loss`.

`acceptable_warns` в acceptance artifact — список regex-паттернов для известных
by-design warning reasons. Любой `verdict.warn_reasons[]`, который не матчится
этим списком, попадает в `acceptance_summary.unacceptable_warns` и требует явного
решения в PR/release note.

## 1) Preflight (обязательно)

1. Поднять стек: `make dev-up`
2. Проверить ключи / модель (без сети):  
   `.venv/bin/python scripts/live_check/config_preflight.py`  
   (строже: `--strict --json`).
3. Проверить API с клиента:  
   `.venv/bin/python scripts/live_check/agent_v2_http.py`  
   (обёртка над `http_suite`: `/health` + sync/SSE agent v2).
4. Перед heavy/full — readiness workspace:  
   `.venv/bin/python scripts/chat_agent_workspace_readiness_audit.py`
5. Для **`--suite acceptance`** (и любых проверок с `agent_v2_fanout_probe`): задайте
   непустой **`--workspace-id`** или экспорт **`AGENT_LIVE_WORKSPACE_ID`**. Иначе
   `agent_trace_review.py` завершится с кодом **2** до HTTP-суиты (fail-fast), а
   fanout/malicious deny проверки не имеют смысла без workspace.

### 1.1) Runtime alignment (важно с 2026-05-08, ADR-029)

Default dev runtime теперь — **`langgraph_supervisor_v3`** (multi-agent supervisor).
Trace shape ожидаем supervisor-form: spans `agent.supervisor.route_selected`,
`agent.supervisor.route_plan_step`, `route_to_specialist` edges.

```bash
export SCIENCE_GRAPHRAG_AGENT_RUNTIME=langgraph_supervisor_v3   # default; задавать явно при ручных live-прогонах
```

Для **ReAct compare baseline** (regression gate против single-agent поведения):

```bash
export SCIENCE_GRAPHRAG_AGENT_RUNTIME=langgraph_research_v1
```

Никогда не комбинировать ветки в одном trace-review артефакте — собирайте отдельные
JSON/MD под `eval/results/trace-review-acceptance-{v3,react}.{json,md}` и сравнивайте
через `scripts/live_check/trace_regression_compare.py`.

**Baseline:** для regression gate в git закреплён снимок  
[`eval/results/baseline-trace-review.json`](../../eval/results/baseline-trace-review.json).  
Обновлять его осознанно после успешного полного прогона на локальном стеке и merge в `main`,
если меняются ожидаемые метрики gate (см. `.md` рядом с baseline).

## 2) Канонический review запуск

```bash
.venv/bin/python scripts/live_check/agent_trace_review.py \
  --base-url http://127.0.0.1:18787 \
  --suite default \
  --with-trace-audit \
  --with-phoenix \
  --with-db-audit \
  --out-json eval/results/trace-review.json \
  --out-md eval/results/trace-review.md
```

Если нужно только быстрый smoke: добавить `--skip-e2e` (HTTP suite всё равно ходит в API).

Опционально multi-turn compaction + слияние в тот же артефакт (после записи JSON оркестратор
запускает `compaction_turn_review.py` и `--emit-merged-into` по умолчанию в `--out-json`):

```bash
.venv/bin/python scripts/live_check/agent_trace_review.py \
  ... \
  --with-compaction-turns 4 \
  --require-compaction-after 2
```

E2E-аудит внутри оркестратора пишет полный отчёт через  
`agent_od_workspace_e2e_audit.py --write-report-json <temp>` (разбор `trace_timeline`).

## 3) Обязательные артефакты

- `eval/results/trace-review.json`
- `eval/results/trace-review.md`
- (опционально) `eval/results/trace_review_e2e_report.jsonl` — summary append из OD E2E
- (опционально) `eval/results/trace-review_phoenix_spans.jsonl` при `--with-phoenix`

## 4) Как читать и интерпретировать

### 4.1 Tool flow

- Проверить, что в `checks` нет fail по `agent_v2_sync_json`/`agent_v2_sse`.
- Проверить последовательность `tool_trace` и наличие `final_answer`.

### 4.2 Phoenix alignment

- В e2e-аудите смотреть покрытие span names относительно `tool_trace`.
- Любое увеличение missing spans против baseline — кандидаты в регрессию.

### 4.3 DB/log side effects

- Проверить секции Postgres/runtime warnings в e2e report.
- Отдельно смотреть новые повторяющиеся warning/error причины.

### 4.4 Compaction последствия

Запускать отдельно:

```bash
.venv/bin/python scripts/live_check/compaction_turn_review.py \
  --base-url http://127.0.0.1:18787 \
  --turns 4 \
  --require-compaction-after 2 \
  --out-json eval/results/compaction-turn-review.json \
  --out-md eval/results/compaction-turn-review.md \
  --emit-merged-into eval/results/trace-review.json
```

Проверять:
- появляются ли `compaction.kinds` после порога;
- нет ли деградации tool-loop (аномальный рост шага/ошибок) после compact boundary.

## 5) Regression gate (baseline vs candidate)

```bash
.venv/bin/python scripts/live_check/trace_regression_compare.py \
  --baseline eval/results/baseline-trace-review.json \
  --candidate eval/results/trace-review.json \
  --out-json eval/results/trace-regression.json \
  --out-md eval/results/trace-regression.md
```

Рекомендуемые fail-политики (`--fail-on`, через запятую):
- `new_missing_spans`
- `tool_error_increase`
- `final_answer_missing_increase`
- `subagent_lifecycle_missing_increase`
- `writer_oscillation_increase` (fail при росте `>= 2`)

Warn-политики (`--warn-on`): `latency_p95_increase`, `shortlist_ratio_increase`,
`unnecessary_tool_calls_avg_increase`  
(порог latency warn: `--latency-warn-ratio 1.25`). Wave G hard fail по latency
включён по умолчанию: `--max-latency-p95-regress-ratio 1.5`.
При WARN процесс завершает с кодом **3** (если не передан `--warn-is-pass`).

`compaction_churn_increase` остаётся доступной fail-политикой для compaction-
focused прогонов, но не входит в default fail stack Wave G: в обычном runtime PR
`compaction_churn_score` читается как advisory drift.

### 5.1 Wave E acceptance harness (baseline vs candidate)

Используй **один и тот же** suite/profile/транспорт для пары прогонов; различай только env-профиль.

**Имена артефактов (канон):**

| Артефакт | Назначение |
|----------|------------|
| `eval/results/agent-corpus-explore-research-plan-acceptance-<date>.{json,md}` | E1: subagent flags off vs on |
| `eval/results/trace-review-writer-baseline-<date>.{json,md}` | E3: текущий writer |
| `eval/results/trace-review-writer-single-pass-shadow-<date>.{json,md}` | E3: shadow single-pass |
| `eval/results/trace-regression-wave-e-<date>.{json,md}` | Сводный compare |

**Профиль A — baseline / off:** subagent flags выключены (или дефолт окружения), writer shadow **off**:

```bash
export SCIENCE_GRAPHRAG_AGENT_CORPUS_EXPLORE_ENABLED=0
export SCIENCE_GRAPHRAG_AGENT_RESEARCH_PLAN_SUBAGENT_ENABLED=0
export SCIENCE_GRAPHRAG_AGENT_TOOL_USE_SUMMARY_ENABLED=0   # для изолированного E1; для E2 включать отдельным прогоном
export SCIENCE_GRAPHRAG_AGENT_WRITER_TERMINAL_SINGLE_PASS_SHADOW_ENABLED=0
```

**Профиль B — candidate / on:** целевая конфигурация Wave E (подставьте значения согласно эксперименту):

```bash
export SCIENCE_GRAPHRAG_AGENT_CORPUS_EXPLORE_ENABLED=1
export SCIENCE_GRAPHRAG_AGENT_RESEARCH_PLAN_SUBAGENT_ENABLED=1
export SCIENCE_GRAPHRAG_AGENT_TOOL_USE_SUMMARY_ENABLED=1   # для E2 acceptance
export SCIENCE_GRAPHRAG_AGENT_WRITER_TERMINAL_SINGLE_PASS_SHADOW_ENABLED=0   # 1 только для E3 shadow-ветки
```

Значения попадают в `run_context.feature_flags` итогового trace-review JSON.

**Compare (пример gate-стека):**

```bash
.venv/bin/python scripts/live_check/trace_regression_compare.py \
  --baseline eval/results/trace-review-writer-baseline-DATE.json \
  --candidate eval/results/trace-review-writer-single-pass-shadow-DATE.json \
  --out-json eval/results/trace-regression-wave-e-DATE.json \
  --out-md eval/results/trace-regression-wave-e-DATE.md \
  --max-writer-oscillation-count 1 \
  --fail-on writer_oscillation_increase,new_missing_spans,tool_error_increase,final_answer_missing_increase
```

Для E2 добавьте порог cache-read:

```bash
  --min-side-llm-cache-read-ratio 0.4
```

Целевые метрики в rollup: `writer_oscillation_count_max`, `side_llm_cache_read_ratio_avg`, `subagent_task_notification_count_avg`, `subagent_lifecycle_missing_count`, `latency_p95_ms`, `tool_loop_repeat_max`.

Если в `metrics.tool_use_summary_row_count_total > 0`, но `side_llm_cache_read_ratio_avg == null`,
acceptance summary вернёт `§10.2_side_llm_cache_read_ratio = fail_missing_side_llm_cache_telemetry`.
Это отдельный failure-mode: summary реально применялся, но provider не вернул cache-read telemetry
(`side_llm_cache_*` null/0). Такой прогон не засчитывать как E2 gate pass.

**E1 rollout decision:** зафиксировать после сравнения двух прогонов в [`docs/analysis/wave-e-e1-rollout-decision-2026-05-10.md`](../analysis/wave-e-e1-rollout-decision-2026-05-10.md).

Несовпадение `review_version` между baseline и candidate → **exit 2**.

## 6) Pass / Warn / Fail

- **PASS**: все обязательные checks OK, нет e2e провала, нет hard regressions.
- **WARN**: нет hard fail, но есть деградация latency/churn/нестабильность (в т.ч. regression WARN).
- **FAIL**: обязательный check провален, e2e non-zero, или regression FAIL.

Wave G добавляет machine-readable acceptance поля:

- top-level `acceptable_warns` — regex allowlist известных by-design warnings;
- `acceptance_summary.unacceptable_warns` — фактические warning reasons вне allowlist;
- gate `§G2_tool_loop_repeat_max` — fail при `tool_loop_repeat_max > 3`;
- gate `§G3_writer_oscillation_count` — fail при `writer_oscillation_count_max > 1`.

## 7) ROI-фичи: что проверяем дополнительно

1. Deferred tool schemas: shortlist quality + latency/prompt-size delta.
2. Discovered tools carry-over: churn после compaction boundary.
3. Unified tool pipeline: validation/permission/hooks breakdown.
4. Allowed-tools matrix: deny-by-mode/role и отсутствие утечек tool exposure.
5. Sidechain transcripts: branch reconstruction и recovery.
6. Token budget loop policy: корректность continue/stop behavior.
7. Away summary: качество recap и корректность follow-up.
8. Feature-gated rollout: on/off parity и telemetry stability.

## 8) Long-thread offline eval (Epic A3, nightly / optional PR)

Детерминированный слой проверок `resolve_prompt_memory_policy` + `format_user_with_memory`
без HTTP. Включается флагом оркестратора; метрики мержатся в `metrics` того же
`trace-review-v1` артефакта (`insight_recall_at_k`, `stale_summary_error_rate`, …).

```bash
.venv/bin/python scripts/live_check/agent_trace_review.py \
  --base-url http://127.0.0.1:18787 \
  --profile quick \
  --with-long-thread-eval \
  --out-json eval/results/trace-review-lt.json \
  --out-md eval/results/trace-review-lt.md
```

Numeric gate (пример) поверх того же `trace_regression_compare.py`:

```bash
.venv/bin/python scripts/live_check/trace_regression_compare.py \
  --baseline eval/results/baseline-trace-review.json \
  --candidate eval/results/trace-review-lt.json \
  --min-insight-recall-at-k 0.95 \
  --max-stale-summary-error-rate 0.05 \
  --max-latency-p95-ms 45000 \
  --min-claim-grounding-precision 0.90 \
  --min-claim-grounding-recall 0.90 \
  --out-json eval/results/trace-regression-lt.json \
  --out-md eval/results/trace-regression-lt.md
```

По умолчанию compare также валит run при регрессии `verdict.status`
(`pass > warn > fail`); отключается только явно через `--no-enforce-verdict-not-worse`.

## 9) Wave H — context compaction maturity

Wave H — context compaction maturity (см.
[`docs/analysis/agent-engine-and-benchmarks-next-waves-2026-05-09.md`](../analysis/agent-engine-and-benchmarks-next-waves-2026-05-09.md)
§6).

### 9.1 Когда запускать

- любая правка в `science_graphrag/agent/context/` (compaction / sanitizers / paper sources);
- любая правка `science_graphrag/agent/forked_runtime.py` или новых side-LLM
  call sites (см. [`docs/analysis/wave-h-side-llm-inventory-2026-05-12.md`](../analysis/wave-h-side-llm-inventory-2026-05-12.md));
- перед обсуждением default-on `agent_llm_full_history_compact_enabled`.

### 9.2 Offline long-thread harness (CI-friendly)

Детерминированный 50-turn прогон через session_store; **не** ходит в LLM provider:

```bash
.venv/bin/python scripts/live_check/long_thread_compaction_eval.py \
  --profile baseline \
  --turns 50 \
  --digest-cap 10 \
  --out-json eval/results/wave_h/baseline-long-thread-DATE.json \
  --out-md eval/results/wave_h/baseline-long-thread-DATE.md

.venv/bin/python scripts/live_check/long_thread_compaction_eval.py \
  --profile candidate \
  --turns 50 \
  --digest-cap 10 \
  --out-json eval/results/wave_h/candidate-long-thread-DATE.json \
  --out-md eval/results/wave_h/candidate-long-thread-DATE.md
```

Профили:

- `baseline` — pre-Wave-H L4 path: `cache_read_ratio = 0.0` на каждом compact.
  Ожидаемый verdict `warn` с `side_llm_cache_read_ratio_avg<0.4`.
- `candidate` — Wave H §H2 path с cache-stable prefix через `run_side_llm_chat`.
  Ожидаемый verdict `pass`, ratio `≥ 0.4`.

Harness **не** замена live trace-review run. Он гарантирует, что:

1. compaction boundary триггерится предсказуемо (число events на 50 turns стабильно);
2. `paper_sources_restored` capsule создаётся и потребляется на каждом compact;
3. cache telemetry прокидывается в audit на candidate-профиле.

### 9.3 Live trace-review для compaction acceptance

После offline harness — live прогон с `agent_llm_full_history_compact_enabled=1`:

```bash
.venv/bin/python scripts/live_check/agent_trace_review.py \
  --base-url http://127.0.0.1:18787 \
  --profile default --suite acceptance \
  --with-compaction-turns 6 \
  --out-json eval/results/trace-review-wave-h-DATE.json \
  --out-md eval/results/trace-review-wave-h-DATE.md
```

Wave H acceptance gate в compare:

```bash
.venv/bin/python scripts/live_check/trace_regression_compare.py \
  --baseline eval/results/baseline-trace-review.json \
  --candidate eval/results/trace-review-wave-h-DATE.json \
  --min-side-llm-cache-read-ratio 0.4 \
  --paper-sources-restored-fail-on-loss \
  --out-json eval/results/trace-regression-wave-h-DATE.json \
  --out-md eval/results/trace-regression-wave-h-DATE.md
```

`--paper-sources-restored-fail-on-loss` превращает Wave H §H1 advisory drift
в hard fail: candidate упадёт, если на тех же `compaction_event_count` он
не восстановил ни одной paper-evidence (baseline восстанавливал ≥ 1).

### 9.4 Чтение acceptance summary

В `acceptance_summary.gates`:

- `§10.2_side_llm_cache_read_ratio` — общий cache-read gate (включает L4 compact
  после Wave H §H2 миграции).
- `§H1_post_compact_paper_sources_restore` — `pass` если был хотя бы один
  paper restore при compaction events `> 0`; `warn_no_paper_sources_restored_after_compaction`
  если compaction случался, но restore не сработал.

В `acceptance_summary.live_proven` появляется `post_compact_paper_sources_restored_in_timeline`
когда хотя бы один turn в timeline вернул `post_compact_paper_sources_restored_count > 0`.

### 9.5 Live paired runs — `agent_llm_full_history_compact` и idle microcompact

Оба флага **default-off** до operator evidence (см.
[`docs/analysis/wave-h-rollout-decision-2026-05-12.md`](../analysis/wave-h-rollout-decision-2026-05-12.md)).

**A) Full L4 history compact (Wave H §H2 rollout gate)**

1. Поднять dev API с явным env (пример):

   ```bash
   export SCIENCE_GRAPHRAG_AGENT_LLM_FULL_HISTORY_COMPACT_ENABLED=1
   export AGENT_LIVE_BASE=dev
   ```

2. Снять acceptance trace-review JSON/MD (§9.3 команда с `--with-compaction-turns 6` или heavy profile по матрице SOP).

3. Compare с `--min-side-llm-cache-read-ratio 0.4` и `--paper-sources-restored-fail-on-loss` (§9.3).

**B) Idle microcompact (`agent_tool_message_microcompact_time_trigger_enabled`)**

- Отдельная **paired** baseline/candidate серия (два прогона), т.к. offline harness не
  доказывает отсутствие churn в продакшене.
- Включение через env, например:
  `SCIENCE_GRAPHRAG_AGENT_TOOL_MESSAGE_MICROCOMPACT_TIME_TRIGGER_ENABLED=1`
  (и при необходимости настройка `SCIENCE_GRAPHRAG_AGENT_TOOL_MESSAGE_MICROCOMPACT_TIME_GAP_MINUTES`).
