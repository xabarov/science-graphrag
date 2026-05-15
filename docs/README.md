# Документация SciGraph

Индекс материалов по ролям: **active** (читать в первую очередь), **reference** (справочники и контракты), **historical** (архив, черновики, не default для LLM).

**LLM / Cursor:** дефолтный вход для планов в `docs/analysis/` — [analysis/ACTIVE.md](analysis/ACTIVE.md). Сводка последних правок навигации: [CHANGELOG-docs.md](CHANGELOG-docs.md). Зоны, исключённые из типового индекса контекста (см. корневой `.cursorignore`): `docs/analysis/_archive/`, `docs/analysis/_snippets/`, `docs/idea.md`, `docs/pilot/`, тяжёлые артефакты под `eval/results/diagnostics/` и `eval/results/multimodel/`.

## Active entrypoints (начать здесь)

| Документ | Описание |
|----------|----------|
| [../README.md](../README.md) | Краткий PRD: пользователи, MVP-сценарии, non-goals |
| [roadmap.md](roadmap.md) | Roadmap фаз 0–7, архитектура верхнего уровня, риски |
| [analysis/ACTIVE.md](analysis/ACTIVE.md) | Короткий порядок чтения для агента: unified plan, horizon, feature matrix, benchmarks, backlog |
| [analysis/README.md](analysis/README.md) | Hub `docs/analysis/`: таблицы «куда смотреть», политика контекста, индекс файлов |
| [runbooks/deploy.md](runbooks/deploy.md) | Docker Compose, политика ранней упаковки сервисов |
| [runbooks/benchmark-decision-gate.md](runbooks/benchmark-decision-gate.md) | GO / CONDITIONAL-GO / NO-GO |
| [adr/README.md](adr/README.md) | Индекс ADR |
| [specs/README.md](specs/README.md) | Индекс контрактов извлечения и API |

## Reference (справочники и операции)

| Документ | Описание |
|----------|----------|
| [runbooks/benchmark-driven-dev-loop.md](runbooks/benchmark-driven-dev-loop.md) | Короткий benchmark-цикл (CLI, compare, UI `/benchmark`) |
| [runbooks/roadmap-next-waves.md](runbooks/roadmap-next-waves.md) | Волны Wave A–H и I–L |
| [runbooks/user-journeys-retrieval-v1.md](runbooks/user-journeys-retrieval-v1.md) | Сценарии Phase 5: corpus → query → evidence |
| [runbooks/benchmark-program-status.md](runbooks/benchmark-program-status.md) | Сводка семейств бенчмарков: core vs advisory |
| [runbooks/benchmark-pilot-advisory-runs.md](runbooks/benchmark-pilot-advisory-runs.md) | Чеклист advisory: live retrieval + claims + aggregate |
| [runbooks/pilot-checklist.md](runbooks/pilot-checklist.md) | Phase 7: pilot package, KPI, GO/NO-GO |
| [benchmarks/README.md](benchmarks/README.md) | Индекс бенчмарков и eval |
| [architecture/README.md](architecture/README.md) | Индекс архитектурных заметок |
| [backlog/refactor-backend.md](backlog/refactor-backend.md), [backlog/refactor-frontend.md](backlog/refactor-frontend.md) | Структурный долг `[OPEN]` |

## Historical / archive (не default для LLM)

| Документ / зона | Описание |
|-----------------|----------|
| [idea.md](idea.md) | Расширенные черновики онтологии и промптов |
| [analysis/_archive/](analysis/_archive/) | Завершённые волны, полные тексты закрытых планов |
| [analysis/_snippets/](analysis/_snippets/) | Промпт-дампы, JSON-сэмплы |
| [pilot/README.md](pilot/README.md) | Архивная зона pilot-заметок (часто только индекс) |
| [analysis/_archive/workspace-experience-gap-2026-04-24.md](analysis/_archive/workspace-experience-gap-2026-04-24.md) | [HISTORICAL] Wave I–L; активное продолжение — [workspace-ux-redesign-2026-04-25.md](analysis/workspace-ux-redesign-2026-04-25.md) |

---

## Продукт и план (детальная таблица)

Расширенный каталог; верхние секции **Active entrypoints** / **Reference** задают приоритет чтения.

