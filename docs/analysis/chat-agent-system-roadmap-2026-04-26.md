# Agent chat system roadmap — 2026-04-26 (living, **slim**)

**Статус (2026-04-27):** продукт **остаётся на упрощённой архитектуре**: один LangGraph run (`supervisor` → `retrieval_agent` / `graph_agent` → `writer_agent`), `POST /v2/agent/query` (JSON + SSE), `thread_id` + digest/session memory, `tool_trace`, UI «run chrome» (`AgentRunHeader`, `AgentLiveStatus`, rail, inspector).  
**Этот файл** — короткий канон: цели, текущее состояние, **что откладываем**, и **два трека будущего**, которые мы явно не выбрасываем: **tool_search** и **суммаризация / компактация контекстного окна**.

**Полная историческая версия** (детальные CH-волны, шесть отдельных specialist subgraphs, длинная taxonomy) перенесена в архив, чтобы не путать читателя с текущим курсом: [`_archive/chat-agent-system-roadmap-full-2026-04-26.md`](./_archive/chat-agent-system-roadmap-full-2026-04-26.md).

**Companion (UI):** [`agent-chat-frontend-ui-plan-2026-04-26.md`](./agent-chat-frontend-ui-plan-2026-04-26.md) · **Rollout / флаги:** [`agent-chat-prod-rollout-2026-04-27.md`](./agent-chat-prod-rollout-2026-04-27.md) · **Eval + Phoenix + live E2E:** [`agent-chat-tools-and-trace-audit-master-2026-04-28.md`](./agent-chat-tools-and-trace-audit-master-2026-04-28.md) · **OD proving ground:** [`chat-agent-od-workspace-restoration-and-eval-plan-2026-04-27.md`](./chat-agent-od-workspace-restoration-and-eval-plan-2026-04-27.md).

---

## 1. Product north star (без изменений по смыслу)

Исследовательский ассистент по **workspace** и статьям: scope понятен, ответы с доказательствами (цитаты, граф, каталог), длинный диалог **без** взрыва контекста, режимы ответа различимы (`answer_class`), поведение **наблюдаемо** (SSE, trace, evals).  
Оркестрация остаётся **agent-friendly**, инструменты — **domain-shaped** (не один «универсальный поиск»).

---

## 2. Текущая архитектура (канон репозитория)

| Слой | Реализация |
|------|------------|
| API | `science_graphrag/api/agent_v2.py` — sync + SSE, `product_step` / synthesis / compaction события для UI |
| Граф | `supervisor`, `retrieval_agent`, `graph_agent`, `writer_agent`; state в `agent/graph/state.py` |
| Инструменты | Расширенный paper/workspace/graph набор **внутри** тех же нод (не отдельные долгоживущие «специалисты-сабграфы») |
| Политика хода | `TurnPolicy` / classifier (`Settings` + env, см. prod rollout doc) |
| Клиент | `useAgentStream`, `ChatMessageThread`, `AskAnswerPanel`, `agentRunViewModel` — live + final, без второго параллельного «консольного» чата |

Инфраструктура **tool_search (rule-based v1)** и **session / compaction** уже задействованы там, где это описано в коде и спеке `docs/specs/agent-chat-v1.md`; дальнейшее усиление — см. §4.

---

## 3. Что сознательно не планируем как ближайший большой шаг

Следующее **не** является текущим обязательством по продукту (детали и история — в архивном файле):

- Вынос **шести именованных specialist** в отдельные LangGraph subgraphs «ради архитектуры» без узкого ROI.
- Полная **LLM-based tool_search** до появления устойчивых eval/gate (rule-based shortlist остаётся базой).
- Расширение UI в отдельную «вторую консоль событий» вне треда.

При необходимости точечного улучшения (например, graph-only кейсы) правки остаются **инкрементальными** в существующих нодах и tool registry.

---

## 4. Будущие треки, которые **оставляем** в дорожной карте

### 4.1 Tool search и отложенная загрузка схем

**Проблема:** полный prompt со всеми JSON-схемами инструментов дорогой и нестабильный при росте каталога (catalog, graph, quotes, bibliography, внешние интеграции).

