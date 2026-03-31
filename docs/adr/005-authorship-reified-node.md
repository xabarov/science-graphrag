# ADR 005: Узел `Authorship` vs свойства на ребре `Work–Author`

- **Status**: Accepted
- **Date**: 2026-03-31

## Context

В Neo4j видна цепочка `Work → Authorship → Author`; на узле `Authorship` отображаются порядок и аффилиация. Возникает вопрос: не перенести ли порядок и прочие поля в **свойства одного ребра** `(:Work)-[:AUTHORED_BY]->(:Author)` и убрать промежуточный узел.

## Decision

**Сохраняем reified узел `:Authorship`** между `Work` и `Author`, как в [ADR 002](002-layer1-graph-model.md) и [idea.md §2.6](../idea.md).

Реализация записи: [`Neo4jGraphStore._write_work_tx`](../../science_graphrag/storage/neo4j_store.py) (`HAS_AUTHORSHIP` / `OF_AUTHOR` / опционально `AFFILIATED_WITH`).

## Criteria (когда узел оправдан vs когда достаточно ребра)

| Критерий | Узел `Authorship` | Только ребро с свойствами |
|----------|-------------------|---------------------------|
| Порядок автора, raw affiliation, confidence на **эту** работу | Свойства на участии; один `Author` — много разных участий | То же на ребре `AUTHORED_BY` |
| Связь **участие → Institution** без смешения с «глобальной» аффилиацией автора | Естественно: `Authorship → Institution` | Требует второго ребра/ключа или усложнения модели |
| Несколько институтов на одного автора в одной статье | Расширяемо отдельными рёбрами от одного `Authorship` | Сложнее без дополнительной сущности |
| Идемпотентность и дедуп по месту в списке | Стабильный `id` вида `{work_id}:ash:{position}` | Зависит от семантики `MERGE` на ребре |
| Визуальная простота в Neo4j Browser | Больше узлов на графе | Меньше узлов; см. [authorship-neo4j-queries.md](../architecture/authorship-neo4j-queries.md) — это **UX**, не обязанность менять схему |

## Consequences

- Новые publication-scoped поля (например `is_corresponding`, `email` из `AuthorshipDraft`) по умолчанию добавляются на `:Authorship`, а не на `:Author`.
- Если когда-либо понадобится альтернативная проекция «только `Work–Author`» для аналитики или экспорта, её можно строить **запросом или материализованным view** без обязательной миграции базовой онтологии.
- Отмена этого решения потребует ADR Superseded + миграцию данных и правок `neo4j_store.py`.

## Links

- [authorship-neo4j-queries.md](../architecture/authorship-neo4j-queries.md) — сравнение Cypher и разделение онтологии / визуализации
- [ADR 002](002-layer1-graph-model.md) — метки и типы рёбер слоя 1
