# Agent engine & benchmarks — next waves (2026-05-09)

**Статус:** действующий план (синхронизировано **2026-05-12** с [`wave-h-rollout-decision-2026-05-12.md`](./wave-h-rollout-decision-2026-05-12.md), [`wave-f-f3-slice1-closure-2026-05-12.md`](./wave-f-f3-slice1-closure-2026-05-12.md), Wave E2 PR1–2 в коде). Канонический верхнеуровневый entrypoint остаётся [`agent-unified-plan-doing-and-benchmarks-2026-05-08.md`](./agent-unified-plan-doing-and-benchmarks-2026-05-08.md); этот документ — детальная очередь работ **после** Wave A (structural hardening) / B (judge benchmark shipped) / C (advisory observability + promotion review flow), все три закрыты.

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
| `writer_agent` сужен до terminal synthesis seam; live oscillation closure **DONE** (Wave E 2026-05-12) | [`refactor-backend.md`](../backlog/refactor-backend.md) |

### 1.2 Product quality observability (закрыто Wave B + C)

| Что закрыто | Канон |
|-------------|-------|
| `agent_v3_quality_judge_v1` advisory lane (mini / pilot / holdout); CLI suite; pairwise + heuristic | [`agent-v3-quality-benchmark-implementation-plan-2026-05-08.md`](./agent-v3-quality-benchmark-implementation-plan-2026-05-08.md) |
| `--progress` heartbeat, `branch_outcome_v1` (`baseline_outcome` / `candidate_outcome`), rollup `cases_with_any_branch_non_ok` | runner hardening 2026-05-09 |
| Wave C promotion review flow (KPI map, cadence, baseline/compare/fingerprint, advisory visibility в `aggregate_benchmark_metrics.py` → `agent_v3_quality_family`) | [`benchmark-family-promotion-review.md`](../runbooks/benchmark-family-promotion-review.md) |
| LLM-judge calibration subset (4 кейса, `agreement_winner_rate=0.5`) — наблюдение, не gate | `scripts/run_agent_v3_quality_llm_calibration_subset.py` |
| **Wave D (P1) — инструментарий в репозитории:** calibration window (`--window` / `--strict` / `--write-variance-baseline`), fixture `calibration_window_case_ids.json`, fingerprint guard (`EXPECTED_JUDGE_PROMPT_FINGERPRINT` + тест), variance JSON-шаблон, `baseline-agent-v3-quality-judge-pilot-embedded.json`, `compare --release-train-gate`, runbooks | [`agent-v3-quality-judge-calibration-2026-05.md`](./agent-v3-quality-judge-calibration-2026-05.md), [`eval/agent_v3_quality/README.md`](../../eval/agent_v3_quality/README.md) |

### 1.3 Что осталось открытым (P0 → P3)

Базовый источник — [`refactor-backend.md`](../backlog/refactor-backend.md) `[OPEN]` / `[PARTIAL]` + §3 / §4 unified plan. **Structural refactor** (распил trace-review CLI и т.п.) ведётся только в backlog — см. §9. **Сводка Settings vs operator** по E1/E2 и смежным флагам (R0): [`agent-engine-feature-status-2026-05-13.md`](./agent-engine-feature-status-2026-05-13.md).

| ID | Тема | Приоритет | Ось |
|----|------|-----------|-----|
| **D §8.1** | **Wave D (promotion-ready gate):** инструментарий и fingerprint guard **в репозитории**; строгий live calibration (`agreement_winner_rate`, variance) — **operator checklist** в [`wave-d-promotion-operator-closeout-2026-05-12.md`](./wave-d-promotion-operator-closeout-2026-05-12.md). Прежний advisory defer см. [`pre-f-closure-wave-d-evidence-2026-05-12.md`](./pre-f-closure-wave-d-evidence-2026-05-12.md) §6. | P1 | benchmark |
| **E1** | **Default-on в `config.py` (2026-05-12):** `corpus_explore` / `research_plan` + latency guard `agent_e1_retrieval_hop_*` (см. [`wave-e-e1-rollout-decision-2026-05-10.md`](./wave-e-e1-rollout-decision-2026-05-10.md) supplement). Исторический live «keep gated» относится к прогону **без** evidence gate. | P1 | engine |
| **E2** | **Default-on в `config.py` (2026-05-12):** `agent_tool_use_summary_enabled` + `agent_side_llm_openrouter_cache_control_enabled` для `run_side_llm_chat`. Operator live compare `side_llm_cache_read_ratio_avg` остаётся рекомендованным при смене модели/провайдера. | P1 | engine |
| **F3-slice2+** | **Закрыто (2026-05-12):** добавлены 2 controlled `multi_workspace_inspect` кейса — [`wave-f-f3-slice2-expansion-2026-05-12.md`](./wave-f-f3-slice2-expansion-2026-05-12.md). | P2 | benchmark |
| **Wave H rollout** | **Default-on в `config.py` (2026-05-12):** `agent_llm_full_history_compact_enabled`, `agent_tool_message_microcompact_time_trigger_enabled`; harness + paired live артефакты — [`wave-h-rollout-decision-2026-05-12.md`](./wave-h-rollout-decision-2026-05-12.md). Trace-review: heartbeat/`execution_diagnostics` в `agent_trace_review.py`. | P2 | context |
| **Structural** | Частичный split: `trace_regression_metrics.py` + heartbeat-модули; полный распил `trace_review_schema.py` остаётся в [`refactor-backend.md`](../backlog/refactor-backend.md) при необходимости. | P2 | discipline |

