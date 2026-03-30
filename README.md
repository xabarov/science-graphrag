# science-graphrag

GraphRAG-система для помощи исследователю при работе с научной литературой: навигация по корпусу, синтез с цитатами и provenance, поиск пробелов и поддержка генерации гипотез — с привязкой утверждений к источникам.

## North star

- Навигация по корпусу и цитированию.
- Синтез знаний из нескольких работ с явными ссылками на источники.
- Поиск противоречий и открытых вопросов (после данных и онтологии).
- Поддержка идей и гипотез как **разложимых** на утверждения и доказательства.

Подробнее: [docs/roadmap.md](docs/roadmap.md) (§1), [docs/idea.md](docs/idea.md).

## Пользователи и MVP (доменно-агностично)

**Пользователь:** исследователь, работающий с подборкой статей в своей области (без фиксации одного узкого домена на этапе MVP).

**Сценарии MVP:**

1. Загрузить корпус работ (PDF / метаданные) и получить связный **scholarly backbone**: работы, авторы, публикация, цитирование, стабильные идентификаторы где возможно.
2. Просматривать граф библиографических связей и метаданные по корпусу.
3. Задавать вопросы по литературе с **grounded** ответом: цитаты, ссылки на работы/фрагменты, trace retrieval (после реализации retrieval-слоя).

**Не в MVP (явные non-goals):**

- «Идеальная» универсальная онтология всей науки.
- Полная автоматическая разрешённость всех entity-resolution кейсов без человека и без итераций.
- Продакшен-мультитенантность, софт для редакций журналов, замена менеджера библиографии «на все случаи».
- Копирование доменного слоя из референсных проектов других предметных областей без перепроектирования.

## Структура репозитория (модули)

| Каталог     | Назначение                                      |
|------------|--------------------------------------------------|
| `ingestion`| Приём документов, нормализация, извлечение, enrichment |
| `graph`    | Модель графа, загрузка в графовое хранилище     |
| `retrieval`| Поиск: lexical / vector, политики контекста      |
| `api`      | HTTP/API и контракты query-time                |
| `ui`       | Клиент: workspace, reader, обзор графа         |
| `eval`     | Бенчмарки, метрики, регрессии                   |
| `science_graphrag/` | Реализация Phase 1: ingestion, storage, CLI |

Детали и фазы: [docs/roadmap.md](docs/roadmap.md).

## Phase 1 (текущая реализация)

Реализован runnable ingestion MVP: пакет `science_graphrag`, локальные **PostgreSQL**, **Neo4j**, **Qdrant**, blobs на диске.

Для PDF pipeline теперь работает как **VL-first**:

- если настроены `SCIENCE_GRAPHRAG_VL_*`, PDF сначала конвертируется в `Markdown` через vision-language model;
- если VL недоступен или не настроен, применяется `pypdf` fallback;
- extraction stages читают именно артефакт `article.md` из `data/artifacts/ingestion/<document_id>/<slug>/article.md`.

```bash
cp .env.example .env   # при необходимости поправьте URL, mailto и SCIENCE_GRAPHRAG_VL_* для VL
docker compose up -d   # Postgres :15432, Neo4j HTTP :17474 / Bolt :17687, Qdrant :16333 (см. docker-compose.yml)
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/science-graphrag ingest path/to/file.pdf
# или .txt с полным текстом статьи
.venv/bin/science-graphrag ingest-corpus path/to/corpus_dir   # рекурсивно .pdf/.md/.txt + аудит дублей Work в Neo4j
```

Архитектура и ADR: [docs/architecture/phase-1-backbone.md](docs/architecture/phase-1-backbone.md), [docs/adr/001-phase1-stack.md](docs/adr/001-phase1-stack.md).

## Документация

- [docs/README.md](docs/README.md) — индекс документации.
- [docs/roadmap.md](docs/roadmap.md) — roadmap и фазы 0–7.
- [docs/idea.md](docs/idea.md) — онтология по слоям, backbone, промпты (черновики).

## Стратегия разработки

**Greenfield + selective reuse:** новый проект; из референсного проекта `osint-gr` (см. [roadmap §2](docs/roadmap.md)) переносим паттерны docs, ADR, бенчмарков и тестовой дисциплины — не доменный код.

Решение зафиксировано в [docs/adr/000-greenfield-strategy.md](docs/adr/000-greenfield-strategy.md).

## Лицензия

См. [LICENSE](LICENSE).
