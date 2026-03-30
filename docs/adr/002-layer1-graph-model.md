# ADR 002: Layer 1 graph model (Neo4j)

- **Status**: Accepted
- **Date**: 2026-03-30

## Context

Нужна однозначная проекция scholarly backbone из [idea.md §2–5](../idea.md) в Neo4j.

## Decision

### Метки узлов

| Label | Ключевые свойства |
|-------|-------------------|
| `Work` | `id`, `doi`, `openalex_id`, `title`, `normalized_title`, `publication_year`, `abstract`, `work_type`, `ingestion_confidence` |
| `Authorship` | `id`, `author_position`, `raw_affiliation`, `extraction_confidence` |
| `Author` | `id`, `full_name`, `normalized_name`, `orcid`, `openalex_author_id` |
| `Institution` | `id`, `name`, `ror_id`, `country` |
| `Venue` | `id`, `name`, `issn`, `openalex_source_id` |

`id` — внутренний UUID строки, стабильный в рамках базы.

### Типы рёбер

| Тип | From → To |
|-----|-----------|
| `HAS_AUTHORSHIP` | Work → Authorship |
| `OF_AUTHOR` | Authorship → Author |
| `AFFILIATED_WITH` | Authorship → Institution |
| `PUBLISHED_IN` | Work → Venue |
| `CITES` | Work → Work |
| `RELATED_VERSION_OF` | Work → Work (symmetric пара; храним одно ребро + `relation_subtype` опционально) |

### Индексы

- Уникальный индекс на `Work(doi)` где doi не null.
- Уникальный индекс на `Work(openalex_id)` где не null.
- Индекс на `Author(orcid)` где не null.

## Consequences

- Dedup обязан обновлять существующие узлы, а не плодить дубликаты при совпадении DOI/OpenAlex id.
- `RELATED_VERSION_OF` на Phase 1 может быть пустым, если нет сигналов preprint/journal.

## Links

- [source-of-truth-v1.md](../architecture/source-of-truth-v1.md)