**Закрыто волнами / срезами (не дублировать как open queue):** E3 writer oscillation, E4 `agent_tools` thin slice, G1–G3, F1/F2/F4 live artifacts (2026-05-12), **F3-slice1** (`quote_evidence_grounding` + `negative_case_refusal`) — см. [`wave-f-f3-slice1-closure-2026-05-12.md`](./wave-f-f3-slice1-closure-2026-05-12.md); Wave H **implementation** (H1 tests/harness, H2 L4 → `run_side_llm_chat`, inventory) — см. [`wave-h-rollout-decision-2026-05-12.md`](./wave-h-rollout-decision-2026-05-12.md).

## 2. Wave D — judge calibration → promotion candidate

**Цель:** сделать `agent_v3_quality_judge_v1` достаточно стабильным, чтобы можно было обсуждать promotion из advisory в core engineering gate (не путать с decision_gate — отдельный процесс).

**Статус (2026-05-10):** реализация D1–D3 **в коде, тестах и runbooks закрыта**; подпункты §2.1–2.3 ниже фиксируют acceptance для **полного** закрытия волны (live evidence + решение по promotion). Gate «готов к promotion review» — §8.1.

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
- любая правка промпта → новый fingerprint → **обязательный** сброс stabilization window (правило в [`benchmark-family-promotion-review.md`](../runbooks/benchmark-family-promotion-review.md)); sanity-check в репозитории: `EXPECTED_JUDGE_PROMPT_FINGERPRINT` + `tests/scripts/test_judge_prompt_fingerprint_guard.py`;
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

**R0 / `config.py` (2026-05-13):** формулировки ниже в §3.1–3.2 про **«keep gated»** / **«default-on still gated»** описывают **operator rollout gate** (решение по live evidence), а не обязательно `Field(default=False)` в коде. Единая матрица *Settings default / operator gate / evidence / next action*: [`agent-engine-feature-status-2026-05-13.md`](./agent-engine-feature-status-2026-05-13.md); контекст волны R0: [`agent-engine-next-horizon-2026-05-13.md`](./agent-engine-next-horizon-2026-05-13.md) §R0.

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
- follow-up evidence для churn: см. уже закрытый `[DONE] Reduce supervisor route churn before writer handoff`; новые прогоны дополняют картину по subagent-флагам.

**Статус на 2026-05-13:** ✅ **Live paired + compare (keep gated)**
- артефакты: `eval/results/agent-corpus-explore-research-plan-acceptance-2026-05-13-{baseline,candidate}.{json,md}`, `eval/results/trace-regression-wave-e-2026-05-13-e1.{json,md}`;
- итог: **keep gated** — `latency_p95_ms` 43865 → 69112 при включённых subagent+summary (регрессия по p95, compare `pass` с warn); см. [`wave-e-e1-rollout-decision-2026-05-10.md`](./wave-e-e1-rollout-decision-2026-05-10.md).

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

**Статус на 2026-05-13:** 🟡 **PARTIAL (telemetry + cache-prefix code done; product default-on still gated)**
- done: cache-safe regression tests + telemetry merge improvements (`debug_events` full aggregation, `specialist_results_v3` fallback extraction в `trace_review_schema`);
- done: live acceptance показывает `tool_use_summary_row_count_total > 0` (summary реально применялся);
- done (code): нормализация ratio при явных нулевых cache-read токенах без creation — `side_llm_cache_read_ratio_avg` больше не `null` **только из-за** `0`+`null` пары; gate §10.2 уходит в `fail_below_0_4_*`, если среднее &lt; 0.4 (см. [`pre-f-closure-readiness-2026-05-12.md`](./pre-f-closure-readiness-2026-05-12.md));
- done (live E2 heavy): `trace-review-wave-e-e2-tool-summary-acceptance-2026-05-13-v5.json` дал `tool_use_summary_row_count_total=28` и non-null `side_llm_cache_read_ratio_avg=0.1`; compare gate `--min-side-llm-cache-read-ratio 0.4` зафейлен (`trace-regression-wave-e-2026-05-13-e2-v5.md`).
- done (code, **2026-05-12 Wave E2 PR1+PR2**): канонический сериализатор payload для идентичного cache-prefix (`science_graphrag/agent/tool_use_summary.py::canonical_tool_json_for_side_llm`), регрессии `tests/agent/test_tool_use_summary_canonical_cache_prefix.py`, опциональный live probe `scripts/live_check/tool_use_summary_cache_preflight.py`.
- open (product / **PR3**): default-on `agent_tool_use_summary_enabled` только после **нового** heavy live с `side_llm_cache_read_ratio_avg ≥ 0.4` на свежем коде **или** явной policy-оговорки «держим off».

