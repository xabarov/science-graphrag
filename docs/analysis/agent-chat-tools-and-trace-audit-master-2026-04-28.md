# Чат-агент: инструменты, live-аудит и Phoenix — мастер-документ (2026-04-28)

**Назначение:** единая точка входа по теме *research chat tools*, *OD live E2E*, *Phoenix trace audit* и *план фаз A–D / remediation P0–P3*. Заменяет удалённые файлы `agent-chat-tools-work-plan-2026-04-28.md`, `agent-heavy-live-trace-audit-and-remediation-2026-04-28.md`, `chat-agent-roadmap-trace-audit-2026-04-27.md` (их содержание суммаризовано здесь).

**Канон по архитектуре API тулов:** [`docs/architecture/agent-chat-tools.md`](../architecture/agent-chat-tools.md), [`docs/architecture/agent-tools-best-practices.md`](../architecture/agent-tools-best-practices.md), [`docs/specs/agent-chat-v1.md`](../specs/agent-chat-v1.md).

**Slim-roadmap агента (multi-turn, UI, не дублируется здесь):** [`agent-runtime-tools-context-roadmap-2026-05-04.md`](./agent-runtime-tools-context-roadmap-2026-05-04.md).

---

## 1. Два harness'а (не путать)

| Harness | CLI / скрипт | Воркспейс | Назначение |
|---------|--------------|-----------|------------|
| **Roadmap eval** | `science-graphrag-chat-agent-roadmap` → [`eval/chat_agent/roadmap_runner.py`](../../eval/chat_agent/roadmap_runner.py) | **`ws-pilot-od`** (фикстуры) | Метрики кейсов, `trace_audit.json`, опционально `--fetch-phoenix`; pre-flight `workspace_audit` (Neo4j+Qdrant). |
| **OD live E2E** | [`scripts/live_check/agent_od_workspace_e2e_audit.py`](../../scripts/live_check/agent_od_workspace_e2e_audit.py) | Подстрока имени (напр. **Object Detection**), ≥ N работ | Жёсткий гейт: последний каталожный тул = `final_answer`, длина ответа, опционально Phoenix REST + `trace_audit` эвристики. |

Корреляция Phoenix ↔ API: в обоих путях важен **`PHOENIX_TRACE_SCOPE`** — для **agent**-спанов нужен `full` (roadmap harness при live подменяет scope на время процесса). Для OD см. [`docker-compose.dev.yml`](../../docker-compose.dev.yml) `PHOENIX_COLLECTOR_ENDPOINT` на API.

---

## 2. Сделано (сводно)

### 2.1 Фаза плана A (корректность и граф)

| Пункт | Статус | Коротко где в коде / доках |
|-------|--------|------------------------------|
| **A1** `final_answer` + бюджет | **Done** | Бюджет после тулов: [`react_edges.py`](../../science_graphrag/agent/graph/react_edges.py); промпт: [`research_chat_system.py`](../../science_graphrag/agent/prompts/research_chat_system.py); предупреждение `agent_finished_without_final_answer_tool`: [`chat_envelope.py`](../../science_graphrag/agent/chat_envelope.py). **P0:** `final_answer_nudge` + graph salvage в [`runtime.py`](../../science_graphrag/agent/runtime.py), политика [`final_answer_policy.py`](../../science_graphrag/agent/final_answer_policy.py). |
| **A2** типы рёбер | **Done** | Тул `workspace_graph_reltypes`, подсказки [`work_graph_schema.py`](../../science_graphrag/agent/tools/work_graph_schema.py), `edge_search` docstring, live streak `edge_search_zero_row_max_streak` в E2E. |
| **A3** `paper_profile` / null | **Частично** | Payload: `metadata_completeness`, `venue_resolution`, промпт «не выдумывать null»; **данные** ingest/OpenAlex — отдельные измерения на OD. |

### 2.2 Фазы B–C–D (частично закрыто волной A/B/C + P1–P3)

- **B:** `cypher_safety` (word-boundary и др.), позитивные примеры в docstring `cypher_query`, тесты; полный «guided template tool» — **не обязателен** (остаток backlog).
- **C1:** shortlist + `tool_search` / манифест / эвристика `heuristic_answer_class` для evidence — **done** (см. P1.2 в истории).
- **C2:** compaction / CH4-CH5 — в продукте есть слой; отдельный бэклог по токенам — в slim roadmap.
- **C3:** E2E скрипт расширен (`--suite full|heavy`, `--trace-audit`, Markdown, Phoenix trace-scoped spans); **обязательный CI на live** — **отложено** (секреты/стенд).
- **D:** частично через промпты и UI i18n; матрица «когда какой retrieval» — можно ужать в одном экране промпта (инкремент).

