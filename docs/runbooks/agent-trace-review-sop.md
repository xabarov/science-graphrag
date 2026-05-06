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