**Мини-план, если целимся в `side_llm_cache_read_ratio_avg >= 0.4`:**
1. **PR1: canonical cache prefix** — ✅ **DONE (2026-05-12):** `canonical_tool_json_for_side_llm` + стабильный `fork_prompt` в `summarize_tool_result_payload_dict`.
2. **PR2: targeted cache benchmark** — ✅ **DONE (2026-05-12):** unit-regression на byte-stable fork_prompt; `scripts/live_check/tool_use_summary_cache_preflight.py` (`--live` после checklist).
3. **PR3: provider/model decision** — **OPEN (operator):** если после повторного heavy live ratio всё ещё `< 0.4`, зафиксировать provider/model/payload-shape follow-up **или** оставить `agent_tool_use_summary_enabled=off` как продуктовое решение.

**Порядок работ / stop condition:**
- до завершения PR1+PR2 не повторять full heavy acceptance ради «надежды на зелёный»;
- если targeted benchmark после стабилизации prefix всё ещё показывает `< 0.4`, не тратить следующий цикл на E2, а формально оставить feature gated.

### 3.3 E3: writer_agent oscillation closure

Текущее: writer narrowed to terminal synthesis seam (slice ✅), но `[PARTIAL]` пункт в backlog ждёт **live** evidence по oscillation delta vs baseline.

**Что доделать:**
- 2 acceptance прогона: один на текущем `writer_agent`, один на namespaced shadow ветке, где writer форсированно single-pass без shortlist (контрольная точка);
- compare `writer_oscillation_count` (новая метрика в trace-review-v1, см. G2);
- если single-pass shadow не уступает по grounding precision/recall и снижает oscillation — отдельный PR на default-on.

**Acceptance:** backlog `[PARTIAL] Simplify writer_agent into terminal synthesis seam` → `[DONE]`.

**Статус на 2026-05-12:** ✅ **DONE**
- `writer_oscillation_count` добавлен в trace-review schema + compare policy;
- live Wave E прогоны подтверждают отсутствие деградации (`writer_oscillation_count_max = 0` на последних acceptance/default артефактах);
- backlog item про writer закрыт в `docs/backlog/refactor-backend.md`.

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

**Статус на 2026-05-12:** ✅ **DONE (thin slice)**
- реализован persisted bucket `agent_tools` + endpoint `PATCH /v1/settings/agent_tools`;
- round-trip для `agent_supervisor_max_rounds` (allowlist + clamp 2..32) покрыт service/API/runtime_overlay тестами;
- секция отделена от `llm.runtime_overrides` и отражается в snapshot/schema.

### 3.5 Что осталось закрыть до Wave F

> **Update 2026-05-12:** Wave F **F-core** (F1/F2 + F3-slice1 evidence) уже зафиксированы артефактами; блок ниже — исторический pre-F чеклист; актуальные хвосты см. §1.3 и [`pre-f-closure-readiness-2026-05-12.md`](./pre-f-closure-readiness-2026-05-12.md).

1. **E1 decision artifact:** ✅ live **2026-05-13** — пара `agent-corpus-explore-research-plan-acceptance-2026-05-13-{baseline,candidate}.*` + [`trace-regression-wave-e-2026-05-13-e1.*`](../../eval/results/trace-regression-wave-e-2026-05-13-e1.md); итог **keep gated** (p95 latency) — [`wave-e-e1-rollout-decision-2026-05-10.md`](./wave-e-e1-rollout-decision-2026-05-10.md).

2. **E2 cache-ratio evidence:** ✅ heavy/E2 прогон выполнен (`trace-review-wave-e-e2-tool-summary-acceptance-2026-05-13-v5.*`), но порог §10.2 не пройден: `side_llm_cache_read_ratio_avg=0.1 < 0.4` (`trace-regression-wave-e-2026-05-13-e2-v5.*`). Практический статус — **keep off / gated**; follow-up mini-plan записан в §3.2.

3. **Wave D promotion gate 8.1:** ✅ live calibration window **2026-05-13** (`eval/results/agent-v3-quality-judge-calibration-window-2026-05-13.*`, variance baseline обновлён); **строгие** пороги agreement/variance **не** пройдены — см. [`pre-f-closure-wave-d-evidence-2026-05-12.md`](./pre-f-closure-wave-d-evidence-2026-05-12.md) § Live run log.

---

## 4. Wave F — benchmark axis expansion

**Цель:** не «ещё одна метрика», а закрыть конкретные оси, которые advisory pairwise judge **не** меряет: latency / tokens / variance / cross-model judge.

### 4.0 Executive summary

Wave F выполняется **поверх** уже известных, но не полностью «зелёных» гейтов Wave D/E (см. [`pre-f-closure-readiness-2026-05-12.md`](./pre-f-closure-readiness-2026-05-12.md)): это **benchmark expansion under unstable-but-known constraints**, а не изолированная волна «всё зелёное → новые метрики».

**Три outcomes волны:**

1. **Quality + cost рядом** — release-train и оператор видят pairwise **и** latency/tokens в одном артефакте (`F1`).
2. **Variance-aware baseline** — `mean_delta` и promotion-чтение опираются на **диапазон по seed**, а не на один случайный прогон (`F2`).
3. **Контролируемое расширение suite** — минимум один новый продуктовый срез + rubric breakdown без размытия baseline discipline (`F3`), плюс отдельный исследовательский appendix по cross-family judge (`F4`).

**Non-goal (явно):** в рамках Wave F **не** выбирать нового canonical judge provider и **не** закрывать promotion gate §8.1 Wave D силой новых осей — только дать честные измерения и документацию интерпретации.

