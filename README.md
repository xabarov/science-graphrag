# SciGraph

![Короткое демо интерфейса SciGraph](docs/readme-assets/scigraph3.gif)

SciGraph — локальная GraphRAG-система для работы с научной литературой. Она помогает загрузить свой корпус статей, построить bibliographic/knowledge graph, искать по чанкам и задавать вопросы с привязкой к источникам.

Если коротко: это инструмент для исследователя, которому мало просто хранить PDF. Нужны граф связей, retrieval, evidence-backed ответы и удобный UI поверх собственной коллекции материалов.

## Что умеет

- Загружать `pdf`, `md`, `txt` через CLI и workspace UI.
- Строить work graph и workspace graph поверх извлечённых сущностей, ссылок и claims.
- Давать grounded Q&A с цитатами, чанками и traceability до исходников.
- Поднимать локальный UI для просмотра works, graph, Ask/чат и связанных исследовательских сценариев.
- Запускать benchmark/eval контур для quality gate и сравнения прогонов.

## Быстрый старт

### Что понадобится

- Docker + Docker Compose
- Python 3.11+
- локальный `.venv` в корне репозитория

### 1. Установите зависимости

```bash
cp .env.example .env
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

### 2. Проверьте минимум в `.env`

Для первого запуска обычно достаточно:

- указать `SCIENCE_GRAPHRAG_OPENALEX_MAILTO`;
- оставить дефолтные URL локальных сервисов, если используете compose как есть;
- добавить `SCIENCE_GRAPHRAG_EXTRACTION_LLM_*` и/или `SCIENCE_GRAPHRAG_VL_*`, только если хотите LLM/VL extraction сразу.

Быстрый smoke-check конфига:

```bash
.venv/bin/science-graphrag config-check --no-strict
```

### 3. Поднимите стек

Для знакомства с проектом начните с prod-like режима:

```bash
make prod-up
```

После старта откройте:

- UI: [http://localhost:8787/ui/](http://localhost:8787/ui/)
- API health: [http://localhost:8787/health](http://localhost:8787/health)
- Swagger: [http://localhost:8787/docs](http://localhost:8787/docs)

Если вы планируете разрабатывать проект, используйте dev-режим:

```bash
make dev-up
```

В `dev` backend идёт с `uvicorn --reload`, UI — через Vite HMR. В `prod-like` всё ближе к реальному запуску, но пересборки медленнее.

### 4. Загрузите первый документ

```bash
.venv/bin/science-graphrag ingest path/to/paper.pdf
```

Поддерживаются `pdf`, `md`, `txt`.

### 5. Проверьте, что всё работает

Минимальный сценарий проверки:

1. Открыть `http://localhost:8787/ui/`
2. Проверить `GET /health`
3. Проверить `GET /v1/works`
4. После ingest открыть work в UI или вызвать `POST /v1/query`

## Самые полезные команды

```bash
make help
make prod-up
make prod-down
make prod-logs
make dev-up
make dev-down
make dev-logs
make quality
```

## Если хотите загрузить целый корпус

Для длинного прогона используйте отдельный runbook: [docs/runbooks/ingest-corpus.md](docs/runbooks/ingest-corpus.md).

Базовый пример:

```bash
.venv/bin/science-graphrag ingest-corpus /path/to/corpus \
  --continue-on-error \
  --per-file-timeout-s 900 \
  --progress-file eval/results/ingest-progress.jsonl
```

Перед долгим ingest с LLM лучше прогнать строгую проверку:

```bash
.venv/bin/science-graphrag config-check
```

Если используете embeddings через OpenRouter, полезен preflight:

```bash
.venv/bin/science-graphrag config-check --embeddings-preflight
```

## Что где находится

| Путь | Что внутри |
|------|------------|
| `science_graphrag/` | Python backend, CLI, ingestion, storage, API, agent runtime |
| `ui/` | React/Vite интерфейс |
| `docs/` | документация, runbooks, архитектура, ADR |
| `eval/` | benchmark runners, отчёты и метрики |
| `tests/` | pytest-регрессии |
| `scripts/` | вспомогательные операционные скрипты |

## Куда читать дальше

Если нужен следующий уровень деталей, начинайте отсюда:

- [docs/README.md](docs/README.md) — индекс документации
- [docs/runbooks/deploy.md](docs/runbooks/deploy.md) — запуск и эксплуатация
- [docs/runbooks/ingest-corpus.md](docs/runbooks/ingest-corpus.md) — долгий ingest корпуса
- [docs/architecture/README.md](docs/architecture/README.md) — архитектурный обзор
- [docs/architecture/agent-chat-tools.md](docs/architecture/agent-chat-tools.md) — чат-агент и инструменты
- [docs/benchmarks/benchmark-program-overview.md](docs/benchmarks/benchmark-program-overview.md) — benchmark program
- [docs/roadmap.md](docs/roadmap.md) — roadmap

## Для разработчика

- `make prod-up` — самый простой способ впервые посмотреть систему как пользователь.
- `make dev-up` — основной режим локальной разработки.
- UI идёт через `http://localhost:8787/ui/`, API — через тот же origin на `/v1`.
- Для нестандартного фронтенд-запуска используйте `ui/.env.local`, в первую очередь `VITE_API_BASE_URL`.

Дополнительно:

- chunking engine и Chonkie: [docs/runbooks/chonkie-chunking.md](docs/runbooks/chonkie-chunking.md)
- work graph / reader authorship: [docs/architecture/work-graph-reader-authorship.md](docs/architecture/work-graph-reader-authorship.md)
- eval и benchmarks: [docs/benchmarks/README.md](docs/benchmarks/README.md), [eval/README.md](eval/README.md)

## Лицензия

См. [LICENSE](LICENSE).
