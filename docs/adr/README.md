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
| [003](003-chunking-and-dedup-strategy.md) | Task-aware chunking, dedup между чанками, модели VL/LLM |
| [004](004-ontology-v1-scope.md) | Scope ontology v1: Method, Dataset; SoT; anti-bloat |
| [005](005-authorship-reified-node.md) | Узел `Authorship` vs свойства на ребре `Work–Author`; критерии выбора |
| [006](006-graph-layout-stack-spike.md) | Wave 4.3: spike силового/layout-стека (React Flow/Sigma vs порт osint simulation) |
| [007](007-canvas-force-layout-port.md) | Canvas: Circle vs Force (порт силовой симуляции osint-gr без OSINT-домена) |
| [011](011-graph-live-ux-and-payload.md) | Live graph UX: enriched `/graph` payload, inspector panel, defaults (force + canvas) |
| [012](012-workspace-graph-projection.md) | Wave J: workspace graph projection, depth, GDS fallback |
| [013](013-concept-research-topic-ontology-v1-5.md) | Wave N: Concept / ResearchTopic ontology v1.5 (gold-first, no production graph) |

Новые ADR нумеровать по порядку (`001-...`, `002-...`); при отмене пометить как Superseded и сослаться на замену.
