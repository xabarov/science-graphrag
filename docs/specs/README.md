# Спецификации

## Layer 1 (Phase 1)

| Документ | Стадия |
|----------|--------|
| [extraction/backbone-metadata.md](extraction/backbone-metadata.md) | Метаданные `Work` |
| [extraction/backbone-authorships.md](extraction/backbone-authorships.md) | Авторы и аффилиации |
| [extraction/backbone-references.md](extraction/backbone-references.md) | Список литературы / `CITES` |
| [extraction/semantic-chunks.md](extraction/semantic-chunks.md) | Чанки retrieval / merge, provenance |
| [extraction/semantic-method-dataset-v1.md](extraction/semantic-method-dataset-v1.md) | Контракт извлечения Method / Dataset (Phase 3, до кода) |

## Phase 2 (семантический слой поверх backbone)

| Документ | Стадия |
|----------|--------|
| [ontology-v1-mvp.md](ontology-v1-mvp.md) | Черновик scope онтологии v1 (anti-bloat policy) |
| [adr/004-ontology-v1-scope.md](../adr/004-ontology-v1-scope.md) | Принятый scope v1: типы, рёбра, Source of Truth |

## Дальше (Phase 3+)

- Реализация стадий и промптов по [extraction/semantic-method-dataset-v1.md](extraction/semantic-method-dataset-v1.md); см. [roadmap Phase 3](../roadmap.md).
- Контракты для frontend Phase 6: [frontend-ui-api-contracts-v1.md](frontend-ui-api-contracts-v1.md).

Черновые идеи промптов — в [idea.md](../idea.md).