### 4.0.1 Разделение: F-core vs F-research

| Трек | Состав | Роль |
|------|--------|------|
| **F-core** | `F1`, `F2`, узкий `F3` (slice1) | Обязательный цикл следующего benchmark pass: cost axis, multiseed range, один controlled rubric/case expansion. |
| **F-research** | `F4`, опционально `F3` slice2+ | Исследование без статуса release blocker; артефакты отдельно, не смешивать с core gate. |

### 4.0.2 Wave F — gating assumptions (зависимости от D/E)

Эти пункты **не блокируют старт F1**, но ограничивают, какие выводы можно делать из артефактов F2/F3/F4:

| Gate / хвост | Статус на момент pre-F closure | Влияние на Wave F |
|--------------|--------------------------------|-------------------|
| **Wave D §8.1 (`--strict`)** | Live окно есть; strict agreement/variance **ещё не** зелёные — см. [`pre-f-closure-wave-d-evidence-2026-05-12.md`](./pre-f-closure-wave-d-evidence-2026-05-12.md). | `F1` — ок. `F2` / multiseed range — **advisory**, не аргумент для promotion до зелёного D. `F4` — только research. |
| **Wave E1** | Paired live + compare; итог **keep gated** (p95 latency) — [`wave-e-e1-rollout-decision-2026-05-10.md`](./wave-e-e1-rollout-decision-2026-05-10.md). | Срезы, чувствительные к routing churn (например `multi_workspace_inspect` в `F3`), **нельзя** трактовать как доказательство default-on readiness. |
| **Wave E2** | `tool_use_summary` применялся, но `side_llm_cache_read_ratio_avg` &lt; порога 0.4 — **keep off / gated**; см. readiness § Risk carried into Wave F. | В `F1` **обязательно** читать `side_llm_cache_read_ratio_avg` **вместе** с `usage_total_tokens_*`; низкий cache ratio при высокой нагрузке summary — сигнал конфигурации/provider follow-up, не «тихий» cost win. |

### 4.0.3 Очередность исполнения (рекомендуемая)

1. **`F1`** — cost/latency axis в runner + summary + advisory flags в `trace_regression_compare.py`.
2. **`F2`** — `--seeds N`, агрегаты min/max/median, frozen multiseed baseline JSON.
3. **`F3-slice1`** — сначала `quote_evidence_grounding`, затем при необходимости `negative_case_refusal`; один controlled baseline refresh.
4. **`F3-slice2`** — только если после slice1 baseline discipline остаётся управляемой; затем `multi_workspace_inspect` (с оговоркой E1).
5. **`F4`** — после появления читаемых артефактов `F1`/`F2`; исследовательский appendix, не core gate.

### 4.0.4 Ожидаемые артефакты Wave F (сводка)

- Обновлённый benchmark summary JSON с блоком `cost_delta` (`F1`).
- Markdown compare / операторская сводка по `F1` (рядом quality + cost).
- `eval/results/baseline-agent-v3-quality-judge-pilot-multiseed.json` (frozen multiseed, `F2`).
- Обновлённый `judge_pilot` + per-axis rubric breakdown в judge JSON (`F3`).
- `eval/results/agent-v3-quality-judge-cross-family-<date>.{json,md}` с `inter_judge_agreement_rate` (`F4`).
- При смене формата summary — точечное обновление [`benchmark-family-promotion-review.md`](../runbooks/benchmark-family-promotion-review.md) (как читать `cost_delta` / multiseed).

### 4.0.5 Wave F — критерий завершения волны (`done when`)

- В одном pilot-артефакте видны **pairwise quality** и **`cost_delta`** (latency + tokens); есть **хотя бы один** live (или эквивалентный operator `subprocess`) compare с краткой текстовой интерпретацией обеих осей (см. §4.1 таблица интерпретации).
- Для того же frozen набора кейсов зафиксирован **multiseed range** (`mean_delta_min` / `max` / `median`), baseline JSON заморожен.
- Выполнен **минимум один** controlled `F3-slice1` (новый срез + пересчёт baseline со stale-маркировкой старого). — ✅ **Closure:** [`wave-f-f3-slice1-closure-2026-05-12.md`](./wave-f-f3-slice1-closure-2026-05-12.md) (фикстуры + `baseline-agent-v3-quality-judge-pilot-multiseed.json` + live pilot JSON).
- `F4` либо выполнен и оформлен как research note, либо явно отложен с причиной (не смешивать с core gate).

### 4.0.6 Статус live evidence (2026-05-12)

✅ **Wave F implementation + live operator artifacts получены** (mock-only этап закрыт, есть live evidence на `judge_mini` и `judge_pilot`):

- **F1/F2 (`judge_pilot`, DeepSeek, `--seeds 3`)**:
  - `eval/results/current-agent-v3-quality-judge-pilot-wavef-live-deepseek-s3-full.{json,md}`;
  - frozen baseline range: `eval/results/baseline-agent-v3-quality-judge-pilot-multiseed.json`
    и dated copy `eval/results/baseline-agent-v3-quality-judge-pilot-multiseed-2026-05-12.json`;
  - summary snapshot: `case_count=13`, `mean_delta=0.2577`, `multiseed.mean_delta_median=0.3808`,
    `multiseed.mean_delta_spread=0.1346`, `cases_with_any_branch_non_ok=0`,
    `cost_delta.latency_p95_ratio=0.9668`.
