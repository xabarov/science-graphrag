# Phoenix tracing coverage — анализ ingestion и IR, план Wave X

**Дата:** 2026-04-25
**Статус:** living working doc; новый трек observability, не пересекается с волнами ingest-async (U–W) и benchmark-onthology (M–T).
**Update 2026-04-27 (Wave X3 — Dramatiq boundary):** на стороне **producer** (`enqueue_ingest_job`, compensation sweep в `science_graphrag/worker/__init__.py`) добавлен `opentelemetry.propagate.inject` → non-empty carrier уходит в Dramatiq `message.options`; воркер по-прежнему поднимает контекст в `OtelTraceMiddleware.before_process_message`. Код: `science_graphrag/worker/trace_options.py`. Тесты: `tests/observability/test_worker_trace_propagation.py` (в т.ч. inject под активным span). **Не доказано автотестом:** полный e2e «HTTP request → enqueue → worker span как child» на живом Redis/Phoenix — проверять на стенде.
**Цель:** оценить, насколько удобно сегодня смотреть трейсы по двум основным пайплайнам (ingestion и IR/retrieval agent), зафиксировать what good looks like для Phoenix/OpenInference, перечислить конкретные пробелы и оформить план работ с чеклистом, который можно брать в работу сразу.

**Контекст триггера:** в Phoenix → `Settings → Models` загружены кастомные модели c ценами:

- `mistralai/mistral-small-3.2-24b-instruct` (через OpenRouter) — `MAIN_LLM_MODEL`, она же `extraction_llm_model` (метаданные / authorships / references / claims / semantic).
- `qwen/qwen3-vl-235b-a22b-instruct` (через OpenRouter) — `SCIENCE_GRAPHRAG_VL_MODEL`, используется в VL-извлечении PDF → Markdown.

Чтобы Phoenix корректно атрибутировал стоимость и метрики, спаны должны быть **LLM-кинда** и нести `llm.model_name`/`llm.provider`/`llm.token_count.*`. Сейчас это выполнено лишь частично — см. §3.

**Связанные документы:**

| Документ | Что в нём |
|----------|-----------|
| [../adr/016-agent-tool-registry-and-langgraph.md](../adr/016-agent-tool-registry-and-langgraph.md) | Целевая архитектура агента / реестра инструментов |
| [../specs/agent-tools-v1.md](../specs/agent-tools-v1.md) | Контракт инструментов агента (idea_search, edge_search, …) |
| [`_archive/ingestion-async-pipeline-roadmap-2026-04-25.md`](./_archive/ingestion-async-pipeline-roadmap-2026-04-25.md) [ARCHIVED] | Wave U–W (delivered): стадии ingest, SSE, Redis/Dramatiq |
| [../specs/frontend-ui-api-contracts-v1.md](../specs/frontend-ui-api-contracts-v1.md) | API контракты UI ↔ backend |
| [../runbooks/roadmap-next-waves.md](../runbooks/roadmap-next-waves.md) | Сводный список волн (после принятия — добавить Wave X-Phoenix) |

---

## 1. TL;DR

1. **Ingestion** уже размечен набором `chain_span` / `llm_span`, видно фазы и три ключевых LLM-вызова (`llm.metadata_extraction`, `llm.authorships_extraction`, `llm.references_extraction`). Это близко к best practice OpenInference, но есть **системные дыры**:
   - VL-вызов (`vl_pdf.chat_completions`) — это `llm_span`, но в нём **не выставляется `llm.model_name` и `llm.token_count.*`** → Phoenix не считает стоимость VL и не подцепляет цену из `Settings → Models` для `qwen/qwen3-vl-235b-a22b-instruct`.
   - `claims_extraction` — внутри `chain_span` напрямую вызывается `extractor.extract_maybe(...)`, который пишет `llm.model_name` / токены **на CHAIN-спан**. В UI это выглядит как CHAIN, не LLM, и **выпадает из агрегаций по моделям и стоимости**.
   - Дерево фаз неконсистентно: часть подспанов (`pdf_to_markdown`, `metadata_and_references_extraction`, `openalex_enrichment`, `neo4j_graph_persistence`, `semantic_method_dataset`, `claims_extraction`, `qdrant_*`, `fallback.*`) идёт **без префикса `ingest.*`**, а часть фаз заворачивается стейджем `ingest.{stage}` поверх `chain_span` — двойная иерархия, в Trace UI читается тяжелее.
   - `neo4j_graph_persistence` оборачивает сразу несколько стадий (`ENRICH_ROR`, `WRITE_GRAPH`, `RESOLVE_REFERENCES`) — выглядит как «одна большая операция», хотя стадии — независимые.
   - `stage(ATTACH_WORKSPACE)` открывается в `api/ingest_jobs.py` **после** закрытия `chain_span("ingest_document")` — становится **отдельным root-спаном**, теряет связь с trace ingest.
   - Нет `session.id` (job_id), нет `user.id` (workspace_id) → UI не группирует трейсы по ingest-задаче. В Phoenix есть **Sessions UI**, но мы его не используем.
   - Эмбеддинги (`HashEmbeddingProvider` / `try_sentence_transformer`) и операции Qdrant (`upsert`, `search_similar`) трассируются только косвенно (через `chain_span` с парой атрибутов); RETRIEVER-кинд не используется.

