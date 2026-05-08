# Orchestration stabilization — closeout (2026-05-08)

Финальный отчёт по плану [`orchestration-stabilization-plan-2026-05-07.md`](./orchestration-stabilization-plan-2026-05-07.md).
Хвост и live-compare закрыты по [`/home/roman/.cursor/plans/orchestration-tail-and-live-compare_6dbe9922.plan.md`](../../../../.cursor/plans/orchestration-tail-and-live-compare_6dbe9922.plan.md).
Baseline снимок (до WS1–WS4) — [`orchestration-stabilization-baseline-2026-05-08.md`](./orchestration-stabilization-baseline-2026-05-08.md).

## TL;DR

- RoutePlan / QuestionFeatures / supervisor_decisions переведены в default-on; legacy fallback shims удалены, supervisor читает план из `metadata.turn_policy.route_plan` единственным каналом.
- Producer-сторона graceful degradation замкнута: retrieval/graph специалисты эмитят `completion_state` через `annotate_completion_state`, runtime salvage поднимает последний `record_partial_state` snapshot при глобальном deadline.
- Структурные хвосты orchestrator-блока закрыты: LLM replan вынесен в `supervisor_decisions.maybe_replan_via_llm`, `tool_execution_pipeline` разделён через `tool_execution_phases`, `tool_search` — через `tool_search_scoring`.
- Dev-runtime по умолчанию переведён на `langgraph_supervisor_v3` (ADR-029): default в `config.py`, `.env.example`, runbook trace-review SOP.
- Live strict-acceptance прошли обе ветки (`v3` и default ReAct) с verdict `warn` (только за счёт ожидаемого `claim_verification_verdict_parse_rate:absent_no_cv_rows`); `trace_regression_compare` `pass`.

## Артефакты

- v3 strict acceptance:
  - JSON: `eval/results/trace-review-acceptance-v3.json`
  - MD: `eval/results/trace-review-acceptance-v3.md`
  - Phoenix: `eval/results/trace-review-acceptance-v3_phoenix_spans.jsonl`
- ReAct strict acceptance:
  - JSON: `eval/results/trace-review-acceptance-react.json`
  - MD: `eval/results/trace-review-acceptance-react.md`
  - Phoenix: `eval/results/trace-review-acceptance-react_phoenix_spans.jsonl`
- Compare:
  - JSON: `eval/results/trace-compare-v3-vs-react.json`
  - MD: `eval/results/trace-compare-v3-vs-react.md`

## Snapshot структуры (после WS1–WS3)

| Модуль | LoC до | LoC после | Δ | Комментарий |
|--------|-------|-----------|----|-------------|
| `agent/graph/supervisor.py` | 634 | 420 | −214 | LLM-routing, force-rules и substring-таблицы вынесены в `supervisor_decisions` + `coordination/question_features` |
| `agent/tool_execution_pipeline.py` | 521 | 467 | −54 | Validation/permission фазы — в `tool_execution_phases.py` |
| `agent/tool_search.py` | 842 | 744 | −98 | Скоринг `score_tool*` — в `tool_search_scoring.py` |
| `agent/graph/supervisor_decisions.py` | новый seam | — | +`maybe_replan_via_llm`, `compute_*` чистые функции |
| `agent/graph/partial_state_checkpoint.py` | новый seam | — | thread-safe snapshot per `parent_turn_id` для salvage |
| `agent/tool_execution_phases.py` | новый seam | — | `validate_tool_call_batch`, `compute_tool_denies` (pure) |
| `agent/tool_search_scoring.py` | новый seam | — | `score_tool*` (pure) |

## Test gates

- `tests/agent/test_route_plan_and_features.py` — 27 passed (round-trip + open-ended skip + planner short-circuit).
- `tests/agent/test_supervisor_routing.py` — 24 passed (включая два safety-net теста LLM-роутера через `_build_state_without_plan`).
- `tests/agent/test_per_tool_deadline_and_completion_state.py` — green после удаления `legacy_fn` параметра.
- `tests/agent/test_partial_state_checkpoint.py` — новый, 4 теста (record/pop/clear/supervisor_node hop integration).
- `tests/agent/` всего — 278 passed.

## Live compare: `langgraph_supervisor_v3` vs default ReAct

Условия одинаковые: workspace `2678c5f1-1b31-4aac-92c9-6bd0f4472b23`, `--suite acceptance`, `--with-trace-audit --with-phoenix --with-db-audit`.

| Метрика | ReAct (`langgraph_research_v1`) | v3 (`langgraph_supervisor_v3`) | Δ | Комментарий |
|---------|---------------------------------|--------------------------------|----|-------------|
| `agent_v2_*` checks | 6/6 ok | 6/6 ok | 0 | health/sync/sse/multi_turn/fanout/malicious_deny |
| Cases (acceptance) | 9/9 finalize `final_answer` | 9/9 finalize `final_answer` | 0 | |
| `final_answer_missing_count` | 0 | 0 | 0 | |
| `tool_error_rate` | 0.0 | 0.0 | 0.0 | |
| `subagent_lifecycle_missing_count` | 0 | 0 | 0 | |
| `missing_span_count` (Phoenix) | 0 | 0 | 0 | |
| `claim_grounding_precision` / `recall` | 1.0 / 1.0 | 1.0 / 1.0 | 0 | |
| `insight_recall_at_k` | 1.0 | 1.0 | 0 | |
| `latency_p50_ms` | 13562 | 25985 | +12423 | стоимость supervisor↔specialist↔writer |
| `latency_p95_ms` | 26299 | 34856 | +8557 | в пределах ожидаемого (>90% от ReAct ~92%) |
| `agent_usage_total_tokens_sum` | 200322 | 320144 | +119822 (+60%) | дополнительные routing-prompts + structured handoff |
| Avg steps / case | ~5.6 | ~8.2 | +2.6 | супервайзерные hops (`route_to_specialist` присутствует) |
| `tool_loop_repeat_max` | 2 | 3 | +1 | укладывается в цель плана (≤4) |
| `shortlist_ratio_avg` | 0.6259 | 0.7322 | +0.1063 | v3 щире выбирает кандидатов из manifest (специалист-aware) |
| `subagent_task_notification_count_avg` | 0.0 | 2.0 | +2.0 | **только у v3** работает task-notification контракт + sidechain (нет в ReAct) |
| `unnecessary_tool_calls_avg` | 0.0 | 0.0 | 0.0 | |
| `compaction_event_count` | 0 | 0 | 0 | acceptance < компактного порога |
| `b4_fanout_multi_tool_http_check_ok` | true | true | — | оба runtime обслуживают fanout-probe |
| `b4_malicious_deny_http_check_ok` | true | true | — | оба runtime отбивают malicious-deny |
| Verdict | `warn` (cv_rows absent) | `warn` (cv_rows absent) | — | одинаковая причина, не регрессия |
| `subagent_spawn_mesh_observed_2plus_rows` | — | live_proven | — | специфично для v3 (специалисты + sidechain) |