**Паттерн (сохраняем как цель):**

1. Координатор по умолчанию видит **короткий каталог** (имена + one-line + теги).
2. Отдельный **`tool_search(query, answer_class, scope, …)`** возвращает shortlist и при необходимости **полные schema refs** для выбранных инструментов.

**Минимальный контракт:** на первых порах допустим **rule/tag-based** shortlist (без LLM); fallback при пустом/широком shortlist — консервативный baseline (каталог + retrieval).  
Артефакты в коде: machine-readable manifest + модуль поиска (см. архив §7 для расширенного текста и acceptance).

### 4.2 Суммаризация и компактация контекстного окна

**Проблема:** длинная история, повтор evidence, многократные ссылки на одни и те же работы — без политики сжатия диалог либо дорогой, либо теряет контекст.

**Уровни (сохраняем как продуктовую модель):**

| Уровень | Назначение |
|---------|------------|
| L0 | Нормализованный evidence pack turn (воспроизводимость / eval), не «сжатие» само по себе |
| L1 | **Turn digest** — краткая структурированная сводка завершённого хода |
| L2 | **Rolling session memory** — компактная память нескольких ходов |
| L3 | **Капсулы** workspace / paper / entity / topic — ленивые переиспользуемые артефакты |
| L4 | **Full compact boundary** — явная граница для очень длинных тредов; сырой audit trail не в каждом prompt |

**Операционная политика:** кто инициирует compact (координатор / side summarizer), триггеры (после meaningful turn, по token threshold, lazy capsules). Детали формулировок и persistence — в архивном §8; реализация уже частично пересекается с `context_compacted`, `session_summary`, `run_metadata.compaction` в API/UI.

---

## 5. Наблюдаемость, evals, доверие

Кратко (без дублирования чеклистов):

- **Многослойные тесты:** unit/view-model/API parity (`tests/test_api_agent_v2_stream_parity.py`), roadmap harness + live E2E — см. [`agent-chat-tools-and-trace-audit-master-2026-04-28.md`](./agent-chat-tools-and-trace-audit-master-2026-04-28.md), опционально live `tests/live/` при `AGENT_LIVE_BASE`.
- **Phoenix:** корреляция `phoenix_trace_id` ↔ `tool_trace`; закрытие span gaps — см. [`phoenix-tracing-coverage-2026-04-25.md`](./phoenix-tracing-coverage-2026-04-25.md) и trace-audit doc.

---

## 6. Ключевые продуктовые решения (сжато)

- Thread-aware контракт на бэкенде (`thread_id`, digest, server session store) — канон.  
- Tool registry **domain-shaped**; **tool_search обязателен при дальнейшем раздувании** набора tools (§4.1).  
- **Многоуровневая компактация** — обязательна для зрелого long-form research chat (§4.2).  
- Raw Cypher — **guarded / advanced**, не основной UX для большинства вопросов.  
- Coordinator / `TurnPolicy` — стабильный seam; hybrid LLM classifier — поэтапно и под eval, не keyword-зоопарк (см. prod rollout).

---

## 7. Горячие точки кода

**Backend:** `api/agent_v2.py`, `agent/graph/state.py`, `agent/graph/supervisor.py`, `agent/graph/nodes/{retrieval_agent,graph_agent,writer_agent}.py`, `agent/tools/`, `agent/llm/chat.py`, `agent/runtime.py`.  
**Frontend:** `ui/src/components/work/ChatMessageThread.jsx`, `AskAnswerPanel.jsx`, `agentRunViewModel.js`, `useAgentStream.js`, `ChatComposer.jsx`.  
**Eval:** `eval/chat_agent/`, `tests/agent/`, `tests/eval/`.

---

## 8. Практический next step

Инкременты в рамках §2: улучшение маршрутизации и tool-coverage в существующих нодах, полировка SSE/UI, eval/Phoenix gaps.  
Крупные темы §4 (усиление tool_search, richer compaction/capsules) — отдельные инициативы с явным scope и метриками, без обязательного «multi-agent rewrite».
