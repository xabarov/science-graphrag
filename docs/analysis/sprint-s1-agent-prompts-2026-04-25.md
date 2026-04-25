# Sprint S1 — Agent Prompts («расчищаем воркер»)

> Дата: 2026-04-25  
> Источник плана: `docs/analysis/master-roadmap-and-refactor-plan-2026-04-25.md` §5 Sprint S1  
> Порядок запуска: **P4 → затем P1+P2+P5+P6 параллельно → затем P3** (P3 зависит от P4, см. ниже).

---

## P4 — G-PhoenixSplit (запустить ПЕРВЫМ, ~1–2 ч)

**Задача:** Разнести `science_graphrag/observability/phoenix_tracer.py` (492 строки) в пакет
`science_graphrag/observability/` с четырьмя модулями, сохранив публичный API без изменений поведения.

### Контекст

Ты — агент рефакторинга Python-пакета `science_graphrag`. Работаешь в репозитории
`/home/roman/pyprojects/ML/Prod/science-graphrag`. Используй venv: `.venv/bin/python`.

Текущий файл `science_graphrag/observability/phoenix_tracer.py` совмещает:
- `init_tracer_provider` — инициализацию Phoenix/OTel провайдера
- `chain_span`, `llm_span`, `embeddings_span` — хелперы span-обёрток
- `PHOENIX_TRACE_SCOPE` и `_EXTRACTION_LLM_CHAIN_NAMES` — политику скоупа
- OpenAI auto-instrumentation хуки

Этот split нужен первым потому, что агент P3 (Wave Y1) добавит LangChain instrumentation именно в
`observability/instrumentation.py` — новый модуль, который создаёшь ты. Если P3 запустить до тебя,
будет merge-конфликт.

### Что сделать

1. **Создать пакет** `science_graphrag/observability/` (уже существует как папка с `__init__.py`, но
   `phoenix_tracer.py` — единственный модуль). Разделить его на:

   - `science_graphrag/observability/init.py` — функции `init_tracer_provider(settings)` и lifespan
     helper. Имена и сигнатуры сохранить **без изменений**.
   - `science_graphrag/observability/spans.py` — `chain_span`, `llm_span`, `embeddings_span` и любые
     внутренние helpers (context managers, attrs). Если в будущем добавится `traced_tool_span` (Wave X2)
     — его место здесь.
   - `science_graphrag/observability/scope.py` — константа `PHOENIX_TRACE_SCOPE` (читается из env /
     settings), список `_EXTRACTION_LLM_CHAIN_NAMES`, логика фильтрации по scope.
   - `science_graphrag/observability/instrumentation.py` — **создать пустой/stub модуль**:
     заглушка `setup_langchain_instrumentation()` с `pass` и комментарием
     `# populated by Wave Y1 (langchain-instrumentation)`. Это место, куда P3 добавит код.

2. **Обновить `science_graphrag/observability/__init__.py`** — реэкспортировать всё, что раньше
   импортировалось из `phoenix_tracer.py`:
   ```python
   from science_graphrag.observability.init import init_tracer_provider
   from science_graphrag.observability.spans import chain_span, llm_span, embeddings_span
   from science_graphrag.observability.scope import PHOENIX_TRACE_SCOPE
   ```
   Так все `from science_graphrag.observability.phoenix_tracer import ...` продолжат работать через
   `phoenix_tracer.py`, который должен стать thin re-export:

3. **`phoenix_tracer.py` оставить** как **тонкий re-export модуль** (не удалять — он импортируется
   во многих местах):
   ```python
   # Backward-compat re-export. Do not add logic here.
   from science_graphrag.observability import (  # noqa: F401
       init_tracer_provider, chain_span, llm_span, embeddings_span, PHOENIX_TRACE_SCOPE,
   )
   from science_graphrag.observability.scope import _EXTRACTION_LLM_CHAIN_NAMES  # noqa: F401
   ```

4. **Проверить все импорты** в репозитории:
   ```bash
   rg "from science_graphrag.observability" --include="*.py" -l
   rg "phoenix_tracer" --include="*.py" -l
   ```
   Убедиться, что все они продолжат работать через backward-compat `phoenix_tracer.py` или `__init__.py`.

