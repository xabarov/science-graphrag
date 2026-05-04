# Инструменты чат-агента — каталог, контракты и карта кода

Документ описывает **инструменты LangChain**, доступные research chat-агенту в режиме по умолчанию: что модель получает на границе с провайдером, как тулзы собираются в Python, где лежит логика. **Rule-based `tool_search` v1** (shortlist схем тулов) уже включён при `SCIENCE_GRAPHRAG_AGENT_RULE_TOOL_SEARCH_ENABLED`; дальнейшее развитие каталога — LLM-discovery, расширение манифеста, компактация контекста (см. §3 и slim roadmap).

**Связанные материалы:** [`docs/specs/agent-chat-v1.md`](../specs/agent-chat-v1.md), [`docs/analysis/chat-agent-system-roadmap-2026-04-26.md`](../analysis/chat-agent-system-roadmap-2026-04-26.md), [`science_graphrag/agent/prompts/research_chat_system.py`](../../science_graphrag/agent/prompts/research_chat_system.py), статический манифест для rule-based отбора: [`science_graphrag/agent/tool_manifest.py`](../../science_graphrag/agent/tool_manifest.py).

---

## 1. Режимы runtime

| `Settings.agent_runtime` | Граф | Реестр тулов |
|--------------------------|------|--------------|
| `langgraph_research_v1` (**по умолчанию**) | Один агент ReAct: `chat` → `tools` → `after_tools` в [`supervisor.py::_build_single_agent_graph`](../../science_graphrag/agent/graph/supervisor.py) | Исполнение: полный [`build_tool_registry`](../../science_graphrag/agent/tools/__init__.py). На **каждый** LLM-ход `chat` при `SCIENCE_GRAPHRAG_AGENT_RULE_TOOL_SEARCH_ENABLED=true` вызывается rule-based [`shortlist_tools_for_single_agent`](../../science_graphrag/agent/tool_search.py) и `bind_tools` только на **подмножество** (см. §3). |
| `langgraph_supervisor_v1` | Supervisor и ноды-специалисты [`build_supervisor_graph`](../../science_graphrag/agent/graph/supervisor.py) | Подмножества: [`build_graph_tools`](../../science_graphrag/agent/tools/__init__.py), [`build_retrieval_tools`](../../science_graphrag/agent/tools/__init__.py), [`build_writer_tools`](../../science_graphrag/agent/tools/__init__.py). |
| `retrieval_v1` | Наследуемый harness | См. [`RetrievalAgent`](../../science_graphrag/agent/runtime.py). |

---

## 2. Сборка и исполнение (Python)

Точка входа реестра:

```python
# science_graphrag/agent/tools/__init__.py
def build_tool_registry(stores: StoreRegistry) -> list[BaseTool]:
    return build_graph_tools(stores) + build_retrieval_tools(stores) + build_writer_tools(stores)
```

- **`build_graph_tools`** — только read-only граф: `cypher_query`, `edge_search` (полнотекст работ — в `find_works`).
- **`build_retrieval_tools`** — [`build_workspace_paper_langchain_tools`](../../science_graphrag/agent/tools/workspace_paper_tools.py) + `idea_search`.
- **`build_writer_tools`** — `final_answer`.

Исполнение тулов в single-agent: [`build_normalized_tool_node_executor`](../../science_graphrag/agent/tool_call_normalization.py) вокруг `ToolNode` (нормализация имён вызовов). Трассы: [`run_tool_result_with_span`](../../science_graphrag/agent/tools/base.py).

---

## 3. Что видит модель

Для каждого инструмента провайдер получает **имя**, **description** (docstring у `@tool`) и **JSON Schema** полей из `args_schema` (Pydantic `Field(description=...)`).

Системный промпт: [`RESEARCH_CHAT_SYSTEM_PROMPT`](../../science_graphrag/agent/prompts/research_chat_system.py) — область, таблица маршрутизации по тулзам, дисциплина fan-out, обязательный `final_answer`.