2. **IR / retrieval agent (`science_graphrag/agent/`)** в Phoenix **не виден вообще**:
   - В `agent/runtime.py`, `agent/tools/*.py` нет ни одного `chain_span` / `llm_span` / `traced_tool_span`.
   - `BaseAgentTool.run_with_trace` собирает **только in-memory `ToolCallTrace`**, который возвращается в API-ответе `/v1/agent/query` и больше никуда не уходит.
   - Сам endpoint `/v1/agent/query` не вызывает `init_tracer_provider()`. Если в этот процесс что-то попадает, то лишь потому, что когда-то ранее в этом же процессе ingestion уже инициализировал tracer.
   - Нет ни корневого CHAIN-спана `agent.query`, ни TOOL-спанов (`idea_search`, `summarize_workspace`, `final_answer`), ни RETRIEVER-спана для Qdrant, ни LLM-спана для будущих ответов агента.
   - Итого: **в Phoenix мы не наблюдаем ни одну сессию вопрос-ответа**, не можем посмотреть, какие инструменты дёрнул агент, сколько он искал, что возвращал Qdrant, какие чанки попали в контекст.

3. Ниже — **детальный обзор по каждой стадии** и **план волны X-Phoenix** с двумя подзадачами:
   - **X1 (cheap wins, без рефакторинга)**: исправить дыры в существующих спанах (VL, claims, dual-hierarchy, attach_workspace, session.id).
   - **X2 (новый трек)**: разметить агент / retrieval, сделать его first-class observable.

---

## 2. Снимок текущей реализации

### 2.1 Хелперы tracing (`science_graphrag/observability/phoenix_tracer.py`)

Реализовано хорошо и близко к OpenInference v1:

- `init_tracer_provider()` — однократная инициализация Phoenix exporter, нормализация endpoint (`http://phoenix:6006` → `…/v1/traces`), batch vs simple processor по `ENV`.
- `chain_span(name, attrs)` — CHAIN-спан, корректно ставит `openinference.span.kind = "CHAIN"`, ловит исключения, помечает Status = ERROR.
- `llm_span(name, attrs)` — то же для LLM.
- `traced_tool_span(name, tool_name=…, tool_parameters=…, tool_description=…)` — TOOL-спан (готовая обёртка, **никем не используется**).
- `SpanAttributes.set_llm_attrs(model, …)` — `llm.model_name`, `llm.provider`, `llm.system`, `llm.temperature`, `llm.max_tokens`, токены через `set_llm_token_counts(...)`.
- `SpanAttributes.set_llm_input_messages` / `set_llm_output_messages` — flat-формат `llm.input_messages.{i}.message.role|content|tool_calls.*`.
- `SpanAttributes.set_input` / `set_output` + `_safe_json` — обрезка длинных payload до `PHOENIX_SPAN_IO_MAX_LEN` (по умолчанию 4 000 символов).
- `SpanAttributes.estimate_token_count` + `usage_source = "estimated"` — fallback, когда провайдер не вернул `usage`.
- `phoenix_trace_scope` = `full` | `extraction_llm` — runtime-фильтр, отрубающий «шумные» спаны и оставляющий только `ingest_document` + `metadata_and_references_extraction` + три LLM-вызова.
- Опциональная авто-инструментация OpenAI-клиента (`openinference.instrumentation.openai`), включается, если `PHOENIX_OPENAI_AUTO_INSTRUMENTATION≠0`.

То есть фундамент — **на уровне best practice**. Проблема не в нём, а в **точках вызова** ниже.

### 2.2 Дерево спанов на одну ingest-задачу (как сейчас)

```
ingest_document                                    [CHAIN]
├── ingest.parse_pdf                               [CHAIN, stage]
│   └── pdf_to_markdown                            [CHAIN]
│       └── vl_pdf.chat_completions                [LLM]  ⚠ нет llm.model_name / token_count
├── ingest.extract_meta                            [CHAIN, stage]
│   └── metadata_and_references_extraction         [CHAIN]
│       ├── llm.metadata_extraction                [LLM]  ✅ полный набор llm.* атрибутов
│       ├── llm.authorships_extraction             [LLM]  ✅
│       └── llm.references_extraction              [LLM]  ✅ × N батчей
│           (опц. fallback.metadata / fallback.authorships / fallback.authorships_probe — CHAIN)
├── ingest.enrich_openalex                         [CHAIN, stage]
│   └── openalex_enrichment                        [CHAIN]  ⚠ HTTP к OpenAlex без RETRIEVER-кинда и input/output
├── neo4j_graph_persistence                        [CHAIN]  ⚠ обёртка, в которой живут СРАЗУ ТРИ стадии
│   ├── ingest.enrich_ror                          [CHAIN, stage]
│   ├── ingest.write_graph                         [CHAIN, stage]
│   │   └── semantic_method_dataset                [CHAIN]
│   │       └── llm.semantic_method_dataset        [LLM]  ✅  (× 1–3 attempts)
│   └── ingest.resolve_references                  [CHAIN, stage]
├── ingest.chunk                                   [CHAIN, stage]
├── ingest.extract_claims                          [CHAIN, stage]
│   └── claims_extraction                          [CHAIN]  ⚠ atomic LLM call внутри пишет llm.* НА CHAIN
├── ingest.embed                                   [CHAIN, stage]
│   ├── qdrant_vector_upsert                       [CHAIN]  ⚠ без RETRIEVER, без db.system
│   └── qdrant_claims_upsert                       [CHAIN]  ⚠ то же
└── (КОНЕЦ ingest_document)
ingest.attach_workspace                            [CHAIN]  ⚠ ROOT, потерял родителя ingest_document
```

Легенда: ✅ — корректно (LLM-кинд + полный llm.* контракт); ⚠ — есть конкретный дефект, см. §3.