5. **Тесты.** Если существует `tests/observability/test_span_contract.py` — запустить и убедиться, что
   они зелёные. Если тестов нет — создать минимальный
   `tests/observability/test_span_contract.py` с тремя тест-кейсами:
   - `test_chain_span_imports` — импорт `chain_span` из `phoenix_tracer` не бросает `ImportError`
   - `test_llm_span_imports` — аналогично `llm_span`
   - `test_scope_constant_readable` — `PHOENIX_TRACE_SCOPE` возвращает строку (из env или дефолт)

### Quality gate

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag
.venv/bin/isort science_graphrag/observability/
.venv/bin/black science_graphrag/observability/
.venv/bin/pylint science_graphrag/observability/ tests/observability/ --fail-under=7.0
.venv/bin/pytest tests/observability/ -v
```

### Файловый скоуп (строго)

**Трогать:** `science_graphrag/observability/` (все файлы), `tests/observability/`.  
**Не трогать:** `science_graphrag/ingestion/`, `science_graphrag/api/`, `science_graphrag/agent/`,
любые другие пакеты. P3 добавит instrumentation — это его задача.

### Backlog

После выполнения пометить в `docs/backlog/refactor-backend.md`:
```
### [DONE] Split `observability/phoenix_tracer.py` (492) — init vs spans vs instrumentation
...
- **Note (done):** 2026-04-25 — разнесено на init.py / spans.py / scope.py / instrumentation.py(stub);
  backward-compat через phoenix_tracer.py re-export; Wave Y1 добавит тело instrumentation.py.
```

---

## P1 — G-IngestSlim (параллельно с P2/P5/P6, после старта P4)

**Задача:** Разнести `science_graphrag/api/ingest_jobs.py` (846 строк) в пакет
`science_graphrag/api/ingest/` с четырьмя модулями.

### Контекст

Ты — агент рефакторинга Python-пакета `science_graphrag`. Репозиторий:
`/home/roman/pyprojects/ML/Prod/science-graphrag`. Venv: `.venv/`.

`api/ingest_jobs.py` совмещает:
- HTTP-роутер FastAPI (`/v1/ingest/...`)
- `IngestJobRegistry` — Postgres/ORM-стор jobs, stages, events
- SSE endpoint (`/v1/ingest/jobs/{id}/events`)
- in-process `threading.Thread` воркер (временно; Wave W заменит на Dramatiq actor)
- `IngestEventBus` — in-process (уже в отдельном `ingest_event_bus.py`; не трогать)
- DTO: `IngestJobView`, `IngestStageView`, `IngestJobEvent`

Wave W (следующий спринт) заменит только `dispatcher.py` и реализацию `IngestEventBus`. Твоя задача —
создать эту границу сейчас, не меняя поведения.

### Что сделать

1. **Создать пакет** `science_graphrag/api/ingest/` с файлами:

   - **`dto.py`** — Pydantic/dataclass модели `IngestJobView`, `IngestStageView`, `IngestJobEvent` и
     маппинги ORM→DTO. Только модели и конверторы, никакого FastAPI.

   - **`registry.py`** — класс `IngestJobRegistry`: всё, что связано с SQLAlchemy ORM (`IngestJobOrm`,
     `IngestJobStageOrm` и пр.), операции `create_job`, `update_stage`, `mark_failed`, `get_job`,
     `list_jobs`, `get_job_events`. Зависит только от `dto.py` и SQLAlchemy.

   - **`dispatcher.py`** — текущий in-process воркер: `_execute_single_ingest(job_id, ...)` запускает
     pipeline в `threading.Thread`, пишет события через `IngestEventBus`. Это класс/функция
     `IngestDispatcher`. **Оставить пустой сигнатурный метод `enqueue(job_id)`** с TODO-комментарием
     `# Wave W: replace with Dramatiq actor.enqueue(ingest_document_actor, job_id)`.

   - **`router.py`** — тонкий FastAPI `APIRouter`: только handlers (`POST /jobs`, `GET /jobs`,
     `GET /jobs/{id}`, `DELETE /jobs/{id}`, `GET /jobs/{id}/events` SSE). Вся логика делегирована
     `registry.py` и `dispatcher.py`.