- **F3-slice1:** ✅ closure note — [`wave-f-f3-slice1-closure-2026-05-12.md`](./wave-f-f3-slice1-closure-2026-05-12.md) (`pilot_quote_grounding_01`, `pilot_negative_refusal_01` в `judge_pilot`, `family_breakdown` в multiseed baseline).
- **F4 (`judge_pilot`, cross-family advisory)**:
  - source artifacts:
    - `eval/results/current-agent-v3-quality-judge-pilot-wavef-live-anthropic-s1-full.{json,md}`
    - `eval/results/current-agent-v3-quality-judge-pilot-wavef-live-openai-s1-full.{json,md}`
    - `eval/results/current-agent-v3-quality-judge-pilot-wavef-live-deepseek-s3-full.{json,md}`
  - aggregate: `eval/results/agent-v3-quality-judge-cross-family-pilot-2026-05-12.{json,md}`;
  - `inter_judge_agreement_rate=0.0769` (`cases_compared=13`) → exploratory signal остаётся шумным, promotion-выводы не делать без дополнительной калибровки D1/D2.

⚠️ **Operator note:** в live subprocess-run'ах `usage_total_tokens` часто `null`, поэтому `cost_delta.tokens_total_ratio` может быть `null`; основная cost-ось на этих прогонах — `latency_p95_ratio`.

---

### 4.1 F1: Latency / token cost ось рядом с pairwise

- **Problem:** pairwise сравнивает **качество** ответа, но не его стоимость. Если `v3` выигрывает 60/40 по pairwise и при этом +60 % токенов и +30 % latency — это не однозначный win; release-train должен видеть обе оси.
- **Implementation slice:** расширить агрегаты поверх per-case полей `branch_outcome_v1` (`latency_ms_*`, `usage_total_tokens_*`); без новой продуктовой логики агента. Добавить в сводку pilot JSON блок `cost_delta` (p95 latency + totals + ratios). Опционально advisory: `trace_regression_compare.py --max-tokens-ratio` / `--max-latency-ratio`. Если `agent_tool_use_summary_enabled` остаётся **off / gated** (Wave E2), это **не** блокирует F1: ограничение только на **интерпретацию** token totals рядом с `side_llm_cache_read_ratio_avg`.
- **Artifacts:** обновлённый `eval/results/current-agent-v3-quality-judge-pilot.json` (или эквивалентный canonical summary path из [`eval/agent_v3_quality/README.md`](../../eval/agent_v3_quality/README.md)); MD-сводка с двумя осями; при необходимости — фрагмент в promotion runbook.
- **Acceptance:**
  - `runner` пишет per case `latency_ms_baseline` / `latency_ms_candidate` и `usage_total_tokens_baseline` / `usage_total_tokens_candidate` (база уже в `branch_outcome_v1` — добить агрегатами p95/totals/ratios).
  - Summary получает блок `cost_delta`:

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

  - markdown summary показывает **обе** оси рядом.
  - `trace_regression_compare.py`: `--max-tokens-ratio` / `--max-latency-ratio` (advisory).
- **Stop condition:** если инфраструктурно нельзя стабильно собрать usage/latency из runner (пропуски &gt; порога) — зафиксировать gap, не расширять `F3` до починки сбора метрик.
- **Dependencies:** нет жёсткой блокировки от Wave D. **Интерпретация:** всегда рядом с `side_llm_cache_read_ratio_avg` (Wave E2) при анализе token totals.

**Интерпретация результатов (операторский гайд):**

| Ситуация | Чтение |
|----------|--------|
| Pairwise win + cost regression (tokens/latency хуже) | Не однозначный win; отдельное решение в release runbook. |
| Pairwise neutral + cost improvement | Возможный engineering win без сдвига judge. |
| Pairwise gain при низком `side_llm_cache_read_ratio_avg` | Проверить overhead side-LLM / provider cache; не трактовать как «дешёвый» win без контекста E2. |

### 4.2 F2: Multi-seed variance baseline

- **Problem:** одна цифра `mean_delta` от одного pilot-прогона — обманчивая «точность»; нужен **range** и медиана.
- **Implementation slice:** `science-graphrag-agent-v3-quality-benchmark --seeds N` (default 1; для variance — 3). Перед серией прогонов зафиксировать **frozen** judge prompt (`judge_prompt_fingerprint` / D2), **frozen** набор кейсов и явные **environment assumptions** (judge model / endpoint / provenance даты) в `run_metadata`. Агрегация по seed: `mean_delta_min`, `mean_delta_max`, `mean_delta_median`, явный spread. F2 **не** «чинит» Wave D — только даёт честный диапазон поверх текущей стабильности judge. Заморозить `eval/results/baseline-agent-v3-quality-judge-pilot-multiseed.json`.
- **Artifacts:** multiseed JSON + MD операторской сводки; ссылка на frozen `judge_prompt_fingerprint` и case set (как в D2).
- **Acceptance:**
  - `--seeds N` в runner.
  - Агрегаты `mean_delta_min` / `mean_delta_max` / `mean_delta_median` по seed-ам.
  - Frozen baseline range файл multiseed.
  - Пересмотр promotion thresholds в [`agent-unified-plan-doing-and-benchmarks-2026-05-08.md`](./agent-unified-plan-doing-and-benchmarks-2026-05-08.md) §C.1: ориентир **`mean_delta_median ≥ 0`**, не «один прогон ≥ 0».
