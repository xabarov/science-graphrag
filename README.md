# SciGraph

SciGraph — scholarly GraphRAG-система для работы с научной литературой: ingest корпуса, библиографический граф, retrieval по чанкам, grounded Q&A с цитатами и traceability до источников.

Проект ориентирован на исследователя, который работает с собственной подборкой статей и хочет не просто хранить PDF, а получать навигацию по корпусу, обзор связей, evidence-backed ответы и основу для дальнейшего semantic/ontology слоя.

## Что доступно сейчас

- Ingestion pipeline для `pdf` / `md` / `txt` через CLI `science-graphrag`.
- Локальный стек на `PostgreSQL`, `Neo4j`, `Qdrant`, `Redis`, `Phoenix`.
- API и UI для workspace, reader, graph, chat/evidence сценариев.
- VL-first PDF pipeline: при настроенных `SCIENCE_GRAPHRAG_VL_*` PDF сначала превращается в Markdown, иначе используется `pypdf` fallback.
- Бенчмарки и регрессионные suite для ingestion, graph, retrieval, claims и agent scenarios.

Подробнее про продуктовый контекст: [docs/roadmap.md](docs/roadmap.md), [docs/idea.md](docs/idea.md).

## Быстрые ссылки

- [docs/README.md](docs/README.md) - индекс документации.
- [docs/architecture/README.md](docs/architecture/README.md) - архитектурный обзор.
- [docs/runbooks/deploy.md](docs/runbooks/deploy.md) - запуск стека и operational notes.
- [docs/runbooks/ingest-corpus.md](docs/runbooks/ingest-corpus.md) - corpus ingest, timeout, resume, troubleshooting.
- [docs/roadmap.md](docs/roadmap.md) - roadmap и фазы проекта.
- [docs/adr/README.md](docs/adr/README.md) - каталог архитектурных решений.
- [docs/benchmarks/README.md](docs/benchmarks/README.md) - benchmark/eval documentation.

## Быстрый старт

### Prerequisites

- Docker + Docker Compose
- Python 3.11+
- Локальный `.venv` в корне репозитория

### 1. Подготовьте окружение