2. **`api/ingest_jobs.py`** — сделать **thin re-export** и переключить APIRouter:
   ```python
   # Backward-compat shim. Logic moved to api/ingest/.
   from science_graphrag.api.ingest.router import router  # noqa: F401
   from science_graphrag.api.ingest.dto import IngestJobView, IngestStageView  # noqa: F401
   ```
   `api/main.py` продолжает `include_router(ingest_jobs.router)` — без изменений.

3. **Проверить все import-цепочки:**
   ```bash
   rg "ingest_jobs" --include="*.py" -l
   ```
   Убедиться, что обратная совместимость сохранена через shim.

4. **Тесты:** Все существующие тесты `tests/test_api_smoke*`, `tests/test_ingest_*` должны
   оставаться зелёными без правок поведения. Добавить минимальные юниты:
   - `tests/api/ingest/test_registry.py` — `test_create_job_returns_view`, `test_update_stage_status`
     (с моком SQLAlchemy session).
   - `tests/api/ingest/test_dto.py` — `test_ingest_job_view_from_orm`.

### Важные ограничения

- **Не трогать** `api/ingest_event_bus.py` — это отдельный модуль, Wave W будет его менять.
- **Не трогать** `ingestion/pipeline.py` — это скоуп P2.
- **Не менять** контракты HTTP-эндпоинтов (URL paths, response schemas).
- Ни один файл в `api/ingest/` **не должен превышать ~400 строк**.

### Quality gate

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag
.venv/bin/isort science_graphrag/api/ingest/
.venv/bin/black science_graphrag/api/ingest/
.venv/bin/pylint science_graphrag/api/ingest/ tests/api/ingest/ --fail-under=7.0
.venv/bin/pytest tests/ -k "ingest" -v
```

### Backlog

Пометить в `docs/backlog/refactor-backend.md` запись `[OPEN] Slim api/ingest_jobs.py...` как:
```
### [DONE] Slim `api/ingest_jobs.py` (846 lines) — registry/worker vs HTTP/SSE
- **Note (done):** 2026-04-25 — разнесено на api/ingest/{dto,registry,dispatcher,router}.py;
  backward-compat shim в ingest_jobs.py; Wave W меняет только dispatcher.py.
