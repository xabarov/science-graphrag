# SciGraph

**Локальный research cockpit для вашей научной библиотеки:** загрузка корпуса, граф связей, поиск по смыслу и ответы с опорой на конкретные места в документах — без обязательного «чата в облаке вместо источников».

![Короткое демо интерфейса SciGraph](docs/readme-assets/scigraph3.gif)

---

## Для кого

Для исследователя или R&D-команды, которым **недостаточно папки с PDF**. Нужен обзор корпуса, навигация по цитированию и смысловым связям, а не разовый промпт к модели без трассировки.

## Что вы получите после установки

- **Корпус становится навигируемым** — работы, чанки, граф, workspace и поиск по вашим данным.
- **Вопросы к литературе — с evidence** — ответы можно проверить по источникам и фрагментам текста.
- **Стек поднимается локально** — Docker Compose, привычный цикл «поднял → открыл UI → загрузил PDF».

## Быстрый старт

### Вариант 1. Просто поднять UI и стек

Если вы хотите сначала просто посмотреть систему, достаточно **Docker + Docker Compose** и файла `.env`:

```bash
cp .env.example .env
docker compose -f docker-compose.yml up -d --build
```

Если у вас есть `make`, это эквивалентно:

```bash
make prod-up
```

Дальше откройте **[веб-интерфейс](http://localhost:8787/ui/)** — главная точка входа. Для быстрой проверки API: [`/health`](http://localhost:8787/health), интерактивная документация: [`/docs`](http://localhost:8787/docs).

### Вариант 2. Полный setup для CLI, ingest и локальной разработки

Если вы хотите не только поднять UI, но и запускать `science-graphrag` с хоста, делать ingest и пользоваться локальным CLI, нужны ещё **Python 3.11+** и `.venv`:

```bash
cp .env.example .env
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/science-graphrag config-check --no-strict
```

В `.env` задайте **`SCIENCE_GRAPHRAG_OPENALEX_MAILTO`** — это не секрет, а ваш contact email для OpenAlex metadata enrichment. Для нормальной практической работы также обычно нужны **`SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY`** и **`SCIENCE_GRAPHRAG_VL_API_KEY`**: без них стек поднимется, но extraction и качество обработки PDF будут заметно ограничены.

Для prod-like режима:

```bash
docker compose -f docker-compose.yml up -d --build
```

Для локальной разработки удобнее dev-режим:

```bash
docker compose -f docker-compose.dev.yml up -d --build
```

Если у вас есть `make`, это те же команды через `make prod-up` и `make dev-up`.

## Один файл — быстрый «ощутимый» результат

```bash
.venv/bin/science-graphrag ingest path/to/paper.pdf
```

Форматы: **`pdf`**, **`md`**, **`txt`**. Этот шаг требует полного setup из варианта 2. После ingest откройте работу в UI или дерните API — см. Swagger на `/docs`.

## Корпус целиком

Долгие прогоны, таймауты, resume и operational чек-листы — **[docs/runbooks/ingest-corpus.md](docs/runbooks/ingest-corpus.md)**. Перед тяжёлым ingest с LLM разумно прогнать **строгую** проверку:

```bash
.venv/bin/science-graphrag config-check
```

Для embeddings через OpenRouter: **`.venv/bin/science-graphrag config-check --embeddings-preflight`**.

## Документация

| Задача | Документ |
|--------|----------|
| Индекс всей документации | [docs/README.md](docs/README.md) |
| Запуск стека, порты, compose | [docs/runbooks/deploy.md](docs/runbooks/deploy.md) |
| Архитектура | [docs/architecture/README.md](docs/architecture/README.md) |
| Чат-агент и инструменты | [docs/architecture/agent-chat-tools.md](docs/architecture/agent-chat-tools.md) |
| Бенчмарки и eval | [docs/benchmarks/README.md](docs/benchmarks/README.md) · [eval/README.md](eval/README.md) |
| Roadmap | [docs/roadmap.md](docs/roadmap.md) |

**Исходники:** `science_graphrag/` (backend, CLI, ingestion), `ui/` (интерфейс), `eval/` и `tests/` — качество и регрессии.

Полезные команды: `make help`, `make prod-down`, `make dev-down`, `make prod-logs` / `make dev-logs`, `make quality`.

## Лицензия

См. [LICENSE](LICENSE).