```bash
cp .env.example .env
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

Минимум перед первым запуском:

- проверьте `SCIENCE_GRAPHRAG_OPENALEX_MAILTO`;
- если у вас нестандартные локальные порты или внешние сервисы, поправьте `SCIENCE_GRAPHRAG_DATABASE_URL`, `SCIENCE_GRAPHRAG_NEO4J_URI`, `SCIENCE_GRAPHRAG_QDRANT_URL`, `SCIENCE_GRAPHRAG_REDIS_URL`;
- если хотите LLM/VL extraction, задайте `SCIENCE_GRAPHRAG_EXTRACTION_LLM_*` и/или `SCIENCE_GRAPHRAG_VL_*`, либо совместимые `MAIN_LLM_*`.

Быстрая диагностика конфига:

```bash
.venv/bin/science-graphrag config-check --no-strict
```

Перед долгим ingest с LLM лучше использовать строгую проверку:

```bash
.venv/bin/science-graphrag config-check
```

### 2. Поднимите локальный стек

Есть два режима запуска.

#### Prod-like stack

Использует [`docker-compose.yml`](docker-compose.yml): backend и frontend идут из собранных образов, изменения в коде требуют пересборки.

```bash
make prod-up
```

Эквивалент без `make`:

```bash
docker compose -f docker-compose.yml up -d --build
```

Точки входа:

- UI: [http://localhost:8787/ui/](http://localhost:8787/ui/)
- API health: [http://localhost:8787/health](http://localhost:8787/health)
- API напрямую, минуя nginx: [http://localhost:18787/health](http://localhost:18787/health)
- Neo4j browser: [http://localhost:17474](http://localhost:17474)
- Qdrant: [http://localhost:16333](http://localhost:16333)
- Phoenix UI: [http://localhost:16006](http://localhost:16006)

#### Dev stack

Использует [`docker-compose.dev.yml`](docker-compose.dev.yml): backend работает через `uvicorn --reload`, UI — через Vite dev server с HMR, вход остаётся тем же через nginx.

```bash
make dev-up
```

**Чем prod-like отличается от dev:** в prod-like образы собираются из Dockerfile и UI отдаётся как статический build за nginx; в dev репозиторий смонтирован в контейнер API/worker, а UI проксируется с Vite (быстрее итерации, больше движущихся частей).

Полезные команды:

```bash
make help
make prod-up
make prod-down
make dev-up
make dev-down
make dev-logs
make dev-recreate-api
make dev-ui-restart
```

## Настройка окружения

Полный список и комментарии находятся в [.env.example](.env.example). Для быстрого старта удобнее думать о переменных по группам.

| Группа | Что обычно нужно сделать |
|--------|---------------------------|
| Обязательно проверить | `SCIENCE_GRAPHRAG_OPENALEX_MAILTO`, storage/connectivity переменные, путь к blobs/artifacts при нестандартном окружении |
| Часто нужно для реальной работы | `SCIENCE_GRAPHRAG_EXTRACTION_LLM_*`, `SCIENCE_GRAPHRAG_VL_*`, либо fallback `MAIN_LLM_*` |
| Опционально | embeddings channel, Phoenix, agent runtime, claims extraction, chunking engine |
| Только для UI | `ui/.env.local`, прежде всего `VITE_API_BASE_URL` если UI открыт не через тот же origin |

### Storage и connectivity

Эти переменные определяют, куда CLI и локальные процессы ходят за данными:

- `SCIENCE_GRAPHRAG_DATABASE_URL`
- `SCIENCE_GRAPHRAG_NEO4J_URI`
- `SCIENCE_GRAPHRAG_QDRANT_URL`
- `SCIENCE_GRAPHRAG_REDIS_URL`
- `SCIENCE_GRAPHRAG_BLOB_ROOT`
- `SCIENCE_GRAPHRAG_ARTIFACT_ROOT`

По умолчанию `.env.example` настроен под локальный compose-стек с host-портами `15432`, `17687`, `16333`, `16379`.

### LLM и VL

Для extraction и PDF-to-Markdown доступны два слоя настроек:

- префиксные переменные проекта: `SCIENCE_GRAPHRAG_EXTRACTION_LLM_*`, `SCIENCE_GRAPHRAG_VL_*`;
- совместимые fallback-переменные: `MAIN_LLM_API_KEY`, `MAIN_LLM_BASE_URL`, `MAIN_LLM_MODEL`, `API_KEY`.

Ключевые сценарии:

- `SCIENCE_GRAPHRAG_VL_*` - vision-language конвертация PDF в Markdown;
- `SCIENCE_GRAPHRAG_EXTRACTION_LLM_*` - metadata/references/claims extraction;
- `MAIN_LLM_*` - совместимый fallback, если префиксные переменные не заданы.

Реальные merge-правила и fallback-логика описаны в [science_graphrag/config.py](science_graphrag/config.py).

### UI-конфиг

Для фронтенда используйте `ui/.env.local`, а не корневой `.env`.

Чаще всего нужны:

- `VITE_API_BASE_URL` - если UI обращается не к тому же origin, где доступен `/v1`;
- `VITE_CLAIMS_UI_ENABLED` - включает Claims panel;
- `VITE_SYNC_ASK_SESSIONS` - включает default-on sync для Ask sessions.

## Основные рабочие сценарии

### Ingest одного документа

```bash
.venv/bin/science-graphrag ingest path/to/paper.pdf
```

Поддерживаются `pdf`, `md`, `txt`.

### Ingest корпуса

Для долгого corpus-wide прогона используйте runbook: [docs/runbooks/ingest-corpus.md](docs/runbooks/ingest-corpus.md).

Базовый пример:

```bash
.venv/bin/science-graphrag ingest-corpus /path/to/corpus \
  --continue-on-error \
  --per-file-timeout-s 900 \
  --progress-file eval/results/ingest-progress.jsonl
```

Если ingest был прерван, можно продолжить с `--resume`. Для cutover эмбеддингов и recovery отдельных документов см. соответствующие материалы в [`docs/runbooks/`](docs/runbooks/) и команду `ingest-resume-embed`.

### Проверка API/UI после старта

После поднятия стека удобно проверить:

1. `GET /health`
2. `GET /v1/works`
3. UI по адресу `http://localhost:8787/ui/`

Дополнительно:

- `GET /docs` - FastAPI docs
- `GET /v1/works/{work_id}`
- `GET /v1/works/{work_id}/chunks`
- `POST /v1/query`

### Benchmarks и eval

Основные benchmark entrypoints регистрируются через `pyproject.toml`, например:

- `science-graphrag-layer1-benchmark`
- `science-graphrag-graph-benchmark`
- `science-graphrag-retrieval-benchmark`
- `science-graphrag-claims-benchmark`
- `science-graphrag-agent-benchmark`

Практический обзор и режимы запуска: [eval/README.md](eval/README.md), [docs/benchmarks/README.md](docs/benchmarks/README.md).

## Обзор репозитория

| Путь | Назначение |
|------|------------|
| `science_graphrag/` | Основной Python-пакет: ingestion, storage, API, worker, agent runtime, CLI |
| `ui/` | Vite + React UI: workspace, reader, graph, chat, admin surfaces |
| `docs/` | Индекс документации, операционные заметки в `docs/runbooks/`, архитектура, ADR, specs, benchmarks |
| `eval/` | Benchmark runners, metrics, reports |
| `tests/` | Pytest и fixture-based regression coverage |
| `scripts/` | Вспомогательные операционные и аналитические скрипты |
| `data/` | Локальные blobs, artifacts, compose volumes и runtime outputs |

## Навигация по документации

### Обзор системы

- [docs/README.md](docs/README.md)
- [docs/roadmap.md](docs/roadmap.md)
- [docs/idea.md](docs/idea.md)

### Архитектура

- [docs/architecture/README.md](docs/architecture/README.md)
- [docs/architecture/phase-1-backbone.md](docs/architecture/phase-1-backbone.md)
- [docs/architecture/chunking-strategy.md](docs/architecture/chunking-strategy.md)
- [docs/adr/README.md](docs/adr/README.md)
- [docs/adr/001-phase1-stack.md](docs/adr/001-phase1-stack.md)

### Запуск и эксплуатация

- [docs/runbooks/deploy.md](docs/runbooks/deploy.md)
- [docs/runbooks/ingest-corpus.md](docs/runbooks/ingest-corpus.md)
- [docs/runbooks/chonkie-chunking.md](docs/runbooks/chonkie-chunking.md)
- [docs/runbooks/user-journeys-retrieval-v1.md](docs/runbooks/user-journeys-retrieval-v1.md)
- [docs/runbooks/phase0-bge-m3-qdrant-cutover.md](docs/runbooks/phase0-bge-m3-qdrant-cutover.md)

### Eval и benchmarks

- [eval/README.md](eval/README.md)
- [docs/benchmarks/README.md](docs/benchmarks/README.md)
- [docs/runbooks/benchmark-driven-dev-loop.md](docs/runbooks/benchmark-driven-dev-loop.md)
- [docs/runbooks/benchmark-decision-gate.md](docs/runbooks/benchmark-decision-gate.md)

## Стратегия разработки

Проект следует стратегии greenfield + selective reuse: паттерны docs, ADR, eval discipline и часть операционных подходов переиспользуются из референсных проектов, но доменная модель и архитектурные решения фиксируются отдельно внутри SciGraph.

Подробности: [docs/adr/000-greenfield-strategy.md](docs/adr/000-greenfield-strategy.md).

## Как проверить, что quickstart достаточен

Если по одному только этому файлу можно ответить на вопросы ниже, README выполняет роль входной страницы.

1. Как поднять локальный стек? — раздел **Быстрый старт**, `make prod-up` / `make dev-up`.
2. Какие переменные править в первую очередь? — раздел **Настройка окружения** и ссылка на [.env.example](.env.example).
3. Чем prod-like отличается от dev? — подсказка под **Dev stack**.
4. Где UI, где API, где runbook по ingest? — **Точки входа** после старта, [docs/runbooks/ingest-corpus.md](docs/runbooks/ingest-corpus.md).
5. Где архитектурный обзор и roadmap? — **Навигация по документации** и [docs/roadmap.md](docs/roadmap.md).

Проверка ссылок в этом файле (локальные пути из markdown) выполняется скриптом из корня репозитория:

```bash
.venv/bin/python - <<'PY'
from pathlib import Path
import re
root = Path(".")
text = (root / "README.md").read_text(encoding="utf-8")
links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)
missing = [
    t
    for t in links
    if not (t.startswith("http://") or t.startswith("https://") or t.startswith("#"))
    and not (root / t).exists()
]
print("missing", missing)
PY
```

Ожидаемый результат: `missing []`.

## Лицензия

См. [LICENSE](LICENSE).