```

---

## P2 — G-PipelineFacade (параллельно с P1/P5/P6)

**Задача:** Разрефакторить `science_graphrag/ingestion/pipeline.py` (976 строк) в фасад поверх
модульных stages, ввести `IngestRunContext`.

### Контекст

Ты — агент рефакторинга Python-пакета `science_graphrag`. Репозиторий:
`/home/roman/pyprojects/ML/Prod/science-graphrag`. Venv: `.venv/`.

`ingestion/pipeline.py` оркеструет весь ingest: OpenAlex enrichment, нормализацию, chunking,
embeddings, claims, semantic, references, Neo4j upsert, Qdrant upsert, workspace attach, Phoenix spans
и CLI entrypoints — всё в одном файле. Каждый ingest-маршрут (CLI, batch, API job, будущий Wave W
Dramatiq actor) копирует инициализацию stores.

Уже существуют частичные stage-модули в `ingestion/stages/` (`authorships.py`, `metadata.py`,
`references.py`). `ingestion/stage_context.py` уже существует (Wave U добавил stage context manager).

### Что сделать

1. **Обогатить `IngestRunContext`** в `science_graphrag/ingestion/stage_context.py`:
   - Добавить атрибуты: `neo4j_store: Neo4jGraphStore`, `qdrant_store: QdrantChunkStore`,
     `blob_store: BlobStore`, `phoenix_tracer: PhoenixTracer` (или их фабрики/lazy init).
   - `IngestRunContext` должен быть dataclass или `@contextmanager` фабрикой, которая создаёт stores
     **один раз** и передаёт в каждую стадию.
   - CLI и `api/ingest/dispatcher.py` (P1) одинаково создают `IngestRunContext` — не дублируют init.

2. **Дополнить `ingestion/stages/`** недостающими stage-модулями. Проверить, каких не хватает
   относительно текущего `pipeline.py`. Создать недостающие из этого списка (только то, чего ещё нет):
   - `stages/vl_pdf.py` — PDF extraction (VL path)
   - `stages/chunking.py` — chunking
   - `stages/embeddings.py` — embeddings generation
   - `stages/semantic.py` — semantic extraction
   - `stages/claims.py` — claims extraction
   - `stages/neo4j_upsert.py` — Neo4j upsert (вынести из pipeline.py)
   - `stages/qdrant_upsert.py` — Qdrant upsert
   - `stages/workspace_attach.py` — workspace attach
   
   Каждый stage — функция `run_<stage>(ctx: IngestRunContext, data: <StageInput>) -> <StageOutput>`.
   Внутри — `with ctx.stage("<name>"):` (из существующего `stage_context`).

3. **Переписать `pipeline.py`** как **тонкий фасад** (цель: ≤ 250 строк):
   - `run_ingest_pipeline(ctx: IngestRunContext, source: IngestSource) -> IngestResult` — последовательно
     вызывает stages.
   - `run_ingest_from_file(path, settings)` и `run_ingest_from_job(job_id, settings)` — фабрики
     `IngestRunContext` + вызов `run_ingest_pipeline`.
   - Без лишних импортов stores в `pipeline.py` напрямую.

4. **Проверить** что CLI (`cli/main.py`) и `api/ingest/dispatcher.py` (скоуп P1) вызывают pipeline
   через единый `IngestRunContext`. Если P1 ещё не создал `dispatcher.py` — оставить TODO-комментарий.

5. **Тесты:**
   - Запустить `tests/integration/test_full_ingest_integration.py` — должен остаться зелёным.
   - Добавить `tests/ingestion/test_stage_context.py` — `test_ingest_run_context_creates_stores` (с
     моком settings).
   - Добавить по одному юниту на новые stage-модули с моком `IngestRunContext`.

### Важные ограничения

- **Не трогать** `api/ingest_jobs.py` или `api/ingest/` — это скоуп P1.
- **Не трогать** `observability/phoenix_tracer.py` — это скоуп P4.
- Ни один файл в `ingestion/stages/` **не должен превышать ~300 строк**.
- `pipeline.py` после рефакторинга **≤ 250 строк**.
- Публичные сигнатуры `run_ingest_*` (вызываются из CLI и API) — сохранить совместимость.

### Quality gate

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag
.venv/bin/isort science_graphrag/ingestion/
.venv/bin/black science_graphrag/ingestion/
.venv/bin/pylint science_graphrag/ingestion/ tests/ingestion/ --fail-under=7.0
.venv/bin/pytest tests/ -k "pipeline or ingest or stage" -v
```

### Backlog

Пометить в `docs/backlog/refactor-backend.md` запись `[OPEN] Refactor ingestion/pipeline.py...` как:
```
### [DONE] Refactor `ingestion/pipeline.py` (976 lines) into stages-with-context facade
- **Note (done):** 2026-04-25 — IngestRunContext расширен stores; pipeline.py → ≤250 строк фасад;
  stages/{chunking,embeddings,semantic,claims,neo4j_upsert,qdrant_upsert,workspace_attach,vl_pdf}.py
  добавлены; Wave W actor получает тот же IngestRunContext.
```

---

## P3 — Wave Y1: LangGraph Foundation (запустить ПОСЛЕ завершения P4)

**Задача:** Установить зависимости LangGraph/LangChain, добавить LangChain instrumentation в
`observability/instrumentation.py` (заглушка от P4), обновить конфиг и CI.

### Контекст

Ты — агент backend-разработки `science_graphrag`. Репозиторий:
`/home/roman/pyprojects/ML/Prod/science-graphrag`. Venv: `.venv/`.

Sprint S1 готовит фундамент для LangGraph-миграции (Track B). Wave Y1 — **только foundation**:
никаких изменений runtime-поведения агента, только пакеты, env, CI, и LangChain instrumentation.
Агент-пакет `science_graphrag/agent/` на этом этапе **не меняется** — это Wave Y2 (Sprint S2).

**Предусловие:** P4 (G-PhoenixSplit) завершён. Файл
`science_graphrag/observability/instrumentation.py` существует и содержит заглушку
`setup_langchain_instrumentation()`.

### Что сделать

