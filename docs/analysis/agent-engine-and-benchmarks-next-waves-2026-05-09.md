# Agent engine & benchmarks — next waves (2026-05-09)

**Статус:** действующий план. Канонический верхнеуровневый entrypoint остаётся [`agent-unified-plan-doing-and-benchmarks-2026-05-08.md`](./agent-unified-plan-doing-and-benchmarks-2026-05-08.md); этот документ — детальная очередь работ **после** Wave A (structural hardening) / B (judge benchmark shipped) / C (advisory observability + promotion review flow), все три закрыты.

**Зачем этот документ:**

- удержать в одном месте, какие конкретные доработки агентского движка и бенчмарков мы делаем дальше;
- зафиксировать KPI / acceptance / зависимости каждой волны;
- развести **engineering hardening** (trace-review, structural debt) и **product quality** (`agent_v3_quality_judge_v1`, новые продуктовые срезы);
- задать ритм promotion review для advisory lanes.

**Что НЕ в scope:**

- продуктовые UI-направления (workspace UX, reader, граф-канвас) — отдельные планы;
- большие миграции инфраструктуры (Phase 5B per-tenant quota, MinIO artifact storage) — отдельные roadmap-ы;
- ingest-конвейер (claims/references resume, dedup, gold-v2 расширение) — следы держим, но это смежная ось ([`ontology-extraction-benchmarks-plan.md`](./ontology-extraction-benchmarks-plan.md));
- Wave A/B/C: всё уже закрыто и заархивировано.

---

## 1. Где мы сейчас

### 1.1 Engineering baseline (закрыто Wave A + stabilization closeout)

| Что закрыто | Канон |
|-------------|-------|
| RoutePlan + QuestionFeatures default-on; `metadata.turn_policy.route_plan` — единственный канал | [`orchestration-stabilization-closeout-2026-05-08.md`](./orchestration-stabilization-closeout-2026-05-08.md) |
| `langgraph_supervisor_v3` — dev default; обе ветки 9/9 acceptance | то же |
| `runtime.py` распилен (`deadline_salvage`, `runtime_answer_salvage`, `runtime_post_turn`, `runtime_envelope`, `runtime_subagent_collectors`) | [`refactor-backend.md`](../backlog/refactor-backend.md) |
| `retrieval_agent.py` распилен (`retrieval_subgraph`, `retrieval_fork_legs`, `retrieval_completion`) | то же |
| `tool_search.py` дальнейший split (`tool_search_discovery_carryover`, `tool_search_strict_deferred`) | то же |
| `writer_agent` сужен до terminal synthesis seam (slice; live evidence по oscillation delta — open) | то же |

### 1.2 Product quality observability (закрыто Wave B + C)

| Что закрыто | Канон |
|-------------|-------|
| `agent_v3_quality_judge_v1` advisory lane (mini / pilot / holdout); CLI suite; pairwise + heuristic | [`agent-v3-quality-benchmark-implementation-plan-2026-05-08.md`](./agent-v3-quality-benchmark-implementation-plan-2026-05-08.md) |
| `--progress` heartbeat, `branch_outcome_v1` (`baseline_outcome` / `candidate_outcome`), rollup `cases_with_any_branch_non_ok` | runner hardening 2026-05-09 |
| Wave C promotion review flow (KPI map, cadence, baseline/compare/fingerprint, advisory visibility в `aggregate_benchmark_metrics.py` → `agent_v3_quality_family`) | [`benchmark-family-promotion-review.md`](../runbooks/benchmark-family-promotion-review.md) |
| LLM-judge calibration subset (4 кейса, `agreement_winner_rate=0.5`) — наблюдение, не gate | `scripts/run_agent_v3_quality_llm_calibration_subset.py` |

### 1.3 Что осталось открытым (P0 → P3)

Базовый источник — [`refactor-backend.md`](../backlog/refactor-backend.md) `[OPEN]` / `[PARTIAL]` + §3 / §4 unified plan + Wave B/C residuals.