### 2.3 Remediation P0–P3 (live + Phoenix)

| Трек | Статус | Суть |
|------|--------|------|
| **P0** | **Shipped** | Nudge `final_answer`, salvage после `cypher_query`/`edge_search`, envelope + SSE, разрыв цикла импорта [`graph/__init__.py`](../../science_graphrag/agent/graph/__init__.py). |
| **P1** | **Done** | Обязательные пути инструментов в system prompt; shortlist/цитаты; heavy-verify (см. артефакты `live-heavy-p1-verify-*`). |
| **P2** | **Done** | `extract_span_names_for_trace` в [`phoenix_export.py`](../../eval/chat_agent/phoenix_export.py); E2E без «плоского» сбора чужих спанов; дока *Agent vs ingest*: [`observability-phoenix.md`](../architecture/observability-phoenix.md). |
| **P3** | **Done** | `graph_only` / `text_only` — только `warnings`, без `product_markers`; spec в `agent-chat-v1.md`. |

### 2.4 Верификация «не хуже» (после закрытия работ)

- **Full suite (6 кейсов), Phoenix ON:** [`eval/results/live-full-verify-2026-04-28.md`](../../eval/results/live-full-verify-2026-04-28.md), лог/jsonl рядом. Итог: **6/6 PASS** строгого гейта; ранее падавшие **`graph_ego_methods`** и **`multi_evidence_speed_accuracy`** стабильно с **`final_answer`** (и `paper_quote_search` там, где нужен сценарий).

---

## 3. Исторический срез (до P0–P3, для контекста)

Первый **heavy** прогон (3 сложных OD-кейса) дал **1/3 PASS**: пустой ответ после `cypher_query` без `final_answer`, и ответ без тулa `final_answer` при длинном тексте. Корневые причины: маршрут `chat → END` без нуджа и извлечение ответа в [`extract_langgraph_answer`](../../science_graphrag/agent/runtime.py). После P0–P3 и full-verify картина **исправлена** на эталонном стенде; отдельный класс флаков — **`agent_turn_deadline_exceeded`** при нехватке wall-clock (см. [`scripts/live_check/README.md`](../../scripts/live_check/README.md)).

---

## 4. Команды оператора (копипаст)

**OD live (рекомендуется для регрессии heavy/full):**

```bash
AGENT_LIVE_BASE=http://127.0.0.1:18787 \
PHOENIX_UI_BASE_URL=http://127.0.0.1:16006 \
.venv/bin/python scripts/live_check/agent_od_workspace_e2e_audit.py \
  --suite full --trace-audit --timeout 600 \
  --markdown-report eval/results/live-full-verify-$(date -u +%Y%m%d).md \
  --write-report eval/results/live-full-verify.jsonl
```

Опции: `--suite default|heavy|full`, `--skip-phoenix`, `AGENT_E2E_PHOENIX_SPAN_CAP`, [`run_agent_od_phases_audit.sh`](../../scripts/live_check/run_agent_od_phases_audit.sh) (bundle evaluate + full).

**Roadmap harness (ws-pilot-od):**

```bash
science-graphrag-chat-agent-roadmap \
  --fixtures tests/fixtures/benchmarks/chat_agent_roadmap \
  --out eval/results/chat-agent-roadmap-live-$(date -u +%Y%m%d)
```

Перед live: `scripts/chat_agent_workspace_readiness_audit.py` или встроенный audit runner; при `blocked` — `scripts/seed_benchmark_workspaces.py`.

**Phoenix checklist (ручной смотр UI после прогона):**

1. `phoenix_trace_id` в ответе = trace в UI проекта `science-graphrag` (или `PHOENIX_PROJECT_NAME`).
2. Имена `tool.*` / `llm.agent.*` согласованы с `tool_trace` (допускаются оговорённые пробелы до полного TOOL/RETRIEVER parity — см. [`phoenix-tracing-coverage-2026-04-25.md`](./phoenix-tracing-coverage-2026-04-25.md)).
3. Для chat-audit не использовать **`PHOENIX_TRACE_SCOPE=extraction_llm`** без понимания (ингест «съедает» agent spans).

**Автоматический snapshot Phoenix из harness:** флаг `--fetch-phoenix` в roadmap runner; результат best-effort между версиями Phoenix.

---

## 5. Наблюдения на будущее