В **supervisor**-режиме каждый специалист уже получает shortlist + SSE `tool_search_result`. В **single-agent** при включённом rule-based shortlist модель на шаге `chat` видит **суженный** набор JSON-схем тулов (полный реестр остаётся у `ToolNode` для исполнения любого вызова из истории совместимости). Опционально: [`maybe_compact_agent_messages_for_react`](../../science_graphrag/agent/tool_message_compact.py) + `SCIENCE_GRAPHRAG_AGENT_TOOL_HISTORY_COMPACT_ENABLED` — усечение **старых** `ToolMessage` перед LLM. Полный каталог имён в системном промпте: [`RESEARCH_CHAT_SYSTEM_PROMPT`](../../science_graphrag/agent/prompts/research_chat_system.py) (таблица «Tool catalog»).

---

## 4. Каталог (объединённый реестр, 10 инструментов)

| Имя | Назначение (смысл для модели) | Код |
|-----|-------------------------------|-----|
| `cypher_query` | Read-only Cypher, лимит строк; структурные запросы. | [`cypher_query.py`](../../science_graphrag/agent/tools/cypher_query.py) |
| `edge_search` | Рёбра / соседи; нужен внутренний id узла (как `work_id` для работ). | [`edge_search.py`](../../science_graphrag/agent/tools/edge_search.py) |
| `workspace_inspect` | Режимы `stats` / `papers` / `blurb` — обзор workspace без полнотекстового поиска заголовков. | [`workspace_paper_tools.py`](../../science_graphrag/agent/tools/workspace_paper_tools.py) |
| `workspace_graph_reltypes` | DISTINCT `type(r)` на соседях `Work` в workspace — перед фильтром `edge_search(rel_types=...)`. | там же + [`work_graph_schema.py`](../../science_graphrag/agent/tools/work_graph_schema.py) |
| `paper_profile` | Карточка одной работы по **реальному** `work_id`. | там же |
| `find_works` | Полнотекст по работам; с `workspace_id` или по всему графу. | там же |
| `paper_quote_search` | Семантика по чанкам, `quote_candidates` для цитат. | [`paper_quote_search_tool.py`](../../science_graphrag/agent/tools/paper_quote_search_tool.py) |
| `format_bibliography_gost` | Библиография по списку `work_ids` в workspace. | [`format_bibliography_gost_tool.py`](../../science_graphrag/agent/tools/format_bibliography_gost_tool.py) |
| `idea_search` | Эмбеддинг-поиск «идей» в Qdrant. | [`idea_search.py`](../../science_graphrag/agent/tools/idea_search.py) |
| `final_answer` | Финальный ответ + `citations`; `return_direct=True`. | [`final_answer.py`](../../science_graphrag/agent/tools/final_answer.py) |

**Примечание:** класс `EntitySearchTool` остаётся в пакете для совместимости/тестов, но в **`build_graph_tools`** не входит.

---

## 5. Сквозные темы

| Тема | Где |
|------|-----|
| Безопасность Cypher | [`cypher_safety.py`](../../science_graphrag/agent/cypher_safety.py) |
| Нормализация имён тулов | [`tool_call_normalization.py`](../../science_graphrag/agent/tool_call_normalization.py) |
| Манифест имён/тегов (rule-based tool_search) | [`tool_manifest.py`](../../science_graphrag/agent/tool_manifest.py) |
| SSE / API | [`agent_v2.py`](../../science_graphrag/api/agent_v2.py) |

### 5.1 E2E heavy-audit (OD workspace, 2026-04-28)

Прогон: [`scripts/live_check/agent_od_workspace_e2e_audit.py`](../../scripts/live_check/agent_od_workspace_e2e_audit.py) с `--suite heavy --trace-audit` на воркспейсе **Object Detection (clean ingested + claims)**; сверка `tool_trace`, Phoenix REST и эвристик. Ниже — зафиксированные проблемы и направления исправлений.

