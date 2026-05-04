# Спецификации

## Layer 1 (Phase 1)

| Документ | Стадия |
|----------|--------|
| [extraction/backbone-metadata.md](extraction/backbone-metadata.md) | Метаданные `Work` |
| [extraction/backbone-authorships.md](extraction/backbone-authorships.md) | Авторы и аффилиации |
| [extraction/backbone-references.md](extraction/backbone-references.md) | Список литературы / `CITES` |
| [extraction/semantic-chunks.md](extraction/semantic-chunks.md) | Чанки retrieval / merge, provenance |
| [extraction/semantic-method-dataset-v1.md](extraction/semantic-method-dataset-v1.md) | Контракт Method / Dataset + измеримый exit criteria, fingerprints в `run_metadata` |

## Phase 2 (семантический слой поверх backbone)

| Документ | Стадия |
|----------|--------|
| [ontology-v1-mvp.md](ontology-v1-mvp.md) | Черновик scope онтологии v1 (anti-bloat policy) |
| [adr/004-ontology-v1-scope.md](../adr/004-ontology-v1-scope.md) | Принятый scope v1: типы, рёбра, Source of Truth |

## Дальше (Phase 3+)

- Реализация стадий и промптов по [extraction/semantic-method-dataset-v1.md](extraction/semantic-method-dataset-v1.md); см. [roadmap Phase 3](../roadmap.md).
- Контракты для frontend Phase 6 и **mandatory API happy-path**: [frontend-ui-api-contracts-v1.md](frontend-ui-api-contracts-v1.md).

Черновые идеи промптов — в [idea.md](../idea.md).

## Ingest / workspace upload

| Документ | Стадия |
|----------|--------|
| [ingest-job-progress-api.md](ingest-job-progress-api.md) | Canonical `progress_pct`, `ingest_phase`, SSE `stage_progress` |

## Agent / Chat

| Документ | Стадия |
|----------|--------|
| [agent-chat-v1.md](agent-chat-v1.md) | `POST /v2/agent/query` — envelope + SSE vocabulary (волны CH* в спеке — метки поставки, не отдельные продукты) |
| [Анализ: slim roadmap](../analysis/agent-runtime-tools-context-roadmap-2026-05-04.md) | Продуктовый канон: упрощённый LangGraph-чат; **rule-based `tool_search` v1** в коде (`science_graphrag/agent/tool_search.py`); compaction / session memory — по roadmap; [полный архив](../analysis/_archive/chat-agent-system-roadmap-full-2026-04-26.md) |