1. **`no_quote_found`** на OD при живых прогонах часто **не провал гейта**, а сигнал тонкого корпуса / merge цитат — дебажить через `paper_quote_search` payload `empty_reason` и envelope.
2. **`graph_only`** на чисто графовых сценариях — **ожидаемый маркер** смеси доказательств (вектор не вызывался); не путать с ошибкой API.
3. **Эвристика `duplicate_tool_calls_in_trace`** в [`agent_trace_audit.py`](../../science_graphrag/agent/agent_trace_audit.py): для сценариев «две семьи детекторов» / два `find_works` — **часто ложнопозитив**; интерпретировать с контекстом вопроса.
4. **`langgraph_supervisor_v1`:** нудж/salvage только у **`langgraph_research_v1`**; при жалобах на writer-only завершение — отдельный мини-план (writer-side `final_answer` или возврат к tool-специалисту).
5. **Таймауты:** `graph_ego_methods` чувствителен к `SCIENCE_GRAPHRAG_AGENT_STEP_TIMEOUT_SECONDS` и `AGENT_LIVE_TIMEOUT_SEC` — при флаке сначала поднять лимиты, потом искать баг.
6. **Roadmap `relation_cites`:** при `strict_answer_class: false` возможен writer-dominated ответ без graph — для nightly рассмотреть strict-tier (исторически зафиксировано в старых прогонах harness).

---

## 6. Оставшаяся работа (backlog)

| ID | Тема | Приоритет | Примечание |
|----|------|-----------|------------|
| **B1** | Guided Cypher / шаблоны / расширение примеров | Средний | Heavy `graph_ego`: метрика «≤1 ошибочный cypher»; опционально `cypher_query_template`. |
| **B2** | Fan-out / дедуп аргументов в state | Средний | Промпт уже ограничивает повторный `paper_profile` на тот же `work_id`; жёсткий dedup — связь с CH4. |
| **B3** | `paper_quote_search` vs `idea_search` пороги / `no_quote_found` rate | Средний | Измерения на фиксированном OD-наборе. |
| **C1** | Дальнейшее снижение токенов бандла | По мере боли | `--json` в `build_research_chat_prompt_bundle.py`. |
| **C2** | Капсулы / multi-turn стоимость | Roadmap L0–L4 | См. slim chat-agent roadmap. |
| **C3** | Nightly CI `AGENT_LIVE_BASE` | Процесс | `continue-on-error` или выделенный стенд. |
| **D1–D4** | GOST edge cases, короткая матрица тулов в промпте, Phoenix UI polish | Низкий | |
| **Supervisor v1** | Контракт `final_answer` | Отложено | §5 п.4. |

---

## 7. Ключевые пути кода

| Область | Путь |
|---------|------|
| ReAct single-agent граф | [`supervisor.py`](../../science_graphrag/agent/graph/supervisor.py) `_build_single_agent_graph` |
| Маршруты chat/tools | [`react_edges.py`](../../science_graphrag/agent/graph/react_edges.py) |
| Извлечение ответа + salvage | [`runtime.py`](../../science_graphrag/agent/runtime.py) `extract_langgraph_answer`, `_salvage_answer_from_last_graph_tool` |
| Политика нуджа | [`final_answer_policy.py`](../../science_graphrag/agent/final_answer_policy.py) |
| Envelope | [`chat_envelope.py`](../../science_graphrag/agent/chat_envelope.py) |
| API v2 sync/SSE | [`agent_v2.py`](../../science_graphrag/api/agent_v2.py) |
| Эвристики live-аудита | [`agent_trace_audit.py`](../../science_graphrag/agent/agent_trace_audit.py) |
| Phoenix HTTP | [`phoenix_export.py`](../../eval/chat_agent/phoenix_export.py) |
| Live harness | [`agent_od_workspace_e2e_audit.py`](../../scripts/live_check/agent_od_workspace_e2e_audit.py) |

---

## 8. Связанные документы (вне объединения)

- Phoenix wave / X2: [`phoenix-tracing-coverage-2026-04-25.md`](./phoenix-tracing-coverage-2026-04-25.md)  
- OD proving ground (восстановление воркспейсов): [`chat-agent-od-workspace-restoration-and-eval-plan-2026-04-27.md`](./chat-agent-od-workspace-restoration-and-eval-plan-2026-04-27.md) (ссылки на harness ведут сюда).  
- Master roadmap: [`master-roadmap-and-refactor-plan-2026-04-25.md`](./master-roadmap-and-refactor-plan-2026-04-25.md)  
- Eval index: [`eval/README.md`](../../eval/README.md)

---

## 9. Changelog документа

| Дата | Изменение |
|------|-----------|
| 2026-04-28 | **Создан мастер-документ:** объединены `agent-chat-tools-work-plan-2026-04-28`, `agent-heavy-live-trace-audit-and-remediation-2026-04-28`, `chat-agent-roadmap-trace-audit-2026-04-27`; три исходных файла удалены. |
| (ист.) | История правок перенесена по смыслу из удалённых файлов: план фаз A–D, P0–P3, post-closure full verify 6/6, roadmap baseline X2. |