- **Stop condition:** если при 3 seed spread нестабилен / не даёт воспроизводимого median signal — **не** увеличивать N в этой волне; зафиксировать advisory-only статус и перейти к `F3-slice1` или итерации Wave D.
- **Dependencies:** fingerprint discipline **Wave D / D2** не должна противоречить прогону (тот же `judge_prompt_sha256`). Если Wave D `--strict` всё ещё красный — `F2` **не** использовать как аргумент для promotion, только как диапазон для engineering visibility.

### 4.3 F3: Расширение rubric / новые продуктовые срезы

Текущие срезы (см. unified plan §5.2): `workspace_stats`, `catalog_resolution`, `quote_evidence`, `dual_evidence_compare`, `relation_tracing`, `open research`.

**Приоритет внутри волны (slice order):**

1. **`quote_evidence_grounding`** — отдельный срез: «сколько % утверждений в ответе закрыты quotes из `paper_quote_search`», без overlap с `dual_evidence_compare`.
2. **`negative_case_refusal`** — пара кейсов: корректный отказ (workspace empty / off-domain).
3. **`multi_workspace_inspect`** — стресс на routing churn (2+ workspace); **только после** slice1 и с оговоркой **Wave E1 keep gated** — не путать с default-on evidence.

- **Problem:** расширить продуктовое покрытие judge suite без потери дисциплины baseline/holdout.
- **Implementation slice:** добавить кейсы в `judge_pilot` контролируемыми батчами; per-axis breakdown в judge JSON; пересчёт baseline с пометкой предыдущего как stale.
- **Artifacts:** обновлённый frozen pilot set; judge JSON с rubric per case; baseline compare артефакты.
- **Acceptance:**
  - До **6** новых кейсов в `judge_pilot` (frozen, **без** пересечения с holdout) — можно разбить на slice1/slice2, не обязательно одним PR.
  - Per-axis breakdown в judge JSON (rubric scores per case).
  - После расширения: baseline `mean_delta` пересчитан; старый baseline помечен **stale** с provenance.
- **Stop condition:** не совмещать в одном цикле волны: крупное расширение rubric + много новых кейсов + перекрой promotion thresholds — сначала **один** controlled baseline refresh после slice1.
- **Dependencies:** `multi_workspace_inspect` зависит от понимания routing/churn (**E1**); не использовать как gate для default-on флагов.

### 4.4 F4: Cross-family judge (advisory exploratory)

- **Problem:** один judge model — корреляция с одной моделью; риск self-preference, если judge и candidate из одного «семейства».
- **Implementation slice:** experimental `--judge-model-family` (`deepseek` | `anthropic` | `openai`); три прогона на одних кейсах с разными judge family; метрика `inter_judge_agreement_rate`.
- **Artifacts:** `eval/results/agent-v3-quality-judge-cross-family-<date>.{json,md}`; короткий decision note (robust vs вернуться к D1).
- **Acceptance:**
  - Флаг `--judge-model-family`.
  - 3 прогона, разные family.
  - Артефакт с `inter_judge_agreement_rate`.
  - Если `inter_judge_agreement ≥ 0.7` — pairwise можно считать более robust **в исследовательском смысле**; если ниже — отдельный issue / возврат к D1 / промпт-калибровке (не автоматический gate).
- **Stop condition:** не запускать до появления читаемых **F1 + F2** артефактов (иначе смешиваются cost axis, seed variance и judge-family шум).
- **Dependencies:** D1, D2 желательны (без них шум перебьёт сигнал). **Non-goal:** не выбирать canonical judge по итогам F4 в этой волне.

**Зависимости (summary):** D1/D2 — для осмысленного F4; F1 — не блокируется D strict; F2/F4 для promotion — только после зелёного D §8.1 или явного advisory disclaimer.

---

## 5. Wave G — trace-review discipline as engineering KPI

**Цель:** не «runbook есть, иногда запускаем», а measurable gate на каждое касание агентного кода.

**Статус (2026-05-12):** ✅ **DONE**.

- `G1`: закрыт через CI-only hotspot reminder в `.github/workflows/agent-sse-contract.yml` и SOP-матрицу выбора `profile` / `suite`; локальный git hook сознательно не вводился.
- `G2`: закрыт через machine-readable warn allowlist (`acceptable_warns`, `acceptance_summary.unacceptable_warns`), hard gate `tool_loop_repeat_max > 3`, baseline latency policy (`>=25%` warn, `>50%` fail) и явное документирование lifecycle thresholds.
- `G3`: закрыт без новой writer-метрики: существующий `writer_oscillation_count` доведён до strict acceptance policy (`writer_oscillation_count_max <= 1`, regression delta `>= 2` fail), отражён в `acceptance_summary` и покрыт compare tests.
- Quality gate: `tests/scripts/live_check/test_trace_review_schema.py`, `tests/scripts/live_check/test_trace_regression_compare.py`, `tests/scripts/live_check/test_agent_trace_review.py` — **63 passed**; `black --check`, `isort --check-only`, IDE lints — clean.

