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

Warn-политики (`--warn-on`): `latency_p95_increase`, `compaction_churn_drop`  
(пороги: `--latency-warn-ratio`, `--compaction-churn-warn-delta`).  
При WARN процесс завершает с кодом **3** (если не передан `--warn-is-pass`).

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
  --max-writer-oscillation-count 5 \
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
