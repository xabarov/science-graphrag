# Source of Truth v1 (Layer 1)

Версия для Phase 1. Обновляется по мере Phase 2+ (семантический слой).

## Принцип

- **Реестры** (OpenAlex, Crossref, ROR, ORCID) — канон там, где есть стабильный внешний id и согласованная запись.
- **Извлечение из PDF** — первичный сигнал для полей и provenance; не единственный источник истины для идентичности `Work`/`Author`.
- **Слияние** — правила из [idea.md §6](../idea.md); реализация в `science_graphrag.ingestion.dedup`.

## Матрица по типам сущностей

| Поле / решение | Источник истины по умолчанию | Примечание |
|----------------|------------------------------|------------|
| `Work.doi`, `Work.openalex_id` | Crossref / OpenAlex | DOI нормализуется; OpenAlex id после lookup |
| `Work.title`, `abstract` | Текст + сверка с OpenAlex при совпадении DOI | Конфликт → лог + приоритет реестра для display |
| `Author.orcid` | ORCID API при наличии | Иначе OpenAlex author id |
| `Institution.ror_id` | ROR / OpenAlex institution | Сырой affiliation остаётся на `Authorship` |
| `Venue` ISSN / OpenAlex source id | OpenAlex `Source` / Crossref | Иначе нормализованное имя |
| `CITES` | Parsed references + разрешение к `Work` | Неразрешённые → stub `Work` с минимальными полями или только рёбра-кандидаты (политика MVP: создаём placeholder Work с `ingestion_confidence` низким) |

## Хранилища

| Хранилище | Что хранит |
|-----------|------------|
| Blobs | `sha256` → файл PDF, `document_id` → `extracted.txt` |
| PostgreSQL | `documents`, `ingestion_runs`, сырой JSON стадий (опционально для отладки) |
| Neo4j | Узлы и рёбра слоя 1 |
| Qdrant | Чанки: `document_id`, `chunk_index`, `text`, vector |

## Логи и воспроизводимость

- Каждый ingest run имеет `run_id`, timestamp, версию зависимостей (из `pyproject` / git при наличии).
- Для embeddings фиксируется **имя модели** в конфиге и в метаданных коллекции Qdrant.