1. **Добавить зависимости** в `pyproject.toml`. Добавить optional-группу `[project.optional-dependencies]`
   секцию `agent`:
   ```toml
   agent = [
     "langgraph>=0.2",
     "langchain-core>=0.3",
     "langchain-openai>=0.2",
     "openinference-instrumentation-langchain>=0.1",
   ]
   ```
   Установить: `.venv/bin/pip install -e ".[agent]"`. Зафиксировать точные версии в комментарии.

2. **Обновить `.env.example`** — добавить секцию:
   ```
   # LangGraph / LangChain (Wave Y1)
   LANGCHAIN_TRACING_V2=false
   OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
   AGENT_RUNTIME=retrieval_v1   # retrieval_v1 | langgraph_v2 (Wave Y2+)
   AGENT_MAX_TOOL_CALLS=8
   ```

3. **Обновить `science_graphrag/config.py`** — добавить поля настроек:
   ```python
   agent_runtime: str = "retrieval_v1"
   agent_max_tool_calls: int = 8
   openrouter_base_url: str = "https://openrouter.ai/api/v1"
   ```

4. **Наполнить `observability/instrumentation.py`** (заглушка от P4):
   ```python
   def setup_langchain_instrumentation() -> None:
       """Register OpenInference LangChain instrumentor with the current OTel provider."""
       try:
           from openinference.instrumentation.langchain import LangChainInstrumentor
           LangChainInstrumentor().instrument()
       except ImportError:
           pass  # agent extra not installed — skip silently
   ```
   Вызвать эту функцию в `observability/init.py` внутри `init_tracer_provider()` **после** регистрации
   провайдера.

5. **CI** (`.github/workflows/`): убедиться что в CI-шаге тестов `pip install -e ".[agent]"` добавлен
   (или добавить его). Если CI-файла нет — пропустить и написать TODO в `docs/runbooks/roadmap-next-waves.md`.

6. **Smoke-тест LangChain:**
   ```bash
   .venv/bin/python -c "from langchain_openai import ChatOpenAI; print('langchain-openai ok')"
   .venv/bin/python -c "from langgraph.graph import StateGraph; print('langgraph ok')"
   .venv/bin/python -c "from openinference.instrumentation.langchain import LangChainInstrumentor; print('instrumentation ok')"
   ```
   Все три должны выполниться без ошибок.

7. **Обновить `docs/runbooks/roadmap-next-waves.md`** (или создать, если нет): добавить раздел
   "Wave Y1 — Done" с датой, списком установленных пакетов и ссылкой на instrumentation.py.

### Важные ограничения

- **Не трогать** `science_graphrag/agent/runtime.py` или любые agent-модули — это Wave Y2.
- **Не трогать** API-роутеры, инgest-pipeline — чужие скоупы.
- Никаких изменений поведения агента — только установка пакетов и инструментация.

