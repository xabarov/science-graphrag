# ADR 003: Task-aware chunking и дедупликация между чанками

**Status:** Accepted  
**Date:** 2026-03-30

## Context

Phase 1 ingestion использовал нормализованный полный текст для LLM-стадий и грубый character-based `chunk_text()` для Qdrant. Для scholarly GraphRAG и моделей с большим контекстом нужно:

- не смешивать front matter и bibliography в одни промпты без нужды;
- резать Markdown по структуре (заголовки, абзацы);
- уметь сливать дубликаты сущностей из перекрывающихся чанков;
- закрепить выбранные VL/LLM модели в конфиге и `.env.example`.

## Decision

1. Ввести **document slices**: `front_matter_slice`, `references_scope` (модуль `science_graphrag/ingestion/document_slices.py`).
2. Layer 1 extraction (metadata, authorships, references) получает **явные тексты слайсов**, а не только усечённый полный документ.
3. Векторный индекс строится из **section-aware chunks** с полями provenance и **детерминированным** `chunk_fingerprint` / point id (`science_graphrag/ingestion/chunking.py`).
4. Контракты для будущего семантического merge: `science_graphrag/ingestion/llm/chunk_merge.py` + [spec semantic-chunks](../specs/extraction/semantic-chunks.md).
5. Пин моделей по умолчанию: VL `qwen/qwen3-vl-235b-a22b-instruct`, extraction `mistralai/mistral-small-3.2-24b-instruct`.

## Consequences

- Зависимость от качества Markdown после PDF (заголовки `##` улучшают chunking).
- `QdrantChunkStore` принимает расширенный payload (`section_path`, `chunk_fingerprint`, …).
- Тесты на slicer/chunker/dedup обязательны для регрессий.
- Полный документ в один вызов LLM для entity extraction остаётся **вне** базового пути до отдельного ADR/флага.

## References

- [architecture/chunking-strategy.md](../architecture/chunking-strategy.md)
- [specs/extraction/semantic-chunks.md](../specs/extraction/semantic-chunks.md)
- Референс паттернов: osint-gr `ExtractionService` + `KGDeduplicator` (binary merge) — концептуально, без копирования онтологии.
