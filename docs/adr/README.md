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
| [008](008-ontology-claims-wave-h.md) | Wave H1: epistemic / claims ontology (gated); см. Wave O для production extractor |
| [009](009-author-institution-merge-catalog.md) | Каталог merge авторов / институций |
| [010](010-work-dedup-review-queue.md) | Очередь review дедупликации работ |
| [011](011-graph-live-ux-and-payload.md) | Live graph UX: enriched `/graph` payload, inspector panel, defaults (force + canvas) |
| [012](012-workspace-graph-projection.md) | Wave J: workspace graph projection, depth, GDS fallback |
| [013](013-concept-research-topic-ontology-v1-5.md) | Wave N: Concept / ResearchTopic ontology v1.5 (gold-first, no production graph) |
| [014](014-work-dedup-smart-wave-l.md) | Wave L: smart dedup (work/author embeddings, LLM judge, Postgres queue) |
| [015](015-neo4j-vector-index-work-title-embedding.md) | Wave Q2 (optional): Neo4j vector index `Work.title_embedding` for in-graph similarity |
| [016](016-agent-tool-registry-and-langgraph.md) | Wave R: read-only agent tool registry, LangGraph runtime, `/v1/agent/query` |
| [017](017-hypothesis-idea-assist-advisory.md) | Wave S: hypothesis/idea-assist advisory layer, rubric benchmark, no production graph writes |
| [018](018-ingest-worker-redis.md) | Ingest worker / Redis queue |
| [019](019-entity-dedup-pipeline.md) | Entity dedup Qdrant collections (methods, datasets, venues, institutions) |
| [020](020-langgraph-supervisor-multiagent.md) | LangGraph supervisor multi-agent |
| [021](021-openrouter-bge-m3-embeddings.md) | OpenRouter `baai/bge-m3` as canonical remote embeddings (Qdrant + dedup) |
| [022](022-reader-extracted-body-vs-qdrant-chunks.md) | Reader: canonical ingest artifacts for full text; Qdrant chunks for retrieval only |
| [023](023-method-ontology-v2-rich-description-and-canonicalization.md) | Method v2: rich description, MethodEvidence, ingest canonicalization, graph merge |
| [024](024-artifact-promotion-and-retention-phase4.md) | Phase 4: object retention tags, promotion to reviewable JSON, evidence export / GC |
| [025](025-llm-distributed-quota-redis.md) | Phase 5: optional Redis-backed global LLM concurrency quota across workers |
| [026](026-otlp-logs-defer.md) | OTLP log export: defer; use JSON stderr + optional Prometheus first |

Новые ADR нумеровать по порядку (`001-...`, `002-...`); при отмене пометить как Superseded и сослаться на замену.