### Quality gate

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag
.venv/bin/python -c "from langchain_openai import ChatOpenAI; from langgraph.graph import StateGraph; print('Y1 ok')"
.venv/bin/isort science_graphrag/observability/ science_graphrag/
.venv/bin/black science_graphrag/observability/ science_graphrag/config.py
.venv/bin/pylint science_graphrag/observability/ science_graphrag/config.py --fail-under=7.0
.venv/bin/pytest tests/observability/ -v
```

---

## P5 — H-i18n-fixes (параллельно с P1/P2/P4)

**Задача:** Вынести hardcoded UI-строки из `HypothesisPanel.jsx`, `IngestionSettingsPanel.jsx` и
`WorkspacePage.jsx` в i18n-словари (`ui/src/i18n/messages/en/` и `ru/`).

### Контекст

Ты — агент фронтенд-рефакторинга. Репозиторий: `/home/roman/pyprojects/ML/Prod/science-graphrag`.
UI находится в `ui/`. После правок запускай `npm run lint` из директории `ui/`.

Проект использует кастомную i18n-систему: `ui/src/i18n/` с контекстом `I18nContext.jsx`, функцией
`translate.js` / хуком `useTranslate` (или аналогом — уточни, прочитав `translate.js`). Словари лежат
в `ui/src/i18n/messages/en/` и `ui/src/i18n/messages/ru/` разбитые по part-файлам
(`partCommon.js`, `partWorkspacePage.js` и пр.).

### Что сделать

1. **Прочитай** файлы `ui/src/i18n/translate.js` и один из `partCommon.js`, чтобы понять, как
   использовать систему переводов (ключи, хуки, функции).

2. **`ui/src/components/work/HypothesisPanel.jsx`** — найди все hardcoded строки. Ожидаемые кандидаты
   (проверь актуальные, файл мог меняться):
   - `"Generating..."`, `"No candidates"`, `"Hypothesis / contradiction assist"`, любые status labels.
   Для каждой: добавь ключ в `partAskPanel.js` (EN+RU), замени литерал на `t("key")` или
   аналогичный вызов i18n-системы.

3. **`ui/src/pages/SettingsPage/IngestionSettingsPanel.jsx`** — аналогично. Ожидаемые:
   - `"Saving…"`, `"Save ingestion settings"`, любые label-строки форм.
   Добавь ключи в `partSettings.js` (EN+RU).

4. **`ui/src/pages/WorkspacePage/WorkspacePage.jsx`** — только строки-литералы (не трогай логику,
   условия, JSX-структуру). Ожидаемые:
   - `"Workspace summary"` и аналогичные заголовки / placeholder'ы.
   Добавь ключи в `partWorkspacePage.js` (EN+RU).

5. Для каждого нового ключа: добавь **и в EN, и в RU** словари. Если перевода нет — вставь `"TODO: RU"` в RU, но не оставляй ключ только в одном словаре.

6. Запусти `npm run lint` — должен быть зелёным.

### Важные ограничения

- **Не трогать** логику, условия рендера, обработку событий — только замена строк.
- **Не трогать** `WorkspaceDedupSection.jsx` — это скоуп P6.
- Не реструктурировать компоненты. Это чисто i18n-патч, не рефакторинг.
- Если компонент не использует i18n-хук — добавить его в начало функции, не переписывать компонент.

### Quality gate

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag/ui
npm run lint
npm run test -- --passWithNoTests
```

---

## P6 — H-Cursor-buttons-in-dedup (параллельно с P1/P2/P4)

**Задача:** Заменить прямые импорты `@mui/material/Button` на `Cursor*` компоненты в
`WorkspaceDedupSection.jsx` и `WorkDedupReviewDialog.jsx`.

### Контекст

Ты — агент фронтенд-рефакторинга. Репозиторий: `/home/roman/pyprojects/ML/Prod/science-graphrag`.
UI: `ui/`. После правок запусти `npm run lint` из `ui/`.

Проект использует кастомную дизайн-систему кнопок:
- `CursorButton` — базовая кнопка (variants: contained, outlined, text)
- `CursorPrimaryButton` — основные действия (сохранить, применить)
- `CursorDangerButton` — деструктивные действия (удалить, отклонить)
- `CursorIconButton` — иконочные кнопки
- `CursorSmallButton` — компактные кнопки

Импорт: `import { CursorButton, CursorDangerButton, CursorPrimaryButton } from '../components/common'`
(путь уточни по актуальному расположению целевых файлов).

**Целевые файлы:**
- `ui/src/pages/WorkspacePage/WorkspaceDedupSection.jsx`
- `ui/src/components/graph/dedup/WorkDedupReviewDialog.jsx`

### Что сделать

1. **Прочитай оба файла** целиком, определи все `<Button ...>` или `Button` импорты из `@mui/material`.

2. **Для каждой кнопки** определи семантику:
   - Подтверждение/применение (merge, accept) → `CursorPrimaryButton`
   - Удаление/отклонение (reject, delete) → `CursorDangerButton`
   - Нейтральные действия (cancel, close, view) → `CursorButton` (variant="outlined" или "text")
   - Иконка без текста → `CursorIconButton`

3. **Замени импорты** и JSX. Убедись что:
   - `color="primary"` → убрать (не нужен, стиль в `CursorPrimaryButton`)
   - `color="error"` → убрать (не нужен, стиль в `CursorDangerButton`)
   - `variant="contained"` → убрать если переходим на `CursorPrimaryButton`
   - `disabled`, `onClick`, `startIcon`, `endIcon` — сохранить как есть (CursorButton-компоненты их
     поддерживают через `...props`).

