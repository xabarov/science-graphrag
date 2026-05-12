# Wave H — side-LLM call sites inventory (2026-05-12)

**Цель документа:** зафиксировать, какие LLM-вызовы попадают в scope Wave H §H2
(«все side-LLM пути идут через `run_side_llm_chat`») и какие — намеренно нет,
с явной причиной. Это вход для PR'ов миграции и для последующего decision note по
`side_llm_cache_read_ratio_avg`.

Источник плана: [`agent-engine-and-benchmarks-next-waves-2026-05-09.md`](./agent-engine-and-benchmarks-next-waves-2026-05-09.md) §6.2.

## Что считается side-LLM в смысле Wave H

`run_side_llm_chat` ([`science_graphrag/agent/forked_runtime.py`](../../science_graphrag/agent/forked_runtime.py))
— один shared seam для **одношаговых summary-вызовов** агента: стабильный
`system + optional prefix + human` payload, без `bind_tools`, без ReAct-цикла,
с обязательным сбором cache telemetry (`side_llm_cache_read_tokens`,
`side_llm_cache_creation_tokens`, `side_llm_cache_read_ratio`).

Поэтому «side-LLM» здесь — это **summary/consolidation-style** одношаговая
LLM-консультация, а **не** любая часть LLM-стека.

## In scope (миграция в H2)

| Путь | Текущий механизм | Целевой статус |
|------|------------------|----------------|
| **L4 full-history compact** — [`science_graphrag/agent/context/llm_history_compact.py::_invoke_summary_llm`](../../science_graphrag/agent/context/llm_history_compact.py) | Прямой `build_chat_model + llm.invoke([System, Human])`; cache-telemetry **не** собирается; PTL-retry на context-limit. | Заменить на `run_side_llm_chat`, прокинуть `SideLlmRunResult` cache fields в `audit` dict (`side_llm_cache_read_*`, `side_llm_cache_read_ratio`, `forked`). PTL-retry сохранить. |

В Wave H §H2 это **единственный** обязательный код-таргет миграции: остальные
кандидаты ниже либо не имеют LLM-вызова, либо принципиально не one-shot summary
shape.

## Out of scope (с обоснованием)

### `away_summary` — деталь архитектуры, **нет LLM**

`Settings.agent_away_summary_enabled` управляет вставкой блока
`<away_recap>` в prompt при достаточно длинном `client_idle_ms`
(см. [`science_graphrag/agent/graph/state.py`](../../science_graphrag/agent/graph/state.py)
строки `agent_away_summary_*`). Текст рассчитывается **детерминированно**
(`away_lines = ["User returned after ...", ...]`); LLM-вызов отсутствует.

**Решение:** не входит в H2; миграция не нужна. Если в будущем away_summary
станет LLM-driven, добавить как новый workstream.

### `agent_note` — короткий narration UX, off-by-default

[`science_graphrag/agent/notes.py`](../../science_graphrag/agent/notes.py)
делает one-shot LLM call с per-event `max_tokens=64` и hard timeout. Кэш не
имеет смысла: контент уникален почти для каждого вызова (текущий tool / route),
prompt-cache hit ratio структурно низкий.

**Решение:** оставить вне H2. Может остаться через `build_chat_model` напрямую;
если позже понадобится телеметрия — рассматривать отдельно, без deal-breaker
для Wave H acceptance.

### `llm_turn_classifier` / `tool_selector_hybrid` — структурный JSON, не summary

[`science_graphrag/agent/coordination/llm_turn_classifier.py`](../../science_graphrag/agent/coordination/llm_turn_classifier.py)
и
[`science_graphrag/agent/tool_selector_hybrid.py`](../../science_graphrag/agent/tool_selector_hybrid.py)
— это per-turn classification / rerank. Уже идут через `invoke_chat_gated` (тот же
concurrency pool). Output-shape — structured JSON, не «merge digests / shrink
payload».

**Решение:** не мигрировать в H2. Они получают cache telemetry (если провайдер
прислал) через свой path, но не должны делить cache-prefix с summary-style
вызовами — структурно разный prompt.

### Subagent runtimes — ReAct, не one-shot

- [`science_graphrag/agent/subagents/claim_verification_runtime.py`](../../science_graphrag/agent/subagents/claim_verification_runtime.py)
- [`science_graphrag/agent/subagents/corpus_explore_runtime.py`](../../science_graphrag/agent/subagents/corpus_explore_runtime.py)
- [`science_graphrag/agent/subagents/research_plan_runtime.py`](../../science_graphrag/agent/subagents/research_plan_runtime.py)

Используют `build_chat_model().bind_tools(tools)` плюс ReAct-цикл с переменной
историей сообщений. По форме это **multi-turn agent** под supervisor, не
one-shot summary с предсказуемым system+prefix. Текущая интеграция через
fork-bundle entrypoints (`run_*_fork_bundle` в `forked_runtime.py`) уже даёт
изоляцию состояния и telemetry-точку.

**Решение:** не входит в H2. Совмещать ReAct fork bundles и `run_side_llm_chat`
в одном seam'е значит ломать «cache-stable prefix» инвариант. Если в субагентах
понадобится отдельный summary-step, его добавление через `run_side_llm_chat`
рассматривать как отдельный slice.

### `tool_use_summary` — уже на helper'е

[`science_graphrag/agent/tool_use_summary.py`](../../science_graphrag/agent/tool_use_summary.py)
уже использует `run_side_llm_chat`. Регрессия — `tests/agent/test_tool_use_summary_cache_safety.py`.

**Решение:** in scope для Wave E2 gate `side_llm_cache_read_ratio_avg ≥ 0.4`,
но миграции в H2 не требует.

### `thread_insights` — уже на helper'е (Train T1)

`synthesize_thread_insight_markdown` в `forked_runtime.py` использует
`run_side_llm_chat` начиная с Train T1 (см. backlog
[`docs/backlog/refactor-backend.md`](../backlog/refactor-backend.md) запись
`Cache-safe forked side-LLM helper (§10.2)`).

**Решение:** не требует миграции; оставить как baseline cache-share образец.

## Acceptance Wave H §H2 (после миграции)

1. `science_graphrag/agent/context/llm_history_compact.py` не вызывает
   `build_chat_model(...).invoke(...)` напрямую — только через
   `run_side_llm_chat`.
2. `audit` dict L4 включает поля `side_llm_cache_read_tokens`,
   `side_llm_cache_creation_tokens`, `side_llm_cache_read_ratio`, `forked`
   (даже если значения `None`).
3. Существующие тесты `tests/agent/test_llm_history_compact.py` остаются
   зелёными (с обновлённым monkeypatch на `run_side_llm_chat`).
4. Trace-review/compare видят `side_llm_cache_read_ratio` от L4 path там, где
   она ранее была `null` only-because-of-missing-telemetry.

## Что **не** acceptance Wave H §H2

- Production switch-on `agent_llm_full_history_compact_enabled=True` —
  отдельное rollout-решение по итогам long-thread acceptance (см. §H1
  workstream и общий decision note).
- Включение default-on `agent_tool_use_summary_enabled` — gate Wave E2,
  не цель Wave H.
- Миграция `agent_note` / `llm_turn_classifier` / subagents — out of scope
  по причинам выше; при необходимости — отдельные workstreams.

## Сводка

Минимальный честный scope Wave H §H2 — **один путь** (`llm_history_compact`).
Это снижает риск «миграции ради миграции» и делает acceptance §H2 проверяемой
одной парой PR (код + тест) без изменения семантики ReAct-субагентов или
classifier'а.
