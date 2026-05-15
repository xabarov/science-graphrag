# Архитектура

## Phase 1

| Документ | Описание |
|----------|----------|
| [phase-1-backbone.md](phase-1-backbone.md) | Цель Phase 1, стек, поток данных |
| [chunking-strategy.md](chunking-strategy.md) | Слайсы документа, section-aware chunks, метрики |
| [source-of-truth-v1.md](source-of-truth-v1.md) | Матрица Source of Truth для слоя 1 |
| [frontend-parallel-track-strategy.md](frontend-parallel-track-strategy.md) | Strategy: параллельный запуск frontend до полного закрытия Phase 5 |
| [frontend-phase6-bridge-backlog.md](frontend-phase6-bridge-backlog.md) | Work backlog: frontend shell и backend bridge API |

## Agent chat

**Live planning entrypoints:** [`../analysis/ACTIVE.md`](../analysis/ACTIVE.md), [`../analysis/agent-unified-plan-doing-and-benchmarks-2026-05-08.md`](../analysis/agent-unified-plan-doing-and-benchmarks-2026-05-08.md), [`../analysis/agent-engine-next-horizon-2026-05-13.md`](../analysis/agent-engine-next-horizon-2026-05-13.md). Deep runtime/tools reference: [`../analysis/agent-runtime-tools-context-roadmap-2026-05-04.md`](../analysis/agent-runtime-tools-context-roadmap-2026-05-04.md).

| Документ | Описание |
|----------|----------|
| [agent-runtime-overview-ru.md](agent-runtime-overview-ru.md) | Русскоязычный обзор архитектуры агентного рантайма: режимы, поток одного запроса, целевой `v3` контур |
| [agent-chat-tools.md](agent-chat-tools.md) | Каталог LangChain tools для research chat: runtime modes, что видит модель, карта реализации в коде, планы `tool_search` и compaction |
| [agent-tools-best-practices.md](agent-tools-best-practices.md) | Практики проектирования тулзов, согласованность промптов/схем, аудит бандла (`scripts/prompt_audit`), чеклист перед мержем |

## Graph / works API

| Документ | Описание |
|----------|----------|
| [work-graph-reader-authorship.md](work-graph-reader-authorship.md) | Контракт `view=reader` vs `view=raw` для authorship на `GET /v1/works/{id}/graph`, пайплайн collapse / агрегаторы, ссылки на полный анализ |

## Общее

- Логические диаграммы верхнего уровня: [roadmap §3](../roadmap.md).
- Границы модулей в репозитории: `science_graphrag/` (ingestion, storage, cli), корневые каталоги `graph/`, `retrieval/` … — дорожная карта для следующих фаз.

Верхний уровень уже зафиксирован в [roadmap §3](../roadmap.md).