4. Запусти `npm run lint` — зелёный.

5. **Визуальная проверка** (опциональная): если есть `npm run storybook` или dev-сервер — убедись что
   кнопки отображаются корректно (не обязательно, если нет быстрого способа).

### Важные ограничения

- **Только кнопки** — не трогать Dialog, TextField, Chip и другие MUI-компоненты.
- **Не трогать** логику, обработку событий, state.
- **Не трогать** `HypothesisPanel.jsx` или другие компоненты — это вне скоупа.
- Если какой-то Cursor* компонент не поддерживает нужный prop — добавить `// TODO: verify props`
  комментарий, но не создавать новые Cursor-компоненты.

### Quality gate

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag/ui
npm run lint
```

Убедиться что `grep -r "@mui/material/Button" ui/src/pages/WorkspacePage/WorkspaceDedupSection.jsx ui/src/components/graph/dedup/WorkDedupReviewDialog.jsx` возвращает пустой результат.

---

## Review Agent — Финальная проверка Sprint S1

**Задача:** Проверить, что все 6 задач Sprint S1 выполнены корректно и Sprint S2 можно запускать
без блокировок.

### Контекст

Ты — агент code review. Репозиторий: `/home/roman/pyprojects/ML/Prod/science-graphrag`.
Venv: `.venv/`. UI: `ui/`.

Sprint S1 выполнил следующее (должно быть проверено):
- **P4 G-PhoenixSplit:** `observability/` → пакет с `init.py`, `spans.py`, `scope.py`, `instrumentation.py`
- **P1 G-IngestSlim:** `api/ingest_jobs.py` → пакет `api/ingest/` с 4 модулями
- **P2 G-PipelineFacade:** `ingestion/pipeline.py` → ≤250 строк фасад + `IngestRunContext` + stage-модули
- **P3 Wave Y1:** LangGraph/LangChain deps, `instrumentation.py` наполнен, `.env.example` обновлён
- **P5 H-i18n-fixes:** hardcoded строки в 3 frontend-файлах заменены на i18n-ключи
- **P6 H-Cursor-buttons:** MUI `Button` заменены на `Cursor*` в 2 dedup-файлах

### Чеклист проверки

Пройди **все** пункты последовательно. По каждому выведи: ✅ OK, ⚠️ Частично, ❌ Провалено.

#### 1. Структурные проверки (файлы существуют)

```bash
ls science_graphrag/observability/init.py
ls science_graphrag/observability/spans.py
ls science_graphrag/observability/scope.py
ls science_graphrag/observability/instrumentation.py
ls science_graphrag/observability/phoenix_tracer.py   # должен остаться как re-export shim

ls science_graphrag/api/ingest/__init__.py
ls science_graphrag/api/ingest/router.py
ls science_graphrag/api/ingest/registry.py
ls science_graphrag/api/ingest/dispatcher.py
ls science_graphrag/api/ingest/dto.py