| ID | Тема | Приоритет | Ось |
|----|------|-----------|-----|
| **D1** | LLM-judge calibration window до promotion | P1 | benchmark |
| **D2** | Frozen judge prompt fingerprint + variance baseline | P1 | benchmark |
| **D3** | `judge_pilot` baseline frozen JSON + автоматизированный compare на release train | P1 | benchmark |
| **E1** | Глубже декомпозировать heavy retrieval-ветки (`corpus_explore`, `research_plan` под supervisor) — calibration + live trace-review | P1 | engine |
| **E2** | `tool_use_summary` для длинных батчей `ToolMessage` — стабилизация side-LLM cache, измерение `side_llm_cache_read_ratio_avg` | P1 | engine |
| **E3** | `writer_agent` oscillation-risk live evidence + дожать backlog `[PARTIAL]` | P1 | engine |
| **E4** | Persisted admin-секция `agent_tools` (operator knobs vs LLM runtime overrides vs internal guardrails) | P2 | engine |
| **F1** | Latency / token cost benchmark axis рядом с judge pairwise (`latency_p95_v3 vs latency_p95_react`, `usage_total_tokens_delta`) | P1 | benchmark |
| **F2** | Multi-seed pilot run (3 seed × frozen prompts) — judge variance baseline | P2 | benchmark |
| **F3** | Расширение judge rubric / новые продуктовые срезы (`open_research`, `dual_evidence_compare`, `relation_tracing` уже есть; добавить `quote_evidence_grounding` отдельно) | P2 | benchmark |
| **F4** | LLM-judge replacement / cross-family judge (DeepSeek vs Mistral vs Anthropic — корреляция с heuristic) | P3 | benchmark |
| **G1** | Trace-review-v1 на каждое касание `agent/graph/*` / `agent/tool_*` / `agent_v2.py` — runbook автоматизация | P1 | discipline |
| **G2** | `tool_loop_repeat_max` / `latency_p95_ms` / `subagent_lifecycle_missing_count` — alert thresholds в decision_gate (явные, не неявные) | P2 | discipline |
| **H1** | Контекст: micro-compact по idle, restore paper sources после compact, pre-compact sanitizers — продакшен-режим | P2 | context |
| **H2** | L4 LLM-history compact: cache-safe forked side-LLM helper для всех side-LLM вызовов (compact / away / memory / agent_summary) | P2 | context |

---

## 2. Wave D — judge calibration → promotion candidate

**Цель:** сделать `agent_v3_quality_judge_v1` достаточно стабильным, чтобы можно было обсуждать promotion из advisory в core engineering gate (не путать с decision_gate — отдельный процесс).

### 2.1 D1: Calibration window

**Acceptance:**
- зафиксированный набор 6–10 кейсов (subset из `judge_pilot`, не пересекается с `judge_holdout`);
- `scripts/run_agent_v3_quality_llm_calibration_subset.py` расширен: 3 прогона подряд тем же `judge_prompt_fingerprint`, та же модель;
- зафиксирован порог: `agreement_winner_rate ≥ 0.7` heuristic vs LLM на этом subset (текущий 0.5 — недостаточно);
- если порог не достигается без правки промпта — исследовать через `dual_evidence_compare` / `relation_tracing` (наблюдение за этими типами).

**Артефакты:**
- `eval/results/agent-v3-quality-judge-calibration-window-<date>.json` (3 прогона);
- markdown сводка / операторский runbook → `docs/analysis/agent-v3-quality-judge-calibration-2026-05.md`;
- compare с предыдущим окном — через `science-graphrag-agent-v3-quality-compare`.

### 2.2 D2: Frozen judge prompt fingerprint + variance baseline

**Acceptance:**
- `eval/agent_v3_quality/judge_prompt_v1.md` снапшотится с `judge_prompt_sha256` в каждом артефакте (уже есть);
- любая правка промпта → новый fingerprint → **обязательный** сброс stabilization window (правило в [`benchmark-family-promotion-review.md`](../runbooks/benchmark-family-promotion-review.md) есть, но добавить sanity-check скриптом);
- baseline judge variance: `(mean_delta_run1, mean_delta_run2, mean_delta_run3)` — не больше **0.15** absolute spread на одних и тех же кейсах.

**Артефакты:**
- `tests/scripts/test_judge_prompt_fingerprint_guard.py` — регрессия: обновить `EXPECTED_JUDGE_PROMPT_FINGERPRINT` в `eval/agent_v3_quality/contract.py` при смене промпта;
- `eval/results/agent-v3-quality-judge-variance-baseline.json` — шаблон / обновление через `--window --write-variance-baseline`.

### 2.3 D3: Frozen `judge_pilot` baseline + release-train compare

