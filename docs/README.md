# Документация SciGraph

Индекс актуальных материалов. Исторические черновики и расширенные рассуждения — в [idea.md](idea.md).

## Продукт и план

| Документ | Описание |
|----------|----------|
| [../README.md](../README.md) | Краткий PRD: пользователи, MVP-сценарии, non-goals |
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
| [architecture/phase-1-backbone.md](architecture/phase-1-backbone.md) | Phase 1: ingestion MVP и стек |
| [architecture/chunking-strategy.md](architecture/chunking-strategy.md) | Task-aware slices, section chunks, dedup |
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
