# Orchestration stabilization — baseline (2026-05-08)

Связано с [`orchestration-stabilization-plan-2026-05-07.md`](./orchestration-stabilization-plan-2026-05-07.md) §6.
Зафиксировано перед стартом реализации фаз 1–7. Используется как gate
(до/после) для измерения регрессий в `tool_loop_repeat_max`,
числе LLM routing-вызовов и формы `tool_trace`.

## Снимок состояния модулей

| Модуль | LoC | Замечание |
|--------|-----|------------|
| `science_graphrag/agent/graph/supervisor.py` | 634 | R0911/R0912/R0915 в closure `supervisor_node`; смешаны: gating, force-rules, route_hint, fast-route, round cap, LLM-routing |
| `science_graphrag/agent/runtime.py` | 889 | R0914 в `_run_langgraph` (не в скоупе текущей программы) |
| `science_graphrag/agent/graph/nodes/retrieval_agent.py` | 574 | специалист, потребитель completion-сигналов в Phase 6 |
| `science_graphrag/agent/coordination/deterministic.py` | 240 | regex/substring-эвристики (`_GRAPH_INTENT_HINTS`, `_RESEARCHISH`, `_GRAPH_CITATION_RELATIONISH`) |
| `science_graphrag/agent/coordination/turn_policy.py` | 194 | `rules_v0` / `hybrid_v1` / `llm_v1` |
| `science_graphrag/agent/tool_execution_pipeline.py` | 419 | place для per-tool deadline (Phase 6) |

## Текущие источники истины маршрута

1. `narrow_deterministic_classify` / `rules_v0_classify` (deterministic).
2. `TurnPolicy` `hybrid_v1` (LLM может перебить `route_hint` для `FUZZY_RULES_V0_REASONS`).
3. LLM-роутер супервизора (вызывается на каждый hop).
4. Эвристики в `supervisor_node`:
   - `_should_force_retrieval_first_hop_workspace_dual_evidence`,
   - `_maybe_force_writer_after_retrieval` (workspace_stats / catalog_resolution / dual_evidence_compare / quote_evidence),
   - round cap `agent_supervisor_max_rounds`.

## Runtime backbone (по `Settings.agent_runtime`)

| ID | Граф | `tool_trace` имеет `route_to_specialist` |
|----|------|-------------------------------------------|
| `langgraph_research_v1` (default) | single-agent ReAct | нет |
| `langgraph_supervisor_v1` | supervisor → specialists → writer | да |
| `langgraph_supervisor_v3` | supervisor → specialists → writer (+ subagents v3) | да |
| `retrieval_v1` | legacy harness | (single-agent fallback) |

## Тестовый baseline (2026-05-08, `.venv` / pytest -q)

- `tests/agent/test_supervisor_routing.py` — 24 passed.
- `tests/agent/test_graph_intent_heuristic.py` — passed.
- `tests/agent/test_turn_policy.py` — passed.

(Combined: 40 passed, см. вывод `pytest`.)

## KPI цели программы (повтор §6 stabilization plan)

- `tool_loop_repeat_max` ≤ 4 на acceptance-наборе после полной миграции
  (Phase 1–4) — измеряется через
  [`scripts/live_check/agent_trace_review.py`](../../scripts/live_check/agent_trace_review.py).
- Один формат `tool_trace` в dev/staging/acceptance после Phase 5.
- Hang отдельного tool-call → partial answer + warning, не пустой deadline.
- `supervisor.py` < 400 LoC; никаких новых веток в `supervisor_node`
  для каждого нового acceptance-кейса (Phase 1 + 7).

## Точки записи для будущих итераций

- Любое regression-сравнение должно явно указывать `agent_runtime`,
  чтобы dev-smoke и acceptance не сверялись через разные backbone.
- При добавлении нового acceptance-кейса
  обновлять `QuestionFeatures` и `RoutePlan`-планировщик, не
  `supervisor_node` (см. Phase 1–3).
