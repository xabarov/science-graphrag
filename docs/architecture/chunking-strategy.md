# Стратегия chunking и дедупликации (scholarly GraphRAG)

## Цель

После PDF → Markdown ingestion должен опираться на **task-aware slicing** и **section-aware chunks**, а не на единый character-splitter. Это улучшает извлечение сущностей, provenance и идемпотентность векторного индекса.

Связанные документы: [ADR 003](../adr/003-chunking-and-dedup-strategy.md), [spec semantic-chunks](../specs/extraction/semantic-chunks.md).

## Три представления одного документа

| Режим | Назначение | Источник текста |
|-------|------------|-----------------|
| `front_matter_slice` | Метаданные `Work`, авторы, аффилиации | Начало статьи до Introduction (с cap по символам) |
| `references_scope` | Библиография, рёбра `CITES` | Секции References/Bibliography или хвост документа |
| `semantic_body_chunks` | Retrieval (Qdrant), будущее семантическое извлечение | Тело с разбиением по заголовкам Markdown и лимиту токенов |

## Модели (pin)

- **PDF → Markdown (VL):** `qwen/qwen3-vl-235b-a22b-instruct` — переменная `SCIENCE_GRAPHRAG_VL_MODEL`.
- **Structured extraction (Layer 1 LLM):** `mistralai/mistral-small-3.2-24b-instruct` — `SCIENCE_GRAPHRAG_EXTRACTION_LLM_MODEL`.

Контекст **128k** у текстовой модели не отменяет chunking для основного извлечения: длинный единый prompt хуже по гранулярности provenance и подвержен деградации на длинных контекстах; опциональный full-document pass — только для reconciliation/summary (Phase 3+).

## Chunking для retrieval

- Ориентир размера: **~800–1600** условных токенов, старт **~1200**, overlap **~100–160** (или ~10–15%) **внутри одной секции** по заголовку.
- Условная оценка токенов без отдельного tokenizer: `len(text) // 4` (эвристика для англ. научного текста).
- Идентификатор чанка в Qdrant: детерминированный UUID5 от `document_id` и `chunk_fingerprint` (хэш текста + путь секции + индекс), чтобы повторный ingest не плодил дубликаты.

## Дедупликация

1. **До embedding:** exact dedup по `chunk_fingerprint` (см. `dedupe_chunks_for_embedding` в коде).
2. **После per-chunk extraction (будущий семантический слой):** merge по детерминированным ключам (DOI, title+year, нормализованные имена) + агрегация provenance (`source_chunk_ids`); см. `science_graphrag/ingestion/llm/chunk_merge.py`.

## Метрики (eval)

- Доля дубликатов чанков до/после dedup.
- Recall references при bibliography не в конце документа.
- Стабильность `chunk_id` при повторном ingest одного и того же `article.md`.