### 2.3 Дерево спанов на один agent.query (как сейчас)

```
(пусто)
```

Никаких OTel-спанов не отправляется. В UI Phoenix `/projects/.../traces` запрос `POST /v1/agent/query` не отображается.

В ответе API возвращается `tool_trace: list[ToolCallTrace]`, где для каждого инструмента есть `step`, `tool`, `args_summary`, `row_count`, `duration_ms`, `truncated`, `error`. Этот объект — **только в HTTP-ответе**, в Phoenix не уходит.

---

## 3. Что плохо и почему — детальный разбор

### 3.1 Ingestion: дыры в LLM-атрибуции (это блокирует «$ за токены»)

**A. VL PDF: нет `llm.model_name` и `llm.token_count.*`.**
Файл `science_graphrag/ingestion/vl_pdf.py`, метод `pdf_to_markdown` открывает `llm_span("vl_pdf.chat_completions", {vl.model, vl.base_url, pdf.path})`, но **ни разу** не вызывает `SpanAttributes.set_llm_attrs(...)` и не парсит `usage` из ответа OpenRouter. На стороне Phoenix этот спан виден как «LLM-вызов без модели и без токенов», и пользователь не получит ни денег, ни цифр по `qwen/qwen3-vl-235b-a22b-instruct`, цену которого он только что внёс в Settings → Models.

**Чем чинить:** в `vl_pdf.chat_completions` после `response.json()`:
- `SpanAttributes.set_llm_attrs(self.settings.vl_model, base_url=self.settings.vl_base_url, temperature=0.0, max_tokens=12000)`
- `SpanAttributes.set_llm_input_messages([{"role":"user","content": <prompt + images placeholder>}])` (с обрезкой PNG до placeholder, чтобы не раздуть атрибуты)
- `SpanAttributes.set_llm_output_messages([{"role":"assistant","content": markdown_truncated}])`
- `SpanAttributes.set_llm_token_counts(prompt_tokens=usage.prompt_tokens, completion_tokens=usage.completion_tokens, ...)` — если в ответе есть `usage`; иначе `set_llm_token_counts_from_text(...)` (estimated).
- `SpanAttributes.set_llm_invocation_parameters({"model": …, "max_tokens": …, "pages": len(images)})`.

**B. `claims_extraction` пишет llm.* на CHAIN.**
В `pipeline.py`:
```python
with chain_span("claims_extraction", {...}):
    claim_rows = extract_claims_llm(...)
```
Внутри `extract_claims_llm` вызывается `ext.extract_maybe(...)` (`science_graphrag/ingestion/llm/extractor.py`), который **сам** делает `SpanAttributes.set_llm_attrs(self.model, ...)` и пишет `llm.input_messages.*`, `llm.output_messages.*`, `llm.token_count.*` **на текущий спан**. Но текущий спан — это `chain_span("claims_extraction", ...)`, у которого `openinference.span.kind = "CHAIN"`. В Phoenix UI это отображается как CHAIN с подвешенными llm.* — оно НЕ попадает в LLM-аналитику, в фильтр `kind = LLM` и в подсчёт стоимости по `Settings → Models`.

**Чем чинить:** обернуть вызов в `llm_span("llm.claims_extraction", {...})` точно так же, как сделано для `metadata_and_references_extraction`:
```python
with llm_span("llm.claims_extraction", {"document.id": doc_id, "work.id": work_id, "chunks": len(chunk_dicts)}):
    parsed, err = ext.extract_maybe(...)
```
И убрать дублирование: либо оставить только `llm_span` (если CHAIN-обёртка не нужна), либо `chain_span("claims_extraction") → llm_span("llm.claims_extraction")` — как в metadata-блоке.

**C. Семантика — корректно, но дерево слишком глубокое.**
`semantic_method_dataset` (CHAIN) → `llm.semantic_method_dataset` (LLM) — структурно правильно. Но `semantic_method_dataset` сидит внутри `ingest.write_graph`, который сидит внутри `neo4j_graph_persistence`, который сидит внутри `ingest_document`. Пять уровней до LLM — много. См. §3.3.

### 3.2 Ingestion: HTTP к OpenAlex / Qdrant / Neo4j не размечен по конвенции

**A. OpenAlex enrichment.** `chain_span("openalex_enrichment")` — это HTTP-вызов к `api.openalex.org` через `httpx` (внутри `_openalex_lookup_with_retry`), плюс фильтрация по DOI. Это «retrieval» в широком смысле — есть запрос, есть ответ, есть retries. Best practice — **RETRIEVER**-кинд (как у Phoenix-инструментаций для retrieval баз) или хотя бы CHAIN с осмысленными `input.value` (DOI) / `output.value` (короткий summary найденной работы) и `retry.attempts`. Сейчас атрибутов на спане нет вообще.

**B. Qdrant upsert.** `qdrant_vector_upsert` / `qdrant_claims_upsert` — это запись в векторную БД. На спан повешено только `chunks`/`claims` и `embedding`. По OpenInference / OpenTelemetry-DB-конвенции стоит добавить:
- `db.system = "qdrant"`
- `db.collection.name = settings.qdrant_collection`
- `db.operation = "upsert"`
- `vector.dim = embedder.dim`
- `vector.count = len(vectors)`

С такими атрибутами в Phoenix UI можно фильтровать по `db.collection.name` и сравнивать прогон до / после смены модели эмбеддинга.