| Документ | Описание |
|----------|----------|
| [../README.md](../README.md) | Краткий PRD: пользователи, MVP-сценарии, non-goals |
| [analysis/README.md](analysis/README.md) | **Hub планирования:** недельные указатели (BT/trust, backlog, snapshot), индекс всех `docs/analysis/*.md`, закрытые планы |
| [roadmap.md](roadmap.md) | Roadmap фаз 0–7, архитектура верхнего уровня, риски |
| [runbooks/benchmark-driven-dev-loop.md](runbooks/benchmark-driven-dev-loop.md) | Короткий benchmark-цикл (CLI, compare, UI `/benchmark`) |
| [runbooks/roadmap-next-waves.md](runbooks/roadmap-next-waves.md) | Волны Wave A–H (benchmark gate → pilot → CI/retrieval/UI/ontology) и I–L (workspace UX + smart dedup) |
| [analysis/_archive/workspace-experience-gap-2026-04-24.md](analysis/_archive/workspace-experience-gap-2026-04-24.md) | [HISTORICAL] Глубокий анализ workspace UX и dedup (Wave I–L закрыты); карта переиспользования паттернов из `osint-gr`. Активное продолжение — [analysis/workspace-ux-redesign-2026-04-25.md](analysis/workspace-ux-redesign-2026-04-25.md). |
| [runbooks/user-journeys-retrieval-v1.md](runbooks/user-journeys-retrieval-v1.md) | Сценарии Phase 5: corpus → query → evidence |
| [runbooks/benchmark-decision-gate.md](runbooks/benchmark-decision-gate.md) | GO / NO-GO, gate перед Wave B–D |
| [runbooks/benchmark-program-status.md](runbooks/benchmark-program-status.md) | Сводка семейств бенчмарков: core vs advisory, Wave H gate |
| [runbooks/benchmark-pilot-advisory-runs.md](runbooks/benchmark-pilot-advisory-runs.md) | Чеклист advisory: live retrieval + claims + aggregate |
| [runbooks/pilot-checklist.md](runbooks/pilot-checklist.md) | Phase 7: pilot package, KPI, GO/NO-GO |
| [runbooks/deploy.md](runbooks/deploy.md) | Docker Compose, политика ранней упаковки сервисов |
| [idea.md](idea.md) | Онтология по слоям, scholarly backbone, промпты (черновик) |

## Архитектура

| Документ | Описание |
|----------|----------|
| [architecture/README.md](architecture/README.md) | Индекс архитектурных заметок |
| [architecture/agent-runtime-overview-ru.md](architecture/agent-runtime-overview-ru.md) | Наглядный обзор архитектуры агентного рантайма: текущие режимы, поток запроса, куда движется `v3` |
| [architecture/agent-chat-tools.md](architecture/agent-chat-tools.md) | Чат-агент: каталог тулов, схемы для LLM, карта кода, планы (`tool_search`, compaction) |
| [architecture/phase-1-backbone.md](architecture/phase-1-backbone.md) | Phase 1: ingestion MVP и стек |
| [architecture/chunking-strategy.md](architecture/chunking-strategy.md) | Task-aware slices, section chunks, dedup |
| [runbooks/chonkie-chunking.md](runbooks/chonkie-chunking.md) | Chonkie vs legacy chunking: baseline, A/B retrieval, rollout (`SCIENCE_GRAPHRAG_CHUNKING_ENGINE`) |
| [architecture/source-of-truth-v1.md](architecture/source-of-truth-v1.md) | Source of Truth слоя 1 |
| [architecture/frontend-parallel-track-strategy.md](architecture/frontend-parallel-track-strategy.md) | Стратегия параллельного frontend-трека (Phase 5/6 bridge) |
| [architecture/frontend-phase6-bridge-backlog.md](architecture/frontend-phase6-bridge-backlog.md) | Backlog: frontend shell + backend bridge endpoints |

## ADR (Architecture Decision Records)

| Документ | Описание |
|----------|----------|
| [adr/README.md](adr/README.md) | Процесс и индекс решений |
| [adr/000-greenfield-strategy.md](adr/000-greenfield-strategy.md) | Greenfield + selective reuse от osint-gr |
| [adr/001-phase1-stack.md](adr/001-phase1-stack.md) | Стек Phase 1 |
| [adr/002-layer1-graph-model.md](adr/002-layer1-graph-model.md) | Модель Neo4j слоя 1 |
| [adr/003-chunking-and-dedup-strategy.md](adr/003-chunking-and-dedup-strategy.md) | Chunking, slices, dedup, pin моделей |

## Спецификации и eval

| Документ | Описание |
|----------|----------|
| [specs/README.md](specs/README.md) | Индекс контрактов извлечения |
| [specs/extraction/](specs/extraction/) | Layer 1: metadata, authorships, references; semantic chunks |
| [specs/frontend-ui-api-contracts-v1.md](specs/frontend-ui-api-contracts-v1.md) | Минимальные UI-facing API контракты для Phase 6 MVP |
| [benchmarks/README.md](benchmarks/README.md) | Индекс бенчмарков и eval |
| [benchmarks/strategy-v1.md](benchmarks/strategy-v1.md) | Стратегия eval v1 (layer 1+) |
| [benchmarks/graph-level-eval-v1.md](benchmarks/graph-level-eval-v1.md) | План graph-level eval после ingest |
| [benchmarks/benchmark-expansion-v1.md](benchmarks/benchmark-expansion-v1.md) | Расширение корпуса и families |
| [benchmarks/retrieval-eval-v1.md](benchmarks/retrieval-eval-v1.md) | Заготовка retrieval/citation benchmark family |
| [benchmarks/teacher-gold-audit-v1.md](benchmarks/teacher-gold-audit-v1.md) | Процедура аудита teacher-gold фикстур |
| [specs/ui-empty-loading-audit-v1.md](specs/ui-empty-loading-audit-v1.md) | Чеклист empty/loading/error по UI |
| [specs/ontology-wave-h-backlog.md](specs/ontology-wave-h-backlog.md) | Backlog онтологии Wave H (Claims, merge) |

## Открытые вопросы

| Документ | Описание |
|----------|----------|
| [questions/phase-0-open-questions.md](questions/phase-0-open-questions.md) | Отложенные решения, не блокирующие Phase 0 |

## Референс (вне репозитория)

Паттерны документации и процессов: проект `osint-gr` — см. [roadmap §4](roadmap.md).