**Acceptance:**
- зафиксирован «золотой» baseline JSON `eval/results/baseline-agent-v3-quality-judge-pilot-<commit>.json` (provenance: `run_metadata`; в репозитории — стартовый снимок `baseline-agent-v3-quality-judge-pilot-embedded.json`, заменить на live LLM-judge baseline при freeze);
- `science-graphrag-agent-v3-quality-compare` запускается автоматически на release-train промежутке (флаг `--release-train-gate`; см. `eval/agent_v3_quality/README.md`);
- если `mean_delta` падает < `baseline_mean_delta - 0.10` или растёт `cases_with_any_branch_non_ok ≥ 1` — release train **блокируется** в release runbook (не CI; сейчас CI берёт `--mock-agent`).

**Зависимости:** D1, D2.

---

## 3. Wave E — engine depth (subagent decomposition + writer hardening)

**Цель:** снизить churn у `latency_p95` и `tool_loop_repeat_max` под нагрузкой за счёт более чистого разделения ролей в supervisor v3, не возвращая «LLM-маршрутизатор как отдельный слой».

### 3.1 E1: corpus_explore / research_plan deepening

Текущее состояние ([`agent-runtime-tools-context-roadmap-2026-05-04.md`](./agent-runtime-tools-context-roadmap-2026-05-04.md) Train T4):
- read-only `corpus_explore` и `research_plan` уже подключены под supervisor с whitelist-инструментами и изоляцией состояния child;
- envelope warnings (`corpus_explore_child_*`, `research_plan_child_*`) при неуспешном child.

**Что доделать в Wave E:**
- live trace-review evidence по типам кейсов, где включение `corpus_explore` реально снижает churn (acceptance compare со старым baseline без флагов);
- замер delta `subagent_task_notification_count_avg`, `subagent_lifecycle_missing_count`, `latency_p95_ms` с/без флагов;
- **default-on** только после: 9/9 acceptance + `tool_loop_repeat_max ≤ 3` + non-degradation `latency_p95_ms` (текущий v3 ~35 c — потолок).

**Acceptance:**
- 1 acceptance volna с флагами off (baseline) и 1 с on, оба `live`, `subprocess` транспорт;
- сводный compare → `eval/results/agent-corpus-explore-research-plan-acceptance-<date>.{json,md}`;
- backlog item в `[OPEN] Reduce supervisor route churn before writer handoff` дополнить evidence ссылкой.

### 3.2 E2: tool_use_summary maturity

Текущее ([`agent-runtime-tools-context-roadmap-2026-05-04.md`](./agent-runtime-tools-context-roadmap-2026-05-04.md) Train T4 + closeout):
- `tool_use_summary` существует; side-LLM через `forked_runtime.run_side_llm_chat`; sanitizer на side-LLM JSON; телеметрия `tool_use_summary_*` в `debug_events_telemetry.py`.
- В trace-review-v1 уже есть `side_llm_cache_read_ratio_avg`.

**Что доделать:**
- сравнить `usage_total_tokens` с/без `tool_use_summary` на длинных батчах ≥ 6 `ToolMessage` подряд (синтетический suite из `judge_pilot`);
- стабилизировать cache-safe форкнутый payload (idential `system+tools+messages prefix`);
- удержать `side_llm_cache_read_ratio_avg ≥ 0.4` (экономия ≥ 40 %) — иначе фича не оправдывает overhead.

**Acceptance:**
- regression в `tests/agent/test_tool_use_summary_cache_safety.py` (новый): assert `cache_read_ratio` ≥ floor;
- `trace_regression_compare.py --min-side-llm-cache-read-ratio 0.4` зелёный на acceptance suite;
- если ratio < 0.4 — feature flag `agent_tool_use_summary_enabled` остаётся **off** до устранения причины.

### 3.3 E3: writer_agent oscillation closure

Текущее: writer narrowed to terminal synthesis seam (slice ✅), но `[PARTIAL]` пункт в backlog ждёт **live** evidence по oscillation delta vs baseline.

**Что доделать:**
- 2 acceptance прогона: один на текущем `writer_agent`, один на namespaced shadow ветке, где writer форсированно single-pass без shortlist (контрольная точка);
- compare `writer_oscillation_count` (новая метрика в trace-review-v1, см. G2);
- если single-pass shadow не уступает по grounding precision/recall и снижает oscillation — отдельный PR на default-on.

**Acceptance:** backlog `[PARTIAL] Simplify writer_agent into terminal synthesis seam` → `[DONE]`.

### 3.4 E4: Persisted admin section `agent_tools`

