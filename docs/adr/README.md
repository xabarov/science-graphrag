# Architecture Decision Records (ADR)

Краткие зафиксированные архитектурные и продуктовые решения. Полная каноническая модель данных и SoT появятся в `docs/architecture/` по мере Phase 1–2.

## Формат

- **Status**: Accepted | Proposed | Superseded
- **Context**: зачем решали
- **Decision**: что выбрали
- **Consequences**: последствия и ссылки на документы/код

## Индекс

| ADR | Тема |
|-----|------|
| [000](000-greenfield-strategy.md) | Greenfield + selective reuse; референс osint-gr |
| [001](001-phase1-stack.md) | Стек Phase 1: Python, Neo4j, Postgres, Qdrant, blobs |
| [002](002-layer1-graph-model.md) | Модель графа первого слоя в Neo4j |

Новые ADR нумеровать по порядку (`001-...`, `002-...`); при отмене пометить как Superseded и сослаться на замену.