### 5.1 G1: Auto-trigger trace-review на изменения hotspot путей

**Статус:** ✅ **DONE 2026-05-12** — реализован CI reminder/job без локального hook; фактический hotspot scope и profile/suite matrix закреплены в [`agent-trace-review-sop.md`](../runbooks/agent-trace-review-sop.md).

**Acceptance:**
- CI job (`agent-sse-contract`) при изменении hotspot-путей выводит reminder про `trace-review-v1` acceptance run; фактический `agent_v2` путь — `science_graphrag/api/agent_v2.py`;
- runbook section в [`agent-trace-review-sop.md`](../runbooks/agent-trace-review-sop.md) обновлён: какой profile (`quick` / `default` / `heavy`) и suite (`default` / `acceptance`) под какой класс правок;
- разделение «merge-блокирующих» полей (`final_answer_missing_count`, `missing_span_count`, `tool_loop_repeat_max`, `writer_oscillation_count_max`, `latency_p95_ms` hard drift) и «advisory drift» (`compaction_churn_score`, `shortlist_ratio_avg`) — формально в runbook.

### 5.2 G2: Explicit alert thresholds в decision_gate / acceptance

**Статус:** ✅ **DONE 2026-05-12** — acceptance verdict получил явный allowlist/summary для warn reasons; `tool_loop_repeat_max`, latency drift и lifecycle thresholds стали явными gates/policies.

Warn от `claim_verification_verdict_parse_rate:absent_no_cv_rows` is by-design; теперь он оформлен как `acceptable_warns`, а остальные warn reasons вне allowlist попадают в `acceptance_summary.unacceptable_warns`.

**Acceptance:**
- `eval/results/trace-review-acceptance-*.json` schema получает поле `acceptable_warns` (список регулярок);
- любой warn вне списка попадает в `acceptance_summary.unacceptable_warns` и требует explicit waiver/release note;
- `tool_loop_repeat_max > 3` → `fail` в single-run verdict и отдельный `acceptance_summary` gate;
- `latency_p95_ms` drift ≥ 25 % от baseline → `warn`; ≥ 50 % → `fail` в `trace_regression_compare.py` default policy.

### 5.3 G3: writer_oscillation_count metric (новая)

**Статус:** ✅ **DONE 2026-05-12** — метрика уже существовала; закрытие Wave G довело её до строгого acceptance/compare contract и тестового покрытия.

**Зачем:** для E3 нужна явная метрика, не просто наблюдение.

**Acceptance:**
- в `trace-review-v1` добавлена `writer_oscillation_count` per case — число поворотов «writer → not-writer → writer» в одном turn;
- baseline на acceptance suite ≤ 1; `acceptance_summary` получает отдельный `§G3_writer_oscillation_count` gate;
- регрессия: при росте baseline ≥ 2 — fail через `writer_oscillation_increase`; candidate cap `writer_oscillation_count_max > 1` — fail.

---

## 6. Wave H — context compaction maturity

**Цель:** L3 / L4 продакшен-готовность, чтобы длинные сессии не «тонули» в `ToolMessage` истории.

**Статус (2026-05-12):** implementation + offline harness + regression tests **закрыты**; operator default-on остаётся только для gated knobs — каноническое решение и артефакты: [`wave-h-rollout-decision-2026-05-12.md`](./wave-h-rollout-decision-2026-05-12.md), inventory scope §H2: [`wave-h-side-llm-inventory-2026-05-12.md`](./wave-h-side-llm-inventory-2026-05-12.md).

### 6.1 H1: Production-ready microcompact / restore / sanitizers

**Acceptance (код + offline):** ✅ — 50-turn harness, restore paper sources regression, sanitizer fixtures; default-on см. rollout table (**microcompact time trigger — keep gated** до live).

### 6.2 H2: Cache-safe forked side-LLM (L4 compact)

**Acceptance (минимальный честный scope):** ✅ L4 `llm_history_compact` → `run_side_llm_chat` + telemetry; «все субагенты ReAct» **вне** H2 по inventory.

### 6.3 Остаток только operator rollout

- **`agent_llm_full_history_compact_enabled`:** live long-thread trace-review + compare (`--min-side-llm-cache-read-ratio 0.4`, `--paper-sources-restored-fail-on-loss`) — см. [`agent-trace-review-sop.md`](../runbooks/agent-trace-review-sop.md) §9.3–9.5.
- **`agent_tool_message_microcompact_time_trigger_enabled`:** paired live compare перед default-on.
- **OpenRouter `cache_control`:** только если live ratio &lt; 0.4 без hint.

---

## 7. Cadence и зависимости

```
Wave A (DONE 2026-05-08)
   └─ Wave B (DONE 2026-05-08)
      └─ Wave C (DONE 2026-05-09)
         ├─ Wave D (tooling DONE; §8.1 strict gate open → advisory defer)
         ├─ Wave E (E1 keep gated; E2 PR1–2 code done / PR3 operator; E3/E4 done)
         ├─ Wave F (F-core evidence done; F3-slice2+ optional)
         ├─ Wave G (DONE)
         └─ Wave H (implementation DONE; live rollout for gated defaults)
```