Дизайн готов: [`agent-tools-admin-settings-proposal-2026-05-07.md`](./agent-tools-admin-settings-proposal-2026-05-07.md). Implementation — отдельная волна.

**Acceptance (минимум):**
- `PATCH /v1/settings/agent_tools` с round-trip для **одного** scalar knob (e.g. `agent_tool_loop_repeat_max`);
- persisted JSON bucket `agent_tools` в `Settings`, с явным разделением:
  - **operator settings** (Settings) — feature flags, timeouts, budget caps;
  - **tool args contract** (Pydantic `args_schema`) — лимиты аргументов, не трогаем;
  - **internal guardrails** (module-level constants) — truncation/preview budgets, не персистим;
- следовать [`constants-and-settings-policy.mdc`](../../.cursor/rules/constants-and-settings-policy.mdc).

**Зависимости:** не блокирует Wave D/F. Может идти параллельно.

---

## 4. Wave F — benchmark axis expansion

**Цель:** не «ещё одна метрика», а закрыть конкретные оси, которые advisory pairwise judge **не** меряет: latency / tokens / variance / cross-model judge.

### 4.1 F1: Latency / token cost ось рядом с pairwise

**Зачем:** pairwise сравнивает **качество** ответа, но не его стоимость. Если `v3` выигрывает 60 / 40 по pairwise и при этом стоит +60 % токенов и +30 % latency — это не однозначный win, и release-train должен видеть обе оси.

**Acceptance:**
- `runner` → запись `latency_ms_baseline / latency_ms_candidate` и `usage_total_tokens_baseline / usage_total_tokens_candidate` per case (уже есть в `branch_outcome_v1` — расширить агрегатами);
- summary в `eval/results/current-agent-v3-quality-judge-pilot.json` получает рядом с pairwise блоком `cost_delta`:

  ```json
  {
    "cost_delta": {
      "latency_p95_baseline_ms": ...,
      "latency_p95_candidate_ms": ...,
      "latency_p95_ratio": ...,
      "tokens_total_baseline": ...,
      "tokens_total_candidate": ...,
      "tokens_total_ratio": ...
    }
  }
  ```
- markdown summary показывает obe оси рядом;
- `trace_regression_compare.py` получает `--max-tokens-ratio` / `--max-latency-ratio` (advisory).

### 4.2 F2: Multi-seed variance baseline

**Зачем:** одна цифра `mean_delta` от одного pilot-прогона — обманчивая «точность». Нужен range.

**Acceptance:**
- `science-graphrag-agent-v3-quality-benchmark` принимает `--seeds N` (по умолчанию 1, для variance — 3);
- агрегация: `mean_delta_min / mean_delta_max / mean_delta_median` по seed-ам;
- baseline range фиксируется как frozen `eval/results/baseline-agent-v3-quality-judge-pilot-multiseed.json`;
- promotion thresholds (`agent-unified-plan-doing-and-benchmarks-2026-05-08.md` §C.1) пересматриваются: ориентир — `mean_delta_median ≥ 0`, не «один прогон ≥ 0».

### 4.3 F3: Расширение rubric / новые продуктовые срезы

Текущие срезы (см. unified plan §5.2): `workspace_stats`, `catalog_resolution`, `quote_evidence`, `dual_evidence_compare`, `relation_tracing`, `open research`.

**Что добавить (приоритет):**
- `quote_evidence_grounding` — отдельный срез: метрика «сколько % утверждений в ответе закрыты quotes из `paper_quote_search`», без overlap с `dual_evidence_compare`;
- `multi_workspace_inspect` — стресс на routing churn: 2+ workspace в одном вопросе;
- `negative_case_refusal` — пара кейсов, где правильный ответ — корректный отказ (workspace empty / off-domain).

**Acceptance:**
- 6 кейсов добавлены в `judge_pilot` (frozen, не пересекаются с holdout);
- per-axis breakdown в judge JSON (rubric scores per case);
- baseline `mean_delta` пересчитан после расширения; old baseline помечается как stale.

### 4.4 F4: Cross-family judge (advisory exploratory)

**Зачем:** один judge model — корреляция с одной моделью. Если judge — DeepSeek и candidate — DeepSeek, есть риск self-preference. Cross-family даст cleaner signal.

