# Ontology v1 — MVP (черновик Phase 2)

Цель: зафиксировать **минимальный** научный слой поверх уже реализованного scholarly backbone ([adr/002-layer1-graph-model.md](../adr/002-layer1-graph-model.md)), без раздувания типов до появления benchmark-покрытия ([roadmap Phase 2](../roadmap.md)).

## Уже есть (backbone, не дублировать)

- `Work`, `Author`, `Institution`, `Venue`, `Authorship`, `CITES`, `PUBLISHED_IN`, версионные связи `RELATED_VERSION_OF` при обогащении.

## Кандидаты в v1 ontopic (после ADR и gold)

| Сущность | Назначение | Статус |
|----------|------------|--------|
| `ResearchTopic` / `Concept` | Тема или концепт из текста | **MVP candidate:** [ADR 013](../adr/013-concept-research-topic-ontology-v1-5.md) (Accepted) + advisory harness [semantic-concept-topic-v1.md](extraction/semantic-concept-topic-v1.md); production Neo4j — после отдельного promotion (см. roadmap Wave N→O) |
| `Method` | Названная методика / архитектура модели | В scope [ADR 004](../adr/004-ontology-v1-scope.md); **в production** |
| `Dataset` | Набор данных, на котором оценивают | В scope ADR 004; **в production** |
| `Claim` / `Evidence` | Проверяемое утверждение + опора на чанк | **MVP candidate:** [ADR 008](../adr/008-ontology-claims-wave-h.md), [ontology-claims-v1.md](ontology-claims-v1.md); production за флагом `SCIENCE_GRAPHRAG_CLAIMS_EXTRACTION_ENABLED` (Wave O) |

## Политика расширения

1. Новый тип узла или отношения в **production** — только вместе с фикстурой, gold и метрикой (см. [benchmarks/strategy-v1.md](../benchmarks/strategy-v1.md)).
2. Ссылки между работой и сущностями v1 — всегда с `confidence` и источником (чанк / span / реестр).
3. Противоречия с [idea.md](../idea.md) разрешаются ADR, не правкой «втихую».

## Следующий шаг

- Реализация в Neo4j / ingestion по принятому [ADR 004: ontology v1 scope](../adr/004-ontology-v1-scope.md); контракт извлечения: [extraction/semantic-method-dataset-v1.md](extraction/semantic-method-dataset-v1.md).