| Неделя (примерная, не CI) | Фокус |
|---------------------------|-------|
| Now | Закрыть Wave D §8.1 **или** держать advisory defer; повторить E2 heavy live после PR1+2; Wave H live rollout по SOP §9 |
| Next | F3-slice2+ только при управляемой baseline-дисциплине; structural split trace-review (backlog) |

Wave H live rollout логично **после** свежего E2/D сигнала, но **не** блокируется ими для read-only evidence run.

---

## 8. Acceptance gates на следующий цикл

Чтобы план не превратился в «новые волны без закрытия предыдущих», два явных gate:

### 8.1 Gate «Wave D готов к промоушн review»

**Статус на 2026-05-12:** gate **не** выполнен на live окне 2026-05-13; зафиксирован **advisory-only defer** — см. [`pre-f-closure-wave-d-evidence-2026-05-12.md`](./pre-f-closure-wave-d-evidence-2026-05-12.md) §6.

- D1, D2, D3 **в смысле gate** = live артефакты и стабилизация (не только наличие CLI в репозитории; инструментарий уже см. §1.2 / §2);
- 3 stable pilot прогона `judge_pilot` без `cases_with_any_branch_non_ok ≥ 1`;
- `mean_delta` median не ниже `−0.05` против baseline;
- `judge_prompt_fingerprint` не менялся ≥ 2 недель;
- variance multi-seed (F2) показал spread ≤ 0.15.

После закрытия — **отдельный** PR с promotion review checklist (по [`benchmark-family-promotion-review.md`](../runbooks/benchmark-family-promotion-review.md)). Решение «advisory → core» принимают мейнтейнеры; **не** делается автоматически по числам.

### 8.2 Gate «engine baseline стабилен после Wave E»

- E1: live paired **2026-05-13** — [`wave-e-e1-rollout-decision-2026-05-10.md`](./wave-e-e1-rollout-decision-2026-05-10.md); итог **keep gated** (p95); default-on не доказан.
- E2 cache ratio: non-null telemetry при `tool_use_summary_row_count_total > 0` (**код**); порог `>= 0.4` для default-on — **операторски** (см. [`pre-f-closure-readiness-2026-05-12.md`](./pre-f-closure-readiness-2026-05-12.md)).
- E3 writer oscillation closure done (**done**);
- backlog `[PARTIAL] Simplify writer_agent into terminal synthesis seam` → `[DONE]` (**done**).

**Проверка по артефактам репозитория (Wave E implementation, 2026-05-10):**

- **Harness / compare:** единый цикл в [`docs/runbooks/agent-trace-review-sop.md`](../runbooks/agent-trace-review-sop.md) §5.1 (имена JSON/MD, env-профили baseline/candidate, флаги `trace_regression_compare.py`).
- **E3:** метрики `writer_oscillation_count` в `scripts/live_check/trace_review_schema.py`; политика регрессии `--max-writer-oscillation-count`, `--fail-on writer_oscillation_increase`; shadow knob `SCIENCE_GRAPHRAG_AGENT_WRITER_TERMINAL_SINGLE_PASS_SHADOW_ENABLED`.
- **E2:** регрессия cache-safe вызова side-LLM и floor ratio — `tests/agent/test_tool_use_summary_cache_safety.py`; gate compare — `--min-side-llm-cache-read-ratio 0.4`.
- **E4:** `PATCH /v1/settings/agent_tools` + overlay `agent_supervisor_max_rounds` (см. тесты в `tests/test_*`).
- **E1 / решение default-on:** шаблон и критерии — [`wave-e-e1-rollout-decision-2026-05-10.md`](./wave-e-e1-rollout-decision-2026-05-10.md); финальный вывод фиксируется оператором после двух live прогонов (артефакты под `eval/results/agent-corpus-explore-research-plan-acceptance-<date>.*`).

После этого backlog по агентскому графу находится в основном в **operator gates** (Wave D §8.1, E2 PR3, E1 default-on, Wave H live) и в **[OPEN] structural** задачах в [`refactor-backend.md`](../backlog/refactor-backend.md) — не путать с волнами F/H выше.

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
| Pre-F closure readiness (2026-05-12) | [`pre-f-closure-readiness-2026-05-12.md`](./pre-f-closure-readiness-2026-05-12.md) |
| Pre-F Wave D operator evidence | [`pre-f-closure-wave-d-evidence-2026-05-12.md`](./pre-f-closure-wave-d-evidence-2026-05-12.md) |
| Wave D §8.1 advisory defer | [`pre-f-closure-wave-d-evidence-2026-05-12.md`](./pre-f-closure-wave-d-evidence-2026-05-12.md) §6 |
| Wave F F3-slice1 closure | [`wave-f-f3-slice1-closure-2026-05-12.md`](./wave-f-f3-slice1-closure-2026-05-12.md) |
| Wave H rollout decision | [`wave-h-rollout-decision-2026-05-12.md`](./wave-h-rollout-decision-2026-05-12.md) |
| Wave H side-LLM inventory | [`wave-h-side-llm-inventory-2026-05-12.md`](./wave-h-side-llm-inventory-2026-05-12.md) |
| **Structural debt (не waves):** split trace-review / compare monoliths | [`refactor-backend.md`](../backlog/refactor-backend.md) `[OPEN] Split trace-review CLI…` |
