# Контракт: semantic chunks и merge/dedup (Phase 2–3+)

## Назначение

Задать структуру **чанков для retrieval и будущего per-chunk KG extraction**, а также правила **слияния и дедупликации** между чанками.

## DocumentChunk (логическая схема)

Поле | Тип | Правила
-----|-----|--------
`chunk_fingerprint` | str | Стабильный хэш от нормализованного текста + `section_path` + порядковый индекс в секции
`section_path` | str | Breadcrumb заголовков Markdown, например `Introduction / Related work`
`text` | str | Текст чанка; может включать префикс контекста секции
`start_offset` | int | Начало в нормализованном документе (для отладки)
`end_offset` | int | Конец
`overlap_prev` | bool | True если в начале есть хвост предыдущего чанка (overlap)
`overlap_next` | bool | True если чанк продолжится со overlap
`chunk_index` | int | Порядковый номер среди всех чанков документа

Реализация: `science_graphrag.ingestion.chunking.DocumentChunk`.

## Chunk-level dedup (до LLM)

- **Exact:** два чанка с одинаковым `chunk_fingerprint` после нормализации — оставить один экземпляр для embedding.
- **Overlap:** соседние чанки с пересечением по дизайну не схлопываются агрессивно; дубликаты сущностей снимаются на этапе merge.

Функция: `dedupe_chunks_for_embedding` в `chunking.py`.

## Per-chunk extraction (будущее)

Выход экстрактора для каждого чанка должен включать:

- сущности и связи с полем **`source_chunk_fingerprint`** (или список `source_chunk_ids`);
- уверенность / optional span внутри чанка.

## Entity / relationship merge (после чанков)

Порядок:

1. **Детерминированные ключи** по типу сущности (см. `chunk_merge.py`): `Work` → DOI > arXiv > fingerprint title+year; `Author` → нормализованное имя + аффилиации; и т.д.
2. **Слияние списков provenance** — объединять `source_chunk_fingerprints`, не отбрасывать.
3. **Дедуп рёбер:** одна и та же тройка (subject, predicate, object) с разными chunk proofs → одно ребро с агрегированным provenance.

Параллельный merge больших списков (как binary tree в osint-gr) — допустимая реализация позже; контракт данных — в этом документе.

## Optional global pass

Один вызов LLM на весь документ (до 128k) для high-level тем или reconciliation — **опционально**, отдельный флаг pipeline, не часть базового chunk path.