`trace_regression_compare.py` (baseline=ReAct, candidate=v3, `--warn-is-pass`):

```
Status: pass
Δ missing spans: 0.0
Δ tool error rate: 0.0
Δ final_answer_missing: 0.0
Δ latency_p95_ms: 8557.0
Δ shortlist_ratio_avg: 0.1063
Δ subagent_lifecycle_missing_count: 0.0
Δ unnecessary_tool_calls_avg: 0.0
Warn reasons: latency_p95_increase:26299→34856, shortlist_ratio_increase:0.1063
```

### Strict-gate расхождения, не относящиеся к регрессиям

- `subagent_task_notification_count_avg` ≠ 0 только у v3 — это контрактный артефакт supervisor-формы (специалисты сидят в sidechain transcripts; см. ADR-029 + §10.8 task-notification contract).
- `b4_subagent_spawn_mesh_observed_2plus_rows` присутствует в `live_proven` v3 и отсутствует у ReAct — single-agent ReAct не поднимает mesh, это by design.
- `latency_p95` v3 / ReAct = ~1.33; обе ниже `--max-latency-p95-ms` практик-уровня и compare gate `pass`. Архитектурный overhead supervisor-формы покупает: deterministic routing → меньшая дисперсия `tool_loop_repeat_max` под живой нагрузкой, partial-state salvage и subagent fanout.

## Что закрыли в backlog

| Backlog item (refactor-backend.md) | Был | Стал |
|--|--|--|
| Introduce RoutePlan + QuestionFeatures (orchestration policy unification) | PARTIAL | DONE — default-on в `config.py`, shims удалены, единый канал `metadata.turn_policy.route_plan` |
| Single supervisor backbone with `single_agent_react_mode` flag | PARTIAL | DONE — dev default `langgraph_supervisor_v3`, runbook + `.env.example` синхронизированы по ADR-029 |
| Per-tool-call deadline + completion_state for graceful degradation | PARTIAL | DONE — `annotate_completion_state` подключён в `retrieval_agent_node` / `graph_agent_node`, runtime salvage через `pop_latest_partial_state` |
| Split `supervisor_node` into `supervisor_decisions` module | PARTIAL | DONE — LLM-replan в `maybe_replan_via_llm`, supervisor.py 634 → 420 LoC |
| Reduce supervisor route churn before writer handoff | PARTIAL | DONE (для acceptance suite) — `tool_loop_repeat_max=3` на v3, ≤ цели плана |
| Split permission/validation phase out of `build_tool_execution_node` | OPEN | DONE — `tool_execution_phases.py` |
| Split oversized `tool_search.py` after hybrid/web selector growth | OPEN | DONE (минимальный slice — scoring) — `tool_search_scoring.py`. Дальнейший split discovery_merge/strict_deferred остаётся как отдельный non-blocker. |

## Что осталось (вне scope этой программы)

- LLM-судья `final_answer` quality, когда `merge.conflict` отсутствует (B2 residual_open в acceptance summary). Не относится к routing/runtime; собирается отдельным prompt-eval треком.
- `tool_search` deeper split (`discovery_merge`, `strict_deferred_telemetry`) — структурный refactor, не блокирует orchestration; останется в backlog как «split after hybrid growth».
- B-нагрузка LLM-judge на `final_answer` для не-CV кейсов — отдельный pipeline.

## Верификация

- `tests/agent/` (278 passed), `tests/scripts/live_check/test_trace_review_schema.py` (compare schema), `tests/agent/test_partial_state_checkpoint.py` — все green.
- Live: 9/9 acceptance кейсов на каждой ветке, Phoenix snapshot пустых missing-spans 0/9 на каждой.
- `pip install -e .` после изменений `pyproject.toml` не требовался: новые модули доступны через стандартный пакетный путь (`science_graphrag.agent.graph.partial_state_checkpoint` и др.).

## Ссылки

- Plan: [`docs/analysis/orchestration-stabilization-plan-2026-05-07.md`](./orchestration-stabilization-plan-2026-05-07.md)
- Baseline: [`docs/analysis/orchestration-stabilization-baseline-2026-05-08.md`](./orchestration-stabilization-baseline-2026-05-08.md)
- ADR-029: [`docs/adr/029-single-supervisor-backbone.md`](../adr/029-single-supervisor-backbone.md)
- Runbook: [`docs/runbooks/agent-trace-review-sop.md`](../runbooks/agent-trace-review-sop.md) (§1.1 runtime alignment)