**Acceptance:**
- experimental flag `--judge-model-family` (`deepseek` | `anthropic` | `openai`);
- 3 прогона на одинаковых кейсах, разные judge family;
- artifact `eval/results/agent-v3-quality-judge-cross-family-<date>.json` с `inter_judge_agreement_rate`;
- если `inter_judge_agreement ≥ 0.7` — pairwise результат можно считать robust; если ниже — отдельный issue / возврат к D1 / промпт-калибровке.

**Зависимости:** D1, D2 (без них шум перебьёт сигнал). Это **research wave**, не release blocker.

---

## 5. Wave G — trace-review discipline as engineering KPI

**Цель:** не «runbook есть, иногда запускаем», а measurable gate на каждое касание агентного кода.

### 5.1 G1: Auto-trigger trace-review на изменения hotspot путей

**Acceptance:**
- pre-commit hook (advisory) или CI job: при изменении `science_graphrag/agent/graph/**`, `science_graphrag/agent/tool_*`, `science_graphrag/agent_v2.py`, `science_graphrag/agent/runtime*.py` — выводить reminder про `trace-review-v1` acceptance run;
- runbook section в [`agent-trace-review-sop.md`](../runbooks/agent-trace-review-sop.md) обновлён: какой profile (`quick` / `default` / `heavy`) под какой класс правок;
- разделение «merge-блокирующих» полей (`final_answer_missing_count`, `missing_span_count`, `tool_loop_repeat_max`) и «advisory drift» (`compaction_churn_score`, `shortlist_ratio_avg`) — формально в runbook.

### 5.2 G2: Explicit alert thresholds в decision_gate / acceptance

Сейчас acceptance verdict: `pass` / `warn`. Warn от `claim_verification_verdict_parse_rate:absent_no_cv_rows` is by-design; нужен явный список acceptable warns.

**Acceptance:**
- `eval/results/trace-review-acceptance-*.json` schema получает поле `acceptable_warns` (список регулярок);
- любой warn вне списка → `pass` понижается до `warn` или ниже в release runbook;
- `tool_loop_repeat_max > 3` → `fail` (сейчас warn, по факту нарушение цели плана);
- `latency_p95_ms` drift ≥ 25 % от baseline → `warn`; ≥ 50 % → `fail`.

### 5.3 G3: writer_oscillation_count metric (новая)

**Зачем:** для E3 нужна явная метрика, не просто наблюдение.

**Acceptance:**
- в `trace-review-v1` добавлена `writer_oscillation_count` per case — число поворотов «writer → not-writer → writer» в одном turn;
- baseline на acceptance suite ≤ 1;
- регрессия: при росте baseline ≥ 2 — fail.

---

## 6. Wave H — context compaction maturity

**Цель:** L3 / L4 продакшен-готовность, чтобы длинные сессии не «тонули» в `ToolMessage` истории.

### 6.1 H1: Production-ready microcompact / restore / sanitizers

Текущее: частично есть (Train T2 closeout), но без production switch-on.

**Acceptance:**
- microcompact по `client_idle_ms` threshold (есть, но default off) → eval suite на 50-turn workspace разговоре;
- `restore paper sources after compact` — explicit eval, что после compaction ссылки на использованные `paper_quote_search` / `paper_profile` НЕ теряются (regression тест);
- pre-compact sanitizers для PII / secrets — sanity-check набор фикстур.

### 6.2 H2: Cache-safe forked side-LLM unified helper

Текущее ([`refactor-backend.md`](../backlog/refactor-backend.md) `[DONE] Cache-safe forked side-LLM helper — Train T1 slice`):
- helper существует;
- `thread_insights` использует его;
- **остальные side-LLM** (`llm_history_compact`, `away_summary`, subagents) — пока **не** мигрированы.

**Acceptance:**
- все side-LLM вызовы (compact / away / agent_summary / subagents) идут через `run_side_llm_chat`;
- `side_llm_cache_read_ratio_avg ≥ 0.4` на acceptance — стало правилом (см. E2);
- `optional` OpenRouter `cache_control` transport hint, если без него ratio проседает.

---

## 7. Cadence и зависимости

```
Wave A (DONE 2026-05-08)
   └─ Wave B (DONE 2026-05-08)
      └─ Wave C (DONE 2026-05-09)
         ├─ Wave D (D1 → D2 → D3)         ◄── ближайшая, P1
         │   └─ enables F1 / F2 numbers grounded in stable judge
         ├─ Wave E (E1, E2, E3 параллельно; E4 независимо)
         │   └─ feeds D3 baseline (после default-on флагов)
         ├─ Wave F (F1 параллельно D; F2 после D2; F3 после E1; F4 — research)
         ├─ Wave G (G1 / G2 / G3 параллельно остальному)
         └─ Wave H (H1 / H2 после E2 / G3, чтобы variance не съел сигнал)
```

