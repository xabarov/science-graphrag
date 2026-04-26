# Agent chat frontend — verification gaps (next wave)

**Date:** 2026-04-26 (updated same day)  
**Source plan:** `docs/analysis/agent-chat-frontend-ui-plan-2026-04-26.md` §12 (Verification plan)

## Doc status — актуальность

**Автоматизируемая часть волны закрыта:** пункты из списка gaps ниже (п.1–6) реализованы в репозитории; этот файл оставлен как **история решения** и краткий чеклист остатков.

**Всё ещё актуально вручную:** прогон живого SSE против бэкенда (план §12.1 п.3) и сценарии §12.2 — их не заменяют unit/RTL тесты.

### Ручной чеклист §12.1.3 + §12.2 (wave 2026-04-26)

**Подготовка**

- API поднят; для автоматизируемой альтернативы: `AGENT_LIVE_BASE=http://127.0.0.1:8000` (+ опционально `AGENT_LIVE_WORKSPACE_ID`) и `pytest tests/live/test_agent_v2_http_optional.py -v` (см. заголовок файла теста).
- В браузере: workspace с ≥1 работой, режим агента, DevTools → Network включить для `POST /v2/agent/query` с `Accept: text/event-stream`.

**§12.1.3 — порядок и плавность SSE**

- [ ] Сразу после отправки появляется pending-оболочка ассистента, live strip не «прыгает» без событий.
- [ ] События идут в ожидаемом порядке: `intent_classified` → (при маршрутизации) `specialist_selected` → опционально UI-5: `subagent_*` / `answer_synthesis_*` → `tool_*` → `evidence_ready` (если есть citations) → при `thread_id`: `context_compacted` → `final_answer`.
- [ ] Нет заметных layout jumps при появлении typed blocks в конце стрима.
- [ ] Автоскролл вниз при нахождении у низа треда; при скролле вверх не уводит насильно.

**§12.2 — сценарии UX**

1. [ ] Короткий inventory-ответ компактный, rail не шумит.
2. [ ] Quote / passage: виден прогресс поиска (live line), затем блок цитат читаемо.
3. [ ] Длинный multi-step: смена специалистов в rail без перегруза треда.
4. [ ] Warning: деградация / предупреждения не ломают вёрстку, читаемы рядом с ответом.
5. [ ] Второй ход с `thread_id`: после ответа видна ненавязчивая отсылка к session / compaction (`context_compacted` / excerpt), если сервер шлёт.

**Фиксация находок:** завести issue/PR-коммент с шагами воспроизведения; этот файл не дублировать длинными логами.

**Опционально позже (не блокер):** расширить матрицу тестов (например полный `AgentRunHeader` для `running` / `done` / `warning`, отдельные тесты на citations + typed blocks в одном снимке), если понадобится жёсткая регрессия по визуалу.

---

## Covered today (после волны)

| Area | Tests | Notes |
|------|-------|------|
| SSE frame parsing | `ui/src/services/agent/agentStreamParse.test.js` | Без изменений по смыслу |
| Run presentation model | `ui/src/components/work/agentRunViewModel.test.js` | + `shouldShowSubagentRail` |
| `AgentRunHeader` | `ui/src/components/work/AgentRunHeader.test.jsx` | По-прежнему узкий набор чипов |
| `AgentLiveStatus` | `ui/src/components/work/AgentLiveStatus.test.jsx` | Как ранее |
| `AskAnswerPanel` | `ui/src/components/work/AskAnswerPanel.test.jsx` | Rail / degraded / warnings |
| `ChatMessageThread` | `ui/src/components/work/ChatMessageThread.test.jsx` | Pending / live / history / rail |
| `AgentRunInspector` | `ui/src/components/work/AgentRunInspector.test.jsx` | Toggle + region |
| `AgentSpecialistRunStack` | `ui/src/components/work/AgentSpecialistRunStack.test.jsx` | Expand + строки |
| `ChatTypedBlocks` | `ui/src/components/work/ChatTypedBlocks.test.jsx` | Smoke chrome |
| `useAgentStream` | `ui/src/hooks/useAgentStream.test.js` | `renderHook` + `act`, без mock React |
| `useAskSubmit` | `ui/src/components/work/useAskSubmit.test.js` | Успех SSE + cap 80 событий |
| `ingestStripModel` | `ui/src/components/ingestion/ingestStripModel.test.js` | Фазы и pick active stage |
| `WorkspaceContextStrip` (ingest) | `ui/src/pages/WorkspacePage/WorkspaceContextStrip.test.jsx` | Humanized secondary line |
| Composed answer panel | `ui/src/components/work/AskAnswerPanel.test.jsx` | Ответ + typed blocks + citations |
| `AgentLiveStatus` expand | `ui/src/components/work/AgentLiveStatus.test.jsx` | aria + recent lines region |
| `AgentRunHeader` states | `ui/src/components/work/AgentRunHeader.test.jsx` | running/done/warning + degraded/failed |

## Previously identified gaps (закрыто в коде 2026-04-26)

1. **Composed chat UI** — закрыто: `ChatMessageThread.test.jsx` (+ mock `scrollIntoView` в jsdom).
2. **`AskAnswerPanel` matrix** — частично закрыто: rail, degraded, warnings; без отдельного теста «все typed blocks + citations в одном кейсе».
3. **`AgentRunInspector`** — закрыто: `AgentRunInspector.test.jsx`.
4. **Subagent rail** — закрыто: тесты stack + `shouldShowSubagentRail` в view-model и `AskAnswerPanel`.
5. **`useAskSubmit`** — закрыто базово: возврат pack и ошибка; cap 80 событий не вынесен в отдельный тест.
6. **Hook lifecycle** — закрыто: `useAgentStream` на `renderHook`.
7. **Manual-only** — **открыто:** live SSE ordering / smoothness.

## What was implemented (кратко)

- `renderHook` тесты: `useAgentStream`, `useAskSubmit`.
- RTL: `ChatMessageThread`, расширенный `AskAnswerPanel`, `AgentRunInspector`, `AgentSpecialistRunStack`, smoke `ChatTypedBlocks`.
- `shouldShowSubagentRail` в `agentRunViewModel.js`, использование в `AskAnswerPanel.jsx`.
- Единый chrome typed blocks: `QuoteCandidatesBlock`, `RelationTraceBlock`, `IdeaSuggestionsBlock` в `ChatTypedBlocks.jsx`.
