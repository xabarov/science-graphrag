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

## За ~5 минут до UI

Нужны **Docker + Docker Compose** и **Python 3.11+**.

```bash
cp .env.example .env
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

В `.env` обязательно задайте **`SCIENCE_GRAPHRAG_OPENALEX_MAILTO`**. Ключи **`SCIENCE_GRAPHRAG_EXTRACTION_LLM_*`** / **`SCIENCE_GRAPHRAG_VL_*`** — только если хотите сразу полноценный LLM/VL extraction (иначе можно начать с «оболочки» и конфигурации по умолчанию).

```bash
.venv/bin/science-graphrag config-check --no-strict
make prod-up
```

Дальше откройте **[веб-интерфейс](http://localhost:8787/ui/)** — главная точка входа. Для проверки API: [`/health`](http://localhost:8787/health), интерактивная документация: [`/docs`](http://localhost:8787/docs).

**Пишете код под проект?** Вместо `make prod-up` используйте **`make dev-up`** (backend с reload, UI через Vite HMR).

## Один файл — быстрый «ощутимый» результат

```bash
.venv/bin/science-graphrag ingest path/to/paper.pdf
```

Форматы: **`pdf`**, **`md`**, **`txt`**. После ingest откройте работу в UI или дерните API — см. Swagger на `/docs`.

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