**C. Neo4j writes.** `_retry_call(neo.upsert_work_layer1, …)`, `_retry_call(neo.merge_cites, …)`, `_retry_call(neo.upsert_claims_with_evidence, …)` — это серия Cypher writes в одной стадии `WRITE_GRAPH` без отдельных спанов. Если заворачивать «слишком много спанов на одну ingest-задачу», UI разваливается; если «слишком мало» — теряется латенси по конкретной операции. Для production достаточно **двух**: `neo4j.upsert_work_layer1` и `neo4j.upsert_claims_with_evidence` (самые крупные write); остальное — атрибуты на стадийном спане (`writes.cites`, `writes.institutions`).

### 3.3 Ingestion: дерево фаз неконсистентно

**A. Двойная иерархия: `ingest.{stage}` + произвольные `chain_span`.**
Сейчас `stage_context.stage()` всегда открывает `chain_span(f"ingest.{stage_name.value}")`, а внутри стадии тут же открывается ещё один `chain_span` без префикса (`pdf_to_markdown`, `openalex_enrichment`, `semantic_method_dataset`, `claims_extraction`, `qdrant_vector_upsert` …). В Trace UI это выглядит как «лестница из CHAIN'ов», в которой человек не сразу видит, где стадия, а где её внутренняя секция.

**Чем чинить:** ввести соглашение о наименовании:
- Корень: `ingest_document` (как сейчас).
- Стадии: `ingest.<stage>` (как сейчас, через `stage()` контекстный менеджер).
- Подспаны внутри стадии: `ingest.<stage>.<substep>`, например `ingest.parse_pdf.vl`, `ingest.extract_meta.metadata_and_refs`, `ingest.write_graph.semantic`, `ingest.embed.qdrant_chunks`, `ingest.extract_claims.llm`, `ingest.enrich_openalex.lookup`.
- Fallback'и: `ingest.<stage>.fallback.<reason>` (например `ingest.extract_meta.fallback.metadata`).
- LLM: оставить нынешний шаблон `llm.<call_name>` (`llm.metadata_extraction`, `llm.semantic_method_dataset`, `llm.claims_extraction`, `llm.vl_pdf`).

Это даёт **естественную сортировку** в Phoenix UI и упрощает поиск.

**B. `neo4j_graph_persistence` оборачивает три стадии.**
В `pipeline.py` `chain_span("neo4j_graph_persistence")` обнимает `ENRICH_ROR`, `WRITE_GRAPH`, `RESOLVE_REFERENCES`. Это путает: стадии — независимые шаги в нашей модели, но в трассировке оказываются «детьми одной операции записи в Neo4j», хотя ROR-lookup — это про HTTP к ROR API, а не про Neo4j. Стоит **убрать обёртку** и оставить стадии как прямых детей `ingest_document`. Семантика «работа с Neo4j» нужна, но её правильно выражать атрибутами на отдельных операциях, а не одним общим CHAIN.

**C. `ingest.attach_workspace` сирота.**
`stage(ATTACH_WORKSPACE, …)` вызывается в `api/ingest_jobs.py::_execute_single_ingest` ПОСЛЕ выхода из `ingest_document` (из-за этого `chain_span("ingest_document")` уже закрыт). В результате `ingest.attach_workspace` появляется в Phoenix как **отдельный root-trace**, не привязанный к ingest-задаче.

**Чем чинить:**
- Вариант 1 (чистый): перенести `attach_workspace` внутрь `ingest_document(...)` (передавая `ingest_workspace_ids`, как уже передаётся), чтобы стадия закрывалась под общим корнем.
- Вариант 2 (минимальный): в `_execute_single_ingest` обернуть всё (включая `ingest_document` и `attach_workspace`) во **внешний** `chain_span("api.ingest_job", {"job.id": job_id, "workspace.id": …})`. Заодно появится корень для метрики «общая длительность одной ingest-задачи» с её id.

**D. `pdf_to_markdown` и `metadata_and_references_extraction` — без явного `ingest.<stage>.*` префикса.**
Это не баг, но снижает читаемость. См. §3.3.A.

### 3.4 Ingestion: нет корреляции trace ↔ ingest job

Сейчас у трейса ingest нет ни `session.id`, ни `user.id`, ни `metadata.workspace_id`, ни `job.id`. То есть:

- В Phoenix UI трейсы не группируются по «job», нельзя выбрать сессию = «всё, что было сделано для этого ingest-job-id», нельзя посмотреть в Sessions UI хронологию по workspace.
- Ассоциировать конкретную row из `ingest_jobs` (Postgres) с конкретным trace в Phoenix можно только глазами — по timestamp + имени файла.
- При ретроспективном дебаге теряется ответ на вопрос «какой именно job это был?».