| Неделя (примерная, не CI) | Фокус |
|---------------------------|-------|
| W1 | D1 calibration window, E3 writer oscillation evidence, G3 metric |
| W2 | D2 fingerprint guard, F1 cost delta в runner, G2 thresholds |
| W3 | D3 frozen baseline, E1 corpus_explore live evidence |
| W4 | F2 multi-seed variance, E2 tool_use_summary cache ratio, G1 SOP polish |
| W5 | F3 rubric expansion (judge_pilot resize + new baseline), E4 admin section P0 slice |
| W6+ | F4 cross-family research, H1 / H2 production switch-on |

Wave H ставится **после** D / E / G — нет смысла двигать compaction defaults, пока baseline judge / acceptance / oscillation не стабильны.

---

## 8. Acceptance gates на следующий цикл

Чтобы план не превратился в «новые волны без закрытия предыдущих», два явных gate:

### 8.1 Gate «Wave D готов к промоушн review»

- D1, D2, D3 закрыты;
- 3 stable pilot прогона `judge_pilot` без `cases_with_any_branch_non_ok ≥ 1`;
- `mean_delta` median не ниже `−0.05` против baseline;
- `judge_prompt_fingerprint` не менялся ≥ 2 недель;
- variance multi-seed (F2) показал spread ≤ 0.15.

После закрытия — **отдельный** PR с promotion review checklist (по [`benchmark-family-promotion-review.md`](../runbooks/benchmark-family-promotion-review.md)). Решение «advisory → core» принимают мейнтейнеры; **не** делается автоматически по числам.

### 8.2 Gate «engine baseline стабилен после Wave E»

- E1 default-on флаги без degradation `latency_p95_ms` и `tool_loop_repeat_max`;
- E2 cache ratio ≥ 0.4;
- E3 writer oscillation closure done;
- backlog `[PARTIAL] Simplify writer_agent into terminal synthesis seam` → `[DONE]`.

После этого backlog по агентскому графу можно считать на 80 % закрытым; следующая волна — F2/F3/F4 (research) и продуктовые направления.

---

## 9. Ссылки

| Тема | Док |
|------|-----|
| Master entrypoint | [`agent-unified-plan-doing-and-benchmarks-2026-05-08.md`](./agent-unified-plan-doing-and-benchmarks-2026-05-08.md) |
| Detailed runtime roadmap | [`agent-runtime-tools-context-roadmap-2026-05-04.md`](./agent-runtime-tools-context-roadmap-2026-05-04.md) |
| Stabilization closeout | [`orchestration-stabilization-closeout-2026-05-08.md`](./orchestration-stabilization-closeout-2026-05-08.md) |
| Judge benchmark spec | [`agent-v3-quality-llm-judge-benchmark-plan-2026-05-08.md`](./agent-v3-quality-llm-judge-benchmark-plan-2026-05-08.md) |
| Judge benchmark implementation | [`agent-v3-quality-benchmark-implementation-plan-2026-05-08.md`](./agent-v3-quality-benchmark-implementation-plan-2026-05-08.md) |
| Promotion review flow | [`../runbooks/benchmark-family-promotion-review.md`](../runbooks/benchmark-family-promotion-review.md) |
| Benchmark program status | [`../runbooks/benchmark-program-status.md`](../runbooks/benchmark-program-status.md) |
| Decision gate | [`../runbooks/benchmark-decision-gate.md`](../runbooks/benchmark-decision-gate.md) |
| Trace review SOP | [`../runbooks/agent-trace-review-sop.md`](../runbooks/agent-trace-review-sop.md) |
| Backlog (`[OPEN]` / `[PARTIAL]`) | [`../backlog/refactor-backend.md`](../backlog/refactor-backend.md) |
| Settings policy | [`../../.cursor/rules/constants-and-settings-policy.mdc`](../../.cursor/rules/constants-and-settings-policy.mdc) |
| Long-running ops policy | [`../../.cursor/rules/long-running-ops.mdc`](../../.cursor/rules/long-running-ops.mdc) |
| Habr export article (downstream consumer) | [`../report/export/habr_scigraph.md`](../report/export/habr_scigraph.md) |