| Сценарий | Итог | Трейс / симптомы | Действия |
|----------|------|-------------------|----------|
| **multi_compare_bibliography** | Ок | 7 шагов: два `find_works` (разные запросы), два `paper_profile`, `format_bibliography_gost`, `final_answer`. Phoenix: несколько `llm.agent.react_turn`, шум LangGraph (`ChannelWrite`, `route_*`). | Нормальный fan-out. При росте каталога — §6.1 `tool_search`. |
| **graph_ego_methods** | Ответ есть, но **3× ошибка Cypher** | Запросы с `other:Method OR other:Dataset` отклонялись как `forbidden_token:SET` из‑за подстроки **SET** в **`Dataset`**. После исправления валидатора такие MATCH допустимы. `edge_search` с узким `rel_types` дал 0 строк — возможно, в графе нет `MENTIONS_METHOD` / `MENTIONS_DATASET`. | **Сделано:** [`cypher_safety.validate_readonly_cypher`](../../science_graphrag/agent/cypher_safety.py) — запретные ключевые слова только как **целые слова** (`\bSET\b` и т.д.). Дальше: в промпте/описании `cypher_query` напоминать реальные `type(r)` или сначала `edge_search` **без** фильтра типов, затем сужать. |
| **multi_evidence_speed_accuracy** | (ист.) **Нет `final_answer` в `tool_trace`** | Цепочка `workspace_inspect` → `idea_search` → `paper_profile` → `paper_quote_search` → `paper_profile`; длинный текст, `no_quote_found`. | **Закрыто P0** (`final_answer_nudge` + salvage). При флаках — wall-clock / `agent_max_tool_calls`; Phoenix: не смешивать run'ы в одном `trace_id` без scoping — см. мастер-док §2.3. |

**Флаги скрипта:** `--suite default|heavy|full`, `--trace-audit`, `--dry-run`, `--write-report PATH` (append JSONL summary per run для CI). **Коды выхода:** `0` все кейсы ок (в т.ч. последний инструмент в `tool_trace` = `final_answer`, длина ответа ≥ 40), `1` провал приёмки, `2` не найден воркспейс, `3` `/health` не 200. С `--trace-audit` в эвристики входят streak нулевых `edge_search`, streak `paper_profile` с одним и тем же `work_id`, и счётчик шагов `cypher_query` с непустым `error` (см. [`science_graphrag/agent/agent_trace_audit.py`](../../science_graphrag/agent/agent_trace_audit.py)). Канон приёмки trace-audit и план фаз A–D / P0–P3: [`agent-chat-tools-and-trace-audit-master-2026-04-28.md`](../analysis/agent-chat-tools-and-trace-audit-master-2026-04-28.md). Общие практики по промптам и аудиту бандла: [`agent-tools-best-practices.md`](agent-tools-best-practices.md).

**`paper_quote_search`:** при пустом результате payload может содержать `empty_reason`: `empty_query`; `no_hits_workspace_scoped` / `no_hits_for_work` / `no_hits_corpus_wide` (область поиска); `qdrant_unavailable`. Запрос нормализуется так же, как у `idea_search` ([`chunk_retrieval_defaults.normalize_agent_retrieval_query`](../../science_graphrag/agent/tools/chunk_retrieval_defaults.py)). См. [`paper_quote_search_tool.py`](../../science_graphrag/agent/tools/paper_quote_search_tool.py).

**Метаданные работ (фаза A3):** доля null `year`/`venue` на конкретном воркспейсе измеряется вне этого документа; для офлайн-агрегации по сохранённым payload `paper_profile` используйте [`eval/paper_profile_stats.py`](../../eval/paper_profile_stats.py) (`summarize_paper_profile_payloads`).

---

## 6. Планы

### 6.1 `tool_search` и отложенные полные схемы

См. roadmap §4.1: короткий каталог в промпте, rule/tag shortlist, eval-ворота. **Сделано для single-agent:** per-turn `shortlist_tools_for_single_agent` перед `bind_tools` (флаг `SCIENCE_GRAPHRAG_AGENT_RULE_TOOL_SEARCH_ENABLED`). Отдельный LLM-callable тул `tool_search` — по-прежнему в планах при дальнейшем росте каталога.

### 6.2 Компактация контекста

Roadmap §4.2 (L0–L4): digest сессии, капсулы, границы полного сжатия; пересечение с `context_compacted`, `session_summary` в API.

### 6.3 Отдельные subgraph-специалисты

Отложено без ROI (roadmap §3).

---

## 7. История

Развёрнутый старый roadmap: [`docs/analysis/_archive/chat-agent-system-roadmap-full-2026-04-26.md`](../analysis/_archive/chat-agent-system-roadmap-full-2026-04-26.md).
