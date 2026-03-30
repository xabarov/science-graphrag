# ADR 004: Ontology v1 scope (scientific semantic layer)

- **Status**: Accepted
- **Date**: 2026-03-31

## Context

Нужен **закрытый scope** первой итерации научного слоя поверх scholarly backbone ([ADR 002](002-layer1-graph-model.md)), без раздувания типов до появления данных и бенчмарков. Черновик политики: [ontology-v1-mvp.md](../specs/ontology-v1-mvp.md); north-star контекст: [idea.md §семантический слой](../idea.md).

## Decision

### Типы узлов, допускаемые в production в рамках ontology v1 (первая итерация)

| Тип | Роль | Примечание |
|-----|------|------------|
| `Method` | Названная методика / архитектура (в т.ч. семейство детекторов, loss, module) | Извлекается из текста; идентификаторы из реестров позже |
| `Dataset` | Набор данных / бенчмарк, на котором оценивают | Из текста + при необходимости нормализация по имени |
| `ResearchTopic` / `Concept` | Обобщённые темы | **Не вводить в production** в v1 до отдельного ADR + gold |
| `Claim` | Утверждение + evidence | Phase 3+; **не в ontology v1 scope** |

Связи **work ↔ method**, **work ↔ dataset**, **method ↔ dataset** (упоминается в тексте) допускаются как **кандидаты** с обязательными полями `confidence` и ссылкой на provenance (chunk / span / section id), как в [ontology-v1-mvp.md §политика](../specs/ontology-v1-mvp.md).

### Типы рёбер (логические имена; реализация Neo4j — в следующем ADR при появлении кода)

| Отношение | Назначение |
|-----------|------------|
| `Work-[:USES_METHOD]->Method` | работа явно предлагает / применяет метод |
| `Work-[:EVALUATED_ON]->Dataset` | эксперименты на датасете |
| `Method-[:TRAINED_OR_TESTED_ON]->Dataset` | связь из текста между методом и данными |

Направленность можно уточнить при первой имплементации; **обратимые** дубликаты запрещены: одна пара узлов — одно ребро с каноническим направлением.

### Source of Truth (SoT)

| Источник данных | Каноничность | Примеры |
|-----------------|--------------|---------|
| Внешние реестры (OpenAlex, ROR, позже Crossref) | Высокая для уже смэпленных `Work` / `Institution` | DOI, OpenAlex id |
| LLM / rules extraction из текста | Кандидаты с `confidence` | `Method`, `Dataset` names |
| Ручная gold-разметка | Эталон для eval | `tests/fixtures/benchmarks/` |

Политика: **новый тип узла/ребра в production** только вместе с фикстурой, gold и метрикой ([benchmark-expansion-v1.md](../benchmarks/benchmark-expansion-v1.md)).

### Anti-bloat

Расширение таблицы типов выше — только через новый ADR или явное обновление этого ADR со ссылкой на benchmark coverage.

## Consequences

- Контракт извлечения для первого semantic-stage: [semantic-method-dataset-v1.md](../specs/extraction/semantic-method-dataset-v1.md).
- Реализация в коде (Neo4j labels, ingestion stages) выходит **за рамки** этого ADR и следует в отдельных PR.
- [roadmap Phase 2](../roadmap.md): черновик specs дополняется принятым scope; Phase 3 — контракты extraction для `Method`/`Dataset`.

## Ссылки

- [ontology-v1-mvp.md](../specs/ontology-v1-mvp.md)
- [002-layer1-graph-model.md](002-layer1-graph-model.md)
- [benchmark-expansion-v1.md](../benchmarks/benchmark-expansion-v1.md)