ls science_graphrag/ingestion/stages/chunking.py
ls science_graphrag/ingestion/stages/embeddings.py
ls science_graphrag/ingestion/stages/neo4j_upsert.py
ls science_graphrag/ingestion/stages/qdrant_upsert.py
```

#### 2. Backward-compat: импорты через shim не сломаны

```bash
.venv/bin/python -c "from science_graphrag.observability.phoenix_tracer import chain_span, llm_span, init_tracer_provider, PHOENIX_TRACE_SCOPE; print('observability shim ok')"
.venv/bin/python -c "from science_graphrag.api.ingest_jobs import router; print('ingest_jobs shim ok')"
```

#### 3. Размер файлов (god-файлы распилены)

```bash
wc -l science_graphrag/observability/phoenix_tracer.py   # должен быть ≤ 15 строк (shim)
wc -l science_graphrag/api/ingest_jobs.py                # должен быть ≤ 15 строк (shim)
wc -l science_graphrag/ingestion/pipeline.py             # должен быть ≤ 250 строк
for f in science_graphrag/api/ingest/*.py; do echo "$f:"; wc -l "$f"; done  # каждый ≤ 400
for f in science_graphrag/observability/*.py; do echo "$f:"; wc -l "$f"; done  # каждый ≤ 300
```

#### 4. Wave Y1: LangGraph установлен

```bash
.venv/bin/python -c "from langchain_openai import ChatOpenAI; print('langchain-openai ok')"
.venv/bin/python -c "from langgraph.graph import StateGraph; print('langgraph ok')"
.venv/bin/python -c "from openinference.instrumentation.langchain import LangChainInstrumentor; print('instrumentation ok')"
grep "agent_runtime" science_graphrag/config.py
grep "AGENT_RUNTIME" .env.example
```

#### 5. Quality gates: Python

```bash
.venv/bin/isort --check science_graphrag/observability/ science_graphrag/api/ingest/ science_graphrag/ingestion/
.venv/bin/black --check science_graphrag/observability/ science_graphrag/api/ingest/ science_graphrag/ingestion/
.venv/bin/pylint science_graphrag/observability/ science_graphrag/api/ingest/ science_graphrag/ingestion/ --fail-under=7.0
.venv/bin/pytest tests/ -x -q 2>&1 | tail -20
```

#### 6. Quality gates: Frontend

```bash
cd ui && npm run lint 2>&1 | tail -20
```

#### 7. i18n: строки вынесены

```bash
# Не должно быть hardcoded строк (примерный grep):
grep -n '"Generating\.\.\."' ui/src/components/work/HypothesisPanel.jsx && echo "FOUND hardcoded" || echo "ok"
grep -n '"Saving…\|Save ingestion settings"' ui/src/pages/SettingsPage/IngestionSettingsPanel.jsx && echo "FOUND hardcoded" || echo "ok"
```

#### 8. Dedup-кнопки

```bash
grep -n 'from.*@mui/material.*Button' ui/src/pages/WorkspacePage/WorkspaceDedupSection.jsx && echo "FOUND raw MUI Button" || echo "ok"
grep -n 'from.*@mui/material.*Button' ui/src/components/graph/dedup/WorkDedupReviewDialog.jsx && echo "FOUND raw MUI Button" || echo "ok"
grep -n 'CursorPrimaryButton\|CursorDangerButton\|CursorButton' ui/src/pages/WorkspacePage/WorkspaceDedupSection.jsx
grep -n 'CursorPrimaryButton\|CursorDangerButton\|CursorButton' ui/src/components/graph/dedup/WorkDedupReviewDialog.jsx
```

#### 9. IngestRunContext доступен и используется

```bash
.venv/bin/python -c "from science_graphrag.ingestion.stage_context import IngestRunContext; print('IngestRunContext ok')"
grep -rn "IngestRunContext" science_graphrag/ingestion/pipeline.py science_graphrag/api/ingest/dispatcher.py
```

#### 10. dispatcher.py содержит Wave W TODO

```bash
grep -n "Wave W" science_graphrag/api/ingest/dispatcher.py && echo "TODO found" || echo "MISSING Wave W TODO"
```

#### 11. Backlog hygiene

```bash
grep "\[DONE\].*IngestSlim\|ingest_jobs" docs/backlog/refactor-backend.md | head -5
grep "\[DONE\].*pipeline\|PipelineFacade" docs/backlog/refactor-backend.md | head -5
grep "\[DONE\].*phoenix_tracer\|PhoenixSplit" docs/backlog/refactor-backend.md | head -5
```

#### 12. Никаких сломанных импортов в API main.py

```bash
.venv/bin/python -c "from science_graphrag.api.main import app; print('app imports ok')"
```

### Что делать с найденными проблемами

После прогона всех проверок:

1. **Если все ✅** — написать: «Sprint S1 complete. Ready for S2 (Wave W + Y2 + X2 + Neo4jSplit).»
   Указать метрику: сколько строк распилено в сумме, какие тесты зелёные.

2. **Если есть ⚠️** — описать конкретно что частично выполнено, какие шаги остались.

3. **Если есть ❌** — описать пункт провала, вывод команды, возможную причину. Не пытаться
   починить самостоятельно — только репортировать.

### Не входит в scope Review Agent

- Не вносить изменения в код — только читать и запускать команды.
- Не запускать интеграционные тесты с реальными БД (Neo4j, Qdrant, Postgres).
- Не оценивать качество кода субъективно — только факты из checklist.