**Чем чинить:**
- На корневом спане выставлять `session.id = job_id` (либо `parent_job_id` для batch'ей) и `user.id = workspace_id`. Phoenix сразу подхватит вкладку Sessions.
- На спане `ingest_document` — `metadata.workspace_id`, `metadata.job_id`, `metadata.parent_job_id`, `metadata.source_name`, `metadata.extraction_mode`, `metadata.embedding_model`, `metadata.extraction_llm_model`. Эти атрибуты используют как фильтры/фасетки в Phoenix.
- На стороне `ingest_jobs` сохранять `phoenix_trace_id` рядом с job (берётся из `trace_api.get_current_span().get_span_context().trace_id` после открытия root-спана). Это даст **обратную ссылку** «открыть в Phoenix» из UI ingest-list (Wave U/V уже планирует UI-видимость стадий — туда же можно добавить кнопку).

### 3.5 IR / agent: нет наблюдаемости вообще

**A. Нет root-спана для запроса.** `RetrievalAgent.run(question, workspace_id, max_tool_calls)` — это «вопрос пользователя», конкретная единица работы. Должен быть `chain_span("agent.query", {"agent.runtime": "retrieval_v1", "agent.max_tool_calls": …, "user.id": workspace_id, "session.id": <ask_session_id если есть>, "agent.question": question})`.

**B. Tool-вызовы не видны.** `BaseAgentTool.run_with_trace` — отличное место, чтобы один раз обернуть **все** инструменты в `traced_tool_span(name, tool_name=self.name, tool_parameters=args_summary, tool_description=self.__doc__)`. Получаем TOOL-кинд + автоматический ввод/вывод/латенси/ошибки в Phoenix без правок каждого инструмента.

**C. Retrieval (Qdrant) не виден.** `IdeaSearchTool.run` делает эмбеддинг запроса + Qdrant `search_similar`. Это классический RETRIEVER. Нужен `chain_span("retrieval.qdrant", {...})` или, лучше, явный RETRIEVER-кинд (Phoenix распознаёт `openinference.span.kind = "RETRIEVER"` + `retrieval.documents.{i}.document.id|score|content`).

**D. LLM-вызовов в агенте сегодня нет** (агент детерминированный, `final_answer` — просто строка). Но как только Wave R / R+1 добавит LLM-планировщик / writer, нужно сразу шаблоном идти через `llm_span` + `SpanAttributes.set_llm_attrs(...)` — иначе повторим дыру `claims_extraction`.

**E. Phoenix не инициализирован в API-процессе.** Endpoint `/v1/agent/query` не вызывает `init_tracer_provider()`. Решение — сделать это **в startup приложения** (`fastapi.FastAPI(..., on_startup=[init_tracer_provider])` или через ASGI-lifespan), один раз на процесс. Это попутно закрывает риск «трассировка ingest зависит от того, попал ли поток через CLI-инициализацию».

### 3.6 Эмбеддинги — слепое пятно

`HashEmbeddingProvider` / `try_sentence_transformer` (sentence-transformers) — это и в ingestion, и в IR. Сегодня эмбеддинг-вызов нигде не оборачивается в спан. Для local-моделей (Sentence-Transformers) считать стоимость не нужно, но **полезно** видеть:

- `embedding.model_name`
- `embedding.dim`
- `embedding.input_count`
- `embedding.duration_ms`
- ошибки/fallback на hash-провайдер

Можно сделать тонкую обёртку `embeddings_span(name, model, dim, count)` рядом с `llm_span` — это и есть OpenInference EMBEDDING-кинд.

### 3.7 Шум и фильтрация

`PHOENIX_TRACE_SCOPE = extraction_llm` уже есть и работает — это сильно. Но он жёстко прибит к набору имён `_EXTRACTION_LLM_CHAIN_NAMES = {"ingest_document", "metadata_and_references_extraction"}`. Если переименуем спаны (см. §3.3.A), **scope сломается**. Нужно обновить набор и держать его рядом с переименованием.

---

## 4. Что мы уже делаем хорошо (не сломать рефакторингом)

| Практика | Где |
|---|---|
| Использование `openinference.span.kind` (CHAIN / LLM / TOOL) | `phoenix_tracer.py` (`chain_span`, `llm_span`, `traced_tool_span`) |
| Полный набор `llm.*` атрибутов (model, provider, system, temperature, max_tokens, токены) | `extractor.SyncInstructorExtractor.extract_maybe` |
| Определение провайдера из `base_url` (OpenRouter → openrouter) | `SpanAttributes._provider_from_base_url` |
| Flat-encoding `llm.input_messages.{i}.message.*` и `llm.output_messages.{i}.message.*` | `SpanAttributes._set_message_attributes` |
| Truncation длинных JSON-payload по `PHOENIX_SPAN_IO_MAX_LEN` | `SpanAttributes._safe_json` |
| `usage_source` (`api` / `estimated` / `estimated_error` / `estimated_maybe_error`) | `SpanAttributes.set_llm_token_counts(...)` |
| Fallback оценки токенов по тексту, когда `usage` пуст | `SpanAttributes.set_llm_token_counts_from_text` |
| Status = ERROR + `record_exception` при исключении в спане | `chain_span` / `llm_span` / `traced_tool_span` |
| Авто-инструментация OpenAI (опц.) | `_register_optional_openai_instrumentation` |
| Runtime-фильтр шума (`PHOENIX_TRACE_SCOPE = extraction_llm`) | `phoenix_trace_scope` + noop-обёртки |
| Однократная инициализация tracer-provider | `@lru_cache(maxsize=1) init_tracer_provider` |
| Стадийные спаны с DB-зеркалом метрик (`IngestJobStageOrm`) | `ingestion/stage_context.py` |

---

## 5. План работ — Wave X-Phoenix

Структура волны: **X1 — фиксы существующего ingest-tracing** (без новой архитектуры), **X2 — разметка IR / агента** (новый трек). Идут независимо, но рекомендуется делать X1 первым — он короче и сразу разблокирует точную атрибуцию стоимости по моделям из Settings.

### 5.1 Wave X1 — fix существующего ingest-tracing

**Цель:** все LLM-вызовы попадают в Phoenix как LLM-спаны с моделью и токенами, дерево фаз читается без подсказок, есть способ открыть конкретный ingest job в Phoenix.

#### Чеклист X1

- [x] **X1.1 VL PDF: довести `vl_pdf.chat_completions` до полноценного LLM-спана.**
  - В `science_graphrag/ingestion/vl_pdf.py::pdf_to_markdown` после получения `data`:
    - `SpanAttributes.set_llm_attrs(model=settings.vl_model, base_url=settings.vl_base_url, temperature=0.0, max_tokens=12000)`
    - `SpanAttributes.set_llm_invocation_parameters({"max_tokens": 12000, "pages": len(images), "dpi": settings.vl_dpi})`
    - `SpanAttributes.set_llm_input_messages([{"role": "user", "content": f"<{len(images)} image(s)> + prompt"}])` (без base64)
    - `SpanAttributes.set_llm_output_messages([{"role": "assistant", "content": markdown[:PHOENIX_SPAN_IO_MAX_LEN]}])`
    - Если `data.get("usage")` есть — `set_llm_token_counts(**usage, usage_source="api")`, иначе `set_llm_token_counts_from_text(prompt_text=DEFAULT_VL_PROMPT, completion_text=markdown)`.
  - Acceptance: в Phoenix Settings → Models в строке `qwen/qwen3-vl-235b-a22b-instruct` появляются ненулевые входные/выходные токены и стоимость.

- [x] **X1.2 Claims: обернуть LLM-вызов в `llm_span("llm.claims_extraction", …)`.**
  - В `science_graphrag/ingestion/pipeline.py` (или, лучше, внутри `extract_claims_llm`) обернуть `ext.extract_maybe(_ClaimsLLMResponse, …)` в `llm_span("llm.claims_extraction", {"document.id": doc_id, "work.id": work_id, "chunks": len(chunk_dicts)})`. Снаружи оставить `chain_span("ingest.extract_claims.llm", …)` с метриками (количество claim'ов, raw vs accepted) — как в metadata-блоке.
  - Acceptance: в Phoenix отдельный LLM-спан `llm.claims_extraction` с `llm.model_name = mistralai/mistral-small-3.2-24b-instruct`, токенами и стоимостью.

- [x] **X1.3 Унифицировать имена подспанов: префикс `ingest.<stage>.<substep>`.**
  - `pdf_to_markdown` → `ingest.parse_pdf.markdown` (внутри ставить атрибут `extraction_mode=vl|pypdf|cached`).
  - `metadata_and_references_extraction` → `ingest.extract_meta.metadata_and_refs`.
  - `openalex_enrichment` → `ingest.enrich_openalex.lookup`.
  - `semantic_method_dataset` → `ingest.write_graph.semantic`.
  - `claims_extraction` → `ingest.extract_claims.llm` (родитель `llm.claims_extraction`).
  - `qdrant_vector_upsert` → `ingest.embed.qdrant_chunks`; `qdrant_claims_upsert` → `ingest.embed.qdrant_claims`.
  - `fallback.metadata|authorships|authorships_probe|all_heuristic` → `ingest.<stage>.fallback.<reason>`.
  - **Не забыть** обновить `_EXTRACTION_LLM_CHAIN_NAMES` в `phoenix_tracer.py` (`{"ingest_document", "ingest.extract_meta.metadata_and_refs"}`).
  - Acceptance: дерево спанов читается линейно сверху вниз, scope `extraction_llm` по-прежнему оставляет только нужное.

- [x] **X1.4 Убрать обёртку `neo4j_graph_persistence` (split в три независимые стадии).**
  - В `pipeline.py` снять `with chain_span("neo4j_graph_persistence")`. Оставить `stage(ENRICH_ROR)`, `stage(WRITE_GRAPH)`, `stage(RESOLVE_REFERENCES)` как прямые детей `ingest_document`.
  - Внутри `WRITE_GRAPH` для крупных Neo4j-операций добавить локальные `chain_span("ingest.write_graph.upsert_work_layer1")` и (внутри claims-блока) `chain_span("ingest.extract_claims.upsert_claims")` с атрибутами `db.system="neo4j"`, `db.operation="merge"`, `writes.count=…`.
  - Acceptance: каждая стадия — на одном уровне дерева; в спанах Neo4j виден `db.system = "neo4j"`.

- [x] **X1.5 Поднять `ATTACH_WORKSPACE` под общий корень.**
  - Вариант A (предпочтительно): передать в `ingest_document(...)` параметр `attach_workspace_id` и выполнить attach как стадию **внутри** функции, до возврата из `chain_span("ingest_document")`.
  - Вариант B (минимум): обернуть всё тело `_execute_single_ingest` (от старта до пост-attach) в `chain_span("api.ingest_job", {"job.id": job_id, "workspace.id": workspace_id})`. Acceptance: в Phoenix `attach_workspace` лежит под общим корневым trace, а не отдельным root-спаном.

- [x] **X1.6 Корреляция trace ↔ ingest job (`session.id`, `user.id`, `metadata.*`).**
  - В `chain_span("ingest_document", attrs)` добавить `session.id = job_id` (через `OpenInferenceAttributes.SESSION_ID`), `user.id = workspace_id`, и плоские `metadata.workspace_id`, `metadata.job_id`, `metadata.parent_job_id`, `metadata.source_name`, `metadata.extraction_mode`, `metadata.embedding_model`, `metadata.extraction_llm_model`, `metadata.vl_model`.
  - В `IngestJobRecord(Orm)` добавить `phoenix_trace_id text NULL`, заполнять из `format(trace_api.get_current_span().get_span_context().trace_id, "032x")` сразу после открытия корневого спана. Migration через alembic.
  - Acceptance: в Phoenix → Sessions появляется по одному session per ingest-job; в `GET /v1/ingest/jobs/{id}` возвращается `phoenix_trace_id` и UI может построить ссылку «Открыть в Phoenix».

- [x] **X1.7 OpenAlex / Qdrant / Neo4j — DB/HTTP-конвенция.**
  - На `ingest.enrich_openalex.lookup`: `http.request.method="GET"`, `http.url="https://api.openalex.org/works/doi:..."`, `openalex.doi=…`, `openalex.found=true|false`, `retry.attempts=N`. Также `SpanAttributes.set_input({"doi": draft.doi})`, `set_output({"openalex_id": …, "title": …})`.
  - На `ingest.embed.qdrant_chunks` / `ingest.embed.qdrant_claims`: `db.system="qdrant"`, `db.collection.name=…`, `db.operation="upsert"`, `vector.dim=…`, `vector.count=…`.
  - На крупных Neo4j-write (см. X1.4): `db.system="neo4j"`, `db.operation="merge|delete"`, `writes.count=…`.
  - Acceptance: в Phoenix можно отфильтровать спаны по `db.collection.name = chunks` или `http.url contains "openalex"`.

- [x] **X1.8 Эмбеддинги: тонкий спан вокруг `embedder.embed(...)`.**
  - В `science_graphrag/ingestion/embeddings.py` (или в pipeline-местах вызова) добавить `embeddings_span(name, model, dim, count)` (новая обёртка в `phoenix_tracer.py`, ставит `openinference.span.kind = "EMBEDDING"`, `embedding.model_name`, `embedding.embeddings.{i}.embedding.text` опционально, `embedding.dim`, `embedding.input_count`).
  - Acceptance: в Phoenix UI вызовы Sentence-Transformers видны отдельной строкой, не теряются в `ingest.embed`.

- [x] **X1.9 FastAPI startup: `init_tracer_provider` один раз.**
  - В `science_graphrag/api/app.py` (или там, где собирается `FastAPI(...)`) на `lifespan` вызывать `init_tracer_provider()`. Убрать (или оставить для CLI) явные вызовы из `run_ingest_cli` / `run_ingest_batch_cli`.
  - Acceptance: `POST /v1/agent/query` и `POST /v1/ingest/...` шлют трейсы независимо от того, что было до этого в процессе.

- [x] **X1.10 Документация и тесты.**
  - Обновить `docs/architecture/observability-phoenix.md` (создать, если нет) с правилами наименования (`ingest.<stage>.<substep>`, `llm.<call>`, `agent.*`, `retrieval.*`) и контрактом атрибутов.
  - В `tests/observability/` (создать пакет) добавить smoke-тест: моделируем `ingest_document` на крошечном PDF, экспортируем спаны через `InMemorySpanExporter` (OTel SDK), проверяем, что у LLM-спанов есть `llm.model_name` и `llm.token_count.total`, у CHAIN — нет.
  - Acceptance: тест зелёный, регрессия по дырам §3.1 ловится статически.

### 5.2 Wave X2 — разметить retrieval agent (IR)

**Цель:** каждый запрос пользователя через `/v1/agent/query` виден в Phoenix как один trace с понятным деревом TOOL/RETRIEVER/LLM-спанов и сессией = `ask_session_id`.

#### Чеклист X2

- [ ] **X2.1 Корневой `agent.query` спан в `RetrievalAgent.run`.**
  - В `science_graphrag/agent/runtime.py::RetrievalAgent.run` обернуть тело в `chain_span("agent.query", {"agent.runtime": "retrieval_v1", "agent.max_tool_calls": max_tool_calls, "agent.question": question, "session.id": ask_session_id, "user.id": workspace_id})`.
  - На спан положить `SpanAttributes.set_input({"question": question, "workspace_id": workspace_id})` и `set_output({"answer_chars": …, "citations": …, "tool_calls": …})` в самом конце.
  - Acceptance: каждый POST `/v1/agent/query` появляется в Phoenix как один trace с CHAIN-кореннем.

- [ ] **X2.2 TOOL-спаны через `BaseAgentTool.run_with_trace`.**
  - В `science_graphrag/agent/tools/base.py::run_with_trace` обернуть `self.run(**kwargs)` в `traced_tool_span(f"tool.{self.name}", tool_name=self.name, tool_parameters=args_summary, tool_description=type(self).__doc__)`.
  - На результат — `SpanAttributes.set_output({"row_count": res.row_count, "truncated": res.truncated, "preview": <первые элементы res.payload>})`.
  - Acceptance: `idea_search`, `summarize_workspace`, `final_answer`, `entity_search`, `edge_search`, `cypher_query` появляются как TOOL-спаны под `agent.query` без правок каждого инструмента.

- [ ] **X2.3 RETRIEVER-кинд для `idea_search` (Qdrant).**
  - В `IdeaSearchTool.run` добавить внутренний `chain_span("retrieval.qdrant.idea_search")` со специальным атрибутом `openinference.span.kind = "RETRIEVER"` (через `set_span_attribute`) и `retrieval.documents.{i}.document.id|score|content`.
  - На спан также `embedding.model_name`, `embedding.dim`.
  - Acceptance: в Phoenix Trace UI «retrieval» виден как RETRIEVER, отображается список документов.

- [ ] **X2.4 EMBEDDING-спан для запроса.**
  - Использовать `embeddings_span(...)` из X1.8 для `self._embedder.embed([q])`.

- [ ] **X2.5 LLM-спан под будущий планировщик / writer (placeholder).**
  - Когда `final_answer` (или новый шаг) станет LLM-вызовом, обязательно идти через `llm_span("llm.agent.<step>", …)` + полный llm.* контракт. В этой волне закладываем шаблон в `agent/tools/final_answer.py` комментарием `# WAVE X2: wrap LLM call in llm_span(...)` чтобы не забыть.

- [ ] **X2.6 Корреляция с ask-session.**
  - В `api/agent.py::post_agent_query` принимать `session_id` (уже есть `ask_sessions`) и пробрасывать в `RetrievalAgent.run`. Если пришло — на root-спане `session.id = ask_session_id`. Иначе сгенерировать `uuid4()` per-request, чтобы Phoenix всё равно сгруппировал.
  - Acceptance: в Phoenix Sessions видна одна сессия per ask-session, в ней — несколько trace'ов (по одному на сообщение пользователя).

- [ ] **X2.7 phoenix_trace_id в ответе агента.**
  - В `AgentQueryResponse` добавить поле `phoenix_trace_id: str | None`, заполнять из текущего span context. UI может выводить кнопку «Открыть в Phoenix» рядом с ответом.

- [ ] **X2.8 Smoke-тест агента.**
  - В `tests/agent/` (или `tests/observability/`) добавить тест: запускаем `RetrievalAgent.run(...)` через `InMemorySpanExporter`, проверяем, что есть ровно один root `agent.query` (CHAIN), под ним — TOOL-спаны `tool.idea_search` и `tool.final_answer`, у TOOL-спана есть `tool.name` и `tool.parameters`.

---

## 6. Связь с другими волнами

- **Wave U (видимость стадий ingest без новой инфры)** из [`_archive/ingestion-async-pipeline-roadmap-2026-04-25.md`](./_archive/ingestion-async-pipeline-roadmap-2026-04-25.md): X1.6 (`phoenix_trace_id` в `ingest_jobs`) даёт ему «бесплатно» обратную ссылку из UI на Phoenix. Делать одной волной не нужно, но порядок: X1.6 → Wave U UI.
- **Wave W (Redis + Dramatiq)**: при выносе ingest в воркер OTel-контекст не пересекает границу процесса автоматически. На стороне отправителя нужно `inject` контекста в payload Dramatiq message, на стороне воркера — `extract` и `with trace_api.use_span(parent_ctx)`. В X1 это не входит, но **зафиксировать как риск** в Wave W перед стартом.
- **ADR 016 (LangGraph-style agent)**: когда runtime агента переедет на полноценный планировщик, X2.1 / X2.2 шаблон применим один в один — каждый «node» планировщика становится CHAIN-спаном, каждый tool — TOOL, каждый LLM-вызов — LLM. Хорошо войти в эту волну с уже разметкой X2.

---

## 7. Сводный чеклист по Wave X-Phoenix

### X1 — fix ingest-tracing

- [x] X1.1 VL PDF → полный LLM-контракт (model + tokens + I/O).
- [x] X1.2 `claims_extraction` → `llm_span("llm.claims_extraction")`.
- [x] X1.3 Унификация имён `ingest.<stage>.<substep>` + sync `_EXTRACTION_LLM_CHAIN_NAMES`.
- [x] X1.4 Убрать `neo4j_graph_persistence`, плюс DB-атрибуты на крупные write.
- [x] X1.5 `ATTACH_WORKSPACE` под общий root (или новый `api.ingest_job`).
- [x] X1.6 `session.id = job_id`, `user.id = workspace_id`, `metadata.*`, `phoenix_trace_id` в `ingest_jobs`.
- [x] X1.7 HTTP/DB-конвенция для OpenAlex / Qdrant / Neo4j.
- [x] X1.8 EMBEDDING-спан + `embeddings_span(...)` в `phoenix_tracer.py`.
- [x] X1.9 `init_tracer_provider` в FastAPI lifespan.
- [x] X1.10 Doc + `tests/observability/` smoke на наличие `llm.model_name` / `llm.token_count.total`.

### X2 — IR / agent observability

- [ ] X2.1 `chain_span("agent.query")` в `RetrievalAgent.run`.
- [ ] X2.2 TOOL-спаны через `BaseAgentTool.run_with_trace`.
- [ ] X2.3 RETRIEVER-кинд в `IdeaSearchTool` + `retrieval.documents.*`.
- [ ] X2.4 EMBEDDING-спан на эмбеддинг запроса.
- [ ] X2.5 Шаблон `llm_span("llm.agent.*")` в `final_answer` (placeholder).
- [ ] X2.6 Корреляция с `ask_session_id`.
- [ ] X2.7 `phoenix_trace_id` в `AgentQueryResponse`.
- [ ] X2.8 `tests/agent/` smoke на дерево `agent.query → tool.* / retrieval.*`.

### Acceptance уровня волны

- [ ] В Phoenix → Settings → Models у обеих кастомных моделей (`mistralai/mistral-small-3.2-24b-instruct`, `qwen/qwen3-vl-235b-a22b-instruct`) видны ненулевые токены и расчётная стоимость **на каждый ingest** одного PDF.
- [ ] В Phoenix → Sessions можно выбрать конкретный `job_id` и увидеть весь trace ingest как одну сессию.
- [ ] В Phoenix → Traces для одного `POST /v1/agent/query` есть один trace с корнем `agent.query` и видимыми tool/retrieval-спанами.
- [ ] При запуске `PHOENIX_TRACE_SCOPE=extraction_llm` остаётся ровно нужный набор LLM-спанов извлечения (с учётом новых имён).
- [ ] Регрессионный тест ловит исчезновение `llm.model_name` или `llm.token_count.total` у любого LLM-спана.

---
