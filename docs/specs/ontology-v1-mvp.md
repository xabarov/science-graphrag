# Ontology v1 — MVP (черновик Phase 2)

Цель: зафиксировать **минимальный** научный слой поверх уже реализованного scholarly backbone ([adr/002-layer1-graph-model.md](../adr/002-layer1-graph-model.md)), без раздувания типов до появления benchmark-покрытия ([roadmap Phase 2](../roadmap.md)).

## Уже есть (backbone, не дублировать)

- `Work`, `Author`, `Institution`, `Venue`, `Authorship`, `CITES`, `PUBLISHED_IN`, версионные связи `RELATED_VERSION_OF` при обогащении.

## Кандидаты в v1 ontopic (после ADR и gold)

| Сущность | Назначение | Статус |
|----------|------------|--------|
| `ResearchTopic` / `Concept` | Тема или концепт из текста | Не в коде; только идеи в [idea.md](../idea.md) |
| `Method` | Названная методика / архитектура модели | В scope [ADR 004](../adr/004-ontology-v1-scope.md); не в коде |
| `Dataset` | Набор данных, на котором оценивают | В scope ADR 004; не в коде |
| `Claim` | Проверяемое утверждение + опора на фрагмент | Phase 3+ (извлечение + provenance) |

## Политика расширения

1. Новый тип узла или отношения в **production** — только вместе с фикстурой, gold и метрикой (см. [benchmarks/strategy-v1.md](../benchmarks/strategy-v1.md)).
2. Ссылки между работой и сущностями v1 — всегда с `confidence` и источником (чанк / span / реестр).
3. Противоречия с [idea.md](../idea.md) разрешаются ADR, не правкой «втихую».

## Следующий шаг

- Реализация в Neo4j / ingestion по принятому [ADR 004: ontology v1 scope](../adr/004-ontology-v1-scope.md); контракт извлечения: [extraction/semantic-method-dataset-v1.md](extraction/semantic-method-dataset-v1.md).
