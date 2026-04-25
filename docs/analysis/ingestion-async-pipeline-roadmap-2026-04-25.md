# Карта развития: асинхронный ingest, очередь и видимость стадий — Wave U–W

**Дата:** 2026-04-25
**Статус:** living working doc; новый infra-трек, не пересекается с benchmark/onthology-волнами M–T из [ontology-benchmarks-roadmap-2026-04-24.md](ontology-benchmarks-roadmap-2026-04-24.md).
**Цель:** убрать две конкретные боли локального стека ingestion (шум polling-логов и нулевая видимость стадии пайплайна) и подготовить почву для масштабирования: вынести долгую работу из процесса API в отдельный воркер на Redis + Dramatiq, перевести прогресс с `polling` на `SSE`, а сам пайплайн разметить явными стадиями с метриками.

**Что внутри:**

1. Симптомы и снимок текущей реализации.
2. Анализ опций: почему **Redis + Dramatiq**, почему **SSE**, почему **явная модель стадий**.
3. Wave U — видимость стадий без новой инфры (cheap wins).
4. Wave V — SSE-канал прогресса (без новой инфры).
5. Wave W — вынос ingest в отдельный воркер на Redis + Dramatiq.
6. Сводный чеклист по всем волнам.
7. Связь с существующими спеками и backlog.

**Связанные документы:**

| Документ | Что в нём |
|----------|-----------|
| [../architecture/phase-1-backbone.md](../architecture/phase-1-backbone.md) | Текущая модель данных Phase 1 (Postgres / Neo4j / Qdrant) |
| [../adr/001-phase1-stack.md](../adr/001-phase1-stack.md) | Выбор стека Phase 1 (фиксирует «без лишних сервисов» как принцип) |
| [../backlog/refactor-backend.md](../backlog/refactor-backend.md) | Структурный backlog, куда уходят отложенные пункты |
| [../backlog/refactor-frontend.md](../backlog/refactor-frontend.md) | UI-сторона backlog (для UI-кусков Wave U/V) |
| [../runbooks/roadmap-next-waves.md](../runbooks/roadmap-next-waves.md) | Сводный список волн (после принятия — добавить туда секции Wave U–W) |
| [../specs/frontend-ui-api-contracts-v1.md](../specs/frontend-ui-api-contracts-v1.md) | Контракты API, которые расширяем стадиями и SSE |

---

## 1. Симптомы и снимок

### 1.1 Что наблюдает пользователь

При запуске ingest одного PDF в access-логе API безостановочно сыпется:

```text
api-1 | INFO: 172.19.0.8:57628 - "GET /v1/ingest/jobs/<id> HTTP/1.1" 200 OK
api-1 | INFO: 172.19.0.8:57638 - "GET /v1/ingest/jobs/<id> HTTP/1.1" 200 OK
…
```

UI при этом показывает только статус `running` и фиксированное сообщение `Running pipeline (Neo4j / vectors / SQL)…` минутами; реальная стадия (PDF parse, chunking, embeddings, semantic extraction LLM, enrichment OpenAlex/ROR, claims, references, write Neo4j, attach workspace) **не наблюдаема**.

### 1.2 Что у нас сейчас в коде

- `science_graphrag/api/ingest_jobs.py` — `IngestJobRegistry` поверх `IngestJobRecordOrm` (Postgres), запуск работы через `threading.Thread(target=_run_ingest_thread, …)` **внутри процесса API**.
- Логи джобы — поле `logs TEXT` (truncated 48 KB), без структуры.
- Прогресс — два числа `progress_current / progress_total` + строка `message`.
- При рестарте API — `mark_stale_running_jobs_failed` помечает все `queued/running` как `failed`. **Долгая работа теряется.**
- UI — `ui/src/hooks/usePollJob.js`, `setInterval(2000)`, `GET /v1/ingest/jobs/{id}`, без `If-None-Match` / 304.
- Edge — `docker/nginx-web.conf`, проксирует `/` в `api`, без специальных настроек под streaming.

### 1.3 Две независимые боли (важно не смешивать)

1. **Доставка прогресса наружу** (шум polling) — про модель доставки `pull` vs `push`.
2. **Внутренняя видимость пайплайна** (на какой стадии) — про моделирование самой работы.

Очередь даёт **третий**, отдельный вопрос — durability и горизонтальное масштабирование, она полезна, но **не закрывает** ни (1), ни (2) сама по себе.

---

## 2. Анализ опций

### 2.1 Почему Redis + Dramatiq, а не Postgres-as-queue / Celery / Kafka

Альтернативы и их положение по критериям:

| Опция | Доп. сервисы | Сложность кода | Гарантии | Хорошо ещё для | Минус |
|-------|--------------|----------------|----------|-----------------|-------|
| **Redis + Dramatiq** | Redis (один) | низкая | at-least-once + ack + retry middleware | SSE pub/sub bus, кэш, rate-limit, дедуп LLM-вызовов | ещё один сервис |
| Postgres `SKIP LOCKED` (procrastinate) | — | средняя (DDL + воркер) | транзакционная связка с бизнес-данными | — | нет нативного pub/sub под SSE; PG `LISTEN/NOTIFY` имеет ограничения |
| Celery + Redis/RabbitMQ | Redis или RabbitMQ | высокая (много магии) | as Dramatiq, но больше кнопок | groups/chords | большой ops-хвост, сложно дебажить |
| RabbitMQ напрямую | RabbitMQ | высокая | строгие AMQP | routing/priority/DLQ | избыточен под одну семью задач |
| Kafka / Redpanda / NATS JetStream | брокер + ZK/raft | высокая | append-only log, replay | event sourcing, multi-consumer | overkill, нет нескольких потребителей |
| Temporal / Restate / Prefect | свой кластер | очень высокая | durable execution, sagas | многочасовые workflows | оправдается только когда пайплайн станет действительно длинным |

**Решение — Redis + Dramatiq.** Обоснование:

1. **Redis всё равно нужен скоро** для других задач: pub/sub-шина под SSE (одно событие — несколько подписчиков), кэш горячих retrieval, дедуп идемпотентных LLM-вызовов, rate-limit. Тащить Redis ради одной только очереди было бы дорого, но он окупается сразу несколькими функциями.
2. **Dramatiq** — современная, маленькая, с middleware для retry / age limit / time limit / message ack «из коробки», без неуправляемой магии Celery.
3. **SSE-шина**: один воркер пишет события `progress` в Redis pub/sub, API-инстанс читает и стримит подписчикам. Без Redis пришлось бы делать `LISTEN/NOTIFY` (с ограничениями на размер payload и фактически без backpressure) или периодически `SELECT` (вернёт нас к polling, только внутри сервера).
4. **Procrastinate** (Postgres-only) рассматривался серьёзно и **отказан** именно по пункту 3: SSE без отдельной шины аккуратно не сделать. При этом мы оставляем дверь: enqueue делаем в одной транзакции с записью job (см. Wave W §5.4), чтобы транзакционные плюсы Postgres-очереди не были потеряны.
5. **Celery** отказан как «слишком много операционного хвоста под нашу нагрузку».
6. **Kafka / Temporal** не имеют сейчас оправдания: нет нескольких потребителей одного события, нет многочасовых workflow с человеческими шагами.

> ⚠️ **Принцип `docs/adr/001-phase1-stack.md` («без лишних сервисов»)** в Wave W будет пересмотрен: фиксируем в новом ADR, что Redis добавлен как **многоцелевой компонент** (queue + pub/sub + cache), а не «просто очередь». Без этого обоснования добавлять сервис нельзя.

### 2.2 Почему SSE, а не WebSocket / long-poll / WebHook

| Способ | Направление | Сложность | Подходит для |
|--------|-------------|-----------|---------------|
| **SSE** | server → client | низкая (`sse-starlette`, нативный `EventSource` в браузере) | прогресс-стримы, нотификации |
| WebSocket | bi-directional | средняя (handshake, ping/pong, reconnection) | чаты, collaborative editing |
| HTTP polling | client → server | минимум | rare-update polling, fallback |
| HTTP long-polling | client → server | средняя | редкие апдейты при отсутствии WS |
| WebHook | server → server | низкая, но нужен публичный URL | server-to-server интеграции |

**Решение — SSE.** Прогресс джобы — строго **однонаправленный** поток; ack/cancel при необходимости отправляется обычными POST. SSE:

1. Идёт поверх обычного HTTP/1.1 — без отдельного протокола, не ломает текущие proxy.
2. `EventSource` в браузере умеет автоматический reconnect и `Last-Event-ID`.
3. Через `sse-starlette` интегрируется в FastAPI без побочного фреймворка.
4. WebSocket потребовал бы лишней сложности (handshake, прокси, heartbeat) ради того же одностороннего потока.
5. Polling остаётся как **fallback** — UI должен корректно деградировать, если SSE-соединение не поднялось (например, корпоративный proxy буферизует ответы).

> ⚠️ **Nginx (`docker/nginx-web.conf`)** для SSE-локации потребует `proxy_buffering off;` и увеличенного `proxy_read_timeout`. Это локальный override на отдельный location, не на весь upstream — см. чеклист Wave V.

### 2.3 Почему явная модель стадий обязательна (а не «улучшенный `message`»)

Без типизированных стадий **никакой формат доставки прогресса** (ни polling, ни SSE) не даст UI рисовать степпер «4/9: extracting claims (chunk 17/42)». Свободный `message: str` остаётся уделом отладки.

Минимальная модель:

```
ingest_job_stage(
  job_id, stage, status,
  started_at, finished_at,
  metrics_jsonb,  -- pages, chunks, tokens_in, tokens_out, llm_ms, …
  error
)
```

И enum `IngestStage`: `parse_pdf | chunk | embed | extract_meta | enrich_openalex | enrich_ror | extract_claims | resolve_references | write_graph | attach_workspace`.

Бонусы такой модели независимо от очереди и SSE:

- **OpenTelemetry-спан на стадию** — у нас уже поднят `phoenix:4317` (`docker-compose.yml`), трейс автоматически окажется в Phoenix. «Бесплатная» dev-observability.
- **Метрики per-stage** для бенчмарков ingestion (latency, token usage) — фундамент для будущих ablation runs.
- **Аккуратный fail/retry per stage** в Wave W (Dramatiq middleware будет видеть, на какой стадии упало).

---

## 3. Wave U — видимость стадий + тишина в логах (Phase 1, без новой инфры)

**Цель:** UI начинает показывать настоящую стадию пайплайна с метриками; access-лог перестаёт зашумляться polling-запросами. **Никаких новых сервисов.**

**Источник анализа:** §1, §2.3.

### 3.1 Backend

1. **Исключение polling-эндпоинтов из uvicorn access-лога.** Кастомный фильтр в `science_graphrag/api/main.py` (logging config или middleware): подавлять INFO для `GET /v1/ingest/jobs/*` и любых других `*/jobs/{id}` / `*/status` (perm-list путей). Ошибки (4xx/5xx) **продолжаем** писать.
2. **Модель стадий.**
   - Новая таблица `ingest_job_stage` (см. §2.3) + ORM `IngestJobStageOrm`.
   - Enum `IngestStage` в `science_graphrag/ingestion/__init__.py` (или `stages/__init__.py`).
   - Контекст-менеджер `with stage(job_id, IngestStage.EMBED) as st: st.metric("chunks", n)` — фиксирует начало/конец/исключение, обновляет строку.
3. **Размечаем `pipeline.py`.** Каждый блок `extract_stages_llm_first`, `chunking`, `embeddings`, `enrichment.openalex`, `enrichment.ror`, `claims.extractor`, `stages.references`, `Neo4jGraphStore.upsert_*`, `workspace_add_work` оборачивается соответствующим `with stage(...)`.
4. **OTel-спан per stage.** В контекст-менеджере открываем `tracer.start_as_current_span(f"ingest.{stage.value}")` с атрибутами `job_id`, `workspace_id`. Если `SCIENCE_GRAPHRAG_OTEL_*` уже экспортируется — спаны автоматически летят в Phoenix.
5. **Расширение `IngestJobView`.** Поле `stages: list[IngestStageView]` (упорядоченно) с `name | status | started_at | finished_at | duration_ms | metrics`. `progress_current` остаётся для обратной совместимости, но вычисляется из числа закрытых стадий.
6. **Backward compat:** старый `logs: str` сохраняем (как сырой буфер для отладки), не основной источник для UI.

### 3.2 Frontend

1. **Компонент `IngestStageStepper`** (`ui/src/components/ingestion/`): рендерит вертикальный/горизонтальный степпер из `job.stages`, с активной стадией, метриками (`chunks: 42`, `llm_ms: 12 340`) и индикатором ошибки.
2. **`WorkspacePage` ingestion card** перестаёт показывать длинную полосу `[11:04:39] Saved 1717390 bytes …` как основной контент; вместо неё — степпер, а лог-выхлоп уезжает под раскрываемый `Details`.
3. Обновить `usePollJob.js` минимально: `intervalMs = 1500` пока статус `running` и **смежная стадия** не сменилась (или оставить 2000 — finalize в Wave V вместе с SSE).

### 3.3 Тесты

1. Unit на `with stage(...)` — корректно фиксирует `failed` при exception, `completed` при успехе, метрики мерджатся.
2. API smoke `tests/test_api_smoke.py::test_get_ingest_job_returns_stages` — после моков пайплайна отвечает массивом стадий.
3. UI snapshot `IngestStageStepper.test.jsx` — рендер с тремя статусами стадий.

### 3.4 Чеклист Wave U

- [ ] Logging filter скрывает INFO `/v1/ingest/jobs/*`; ошибки видны.
- [ ] ORM `IngestJobStageOrm` + Alembic-миграция (см. ADR в Wave W §5.1 на тему миграций — здесь применяется уже существующий механизм `init_db`).
- [ ] Enum `IngestStage` покрывает 10 стадий из §2.3.
- [ ] Контекст-менеджер `stage(...)` с OTel-интеграцией.
- [ ] `pipeline.py` размечен; в каждой стадии — минимум одна метрика.
- [ ] `IngestJobView.stages` в API; обратная совместимость по `progress_*` и `logs` сохранена.
- [ ] UI `IngestStageStepper` отрисован на WorkspacePage; в скриншоте секции «Загрузка статьи» виден список стадий с метриками.
- [ ] Backend pylint + isort + black (`backend-quality.mdc`); UI `npm run lint` + unit-тесты зелёные.
- [ ] Запись в [backlog/refactor-backend.md](../backlog/refactor-backend.md) **закрыта**: «[DONE] Stage timeline for ingest jobs».

**Exit:** при ingest одного PDF в UI видны 10 стадий со статусами и метриками; в access-логе нет периодических `GET /v1/ingest/jobs/*`; при ошибке на любой стадии видно, на какой именно (с краткой ошибкой).

---

## 4. Wave V — SSE-канал прогресса джобы (Phase 1, без новой инфры)

**Цель:** UI получает прогресс push'ем без 2-секундной задержки и без поллинга; одно соединение на джобу. Polling остаётся как fallback. **Новых сервисов всё ещё нет.**

**Источник анализа:** §1, §2.2.

### 4.1 Backend

1. **`sse-starlette`** добавить в `pyproject.toml` (`science-graphrag` deps).
2. **In-process event bus** для Wave V: простой `asyncio.Queue` per `job_id` в `science_graphrag/api/ingest_event_bus.py`. Контракт публикации:
   ```python
   bus.publish(job_id, IngestEvent(kind="stage", stage="embed", status="started", metrics={…}))
   ```
   Контракт подписки:
   ```python
   async for event in bus.subscribe(job_id, last_event_id=None): …
   ```
   Это **временное** in-process решение — будет заменено на Redis pub/sub в Wave W §5.5 (контракт остаётся тем же, меняется только реализация).
3. **Эндпоинт** `GET /v1/ingest/jobs/{job_id}/events` (`router` в `ingest_jobs.py`):
   - `EventSourceResponse` от `sse-starlette`.
   - Поддержка `Last-Event-ID` (повторно отдавать события > id из БД-таблицы `ingest_job_event` либо хотя бы текущий снимок `stages`).
   - Heartbeat `ping` каждые 15 секунд (требует nginx-настройки, см. ниже).
   - Завершение стрима после `status in (completed, failed)` + финальное событие `terminal`.
4. **Источник событий** — контекст-менеджер `stage(...)` из Wave U: `__enter__` публикует `stage_started`, `__exit__` — `stage_finished` или `stage_failed`. Никаких новых вызовов в `pipeline.py` не нужно, они автоматические.
5. **Persisted snapshot:** для replay через `Last-Event-ID` сохраняем события в `ingest_job_event(job_id, seq, kind, payload_jsonb, ts)`. Достаточно последних N за джобу (или TTL = `finished_at + 24h`).

### 4.2 Edge / nginx

1. **`docker/nginx-web.conf` и `docker/nginx-web.dev.conf`** — добавить отдельный `location ~ ^/v1/ingest/jobs/.+/events$`:
   ```nginx
   proxy_pass http://api:8787;
   proxy_http_version 1.1;
   proxy_set_header Connection '';
   proxy_buffering off;
   proxy_cache off;
   proxy_read_timeout 1h;
   chunked_transfer_encoding on;
   ```
2. Smoke-тест: `curl -N` через nginx должен видеть события **сразу** (не «копит» 4 KB).

### 4.3 Frontend

1. **Новый хук `useJobStream(jobId, { onEvent, onTerminal, fallbackPollMs })`:**
   - Открывает `EventSource('/v1/ingest/jobs/' + jobId + '/events')`.
   - При `error` событии **3 раза подряд** или в Safari (нет SSE через некоторые корпоративные proxy) — закрывает SSE и подключает `usePollJob`.
   - При reconnect передаёт `Last-Event-ID` (браузер сам).
2. WorkspacePage / Ingestion card подключается через `useJobStream`. `usePollJob` остаётся как named export, не удаляется.
3. UI должен корректно отрисовывать промежуточные события стадий (мерджить в массив, не перерисовывать всё).

### 4.4 Тесты

1. API smoke: `tests/test_api_smoke.py::test_ingest_job_events_stream_yields_stage_events` через `httpx.AsyncClient` + `aread` SSE chunks.
2. Unit на `IngestEventBus` — fan-out нескольким подписчикам, корректное завершение очереди.
3. UI: `useJobStream.test.jsx` — мок `EventSource` (jsdom не имеет нативного — поднимаем минимальный stub), сценарий reconnect → fallback polling.
4. Manual smoke: открыть две вкладки на одну джобу → обе получают одинаковые события.

### 4.5 Чеклист Wave V

- [x] `sse-starlette` в зависимостях; `IngestEventBus` (in-process) реализован.
- [x] `GET /v1/ingest/jobs/{id}/events` отвечает `text/event-stream`, поддерживает `Last-Event-ID`, heartbeat 15s.
- [x] Таблица `ingest_job_event` для replay; TTL/cleanup.
- [x] nginx prod + dev конфиги имеют SSE-friendly `location`; smoke `curl -N` через `:8787` показывает мгновенный chunk.
- [x] UI `useJobStream` с graceful fallback на polling; `WorkspacePage` использует его.
- [x] Smoke + unit-тесты (backend и UI) зелёные.
- [x] Backend pylint + isort + black; UI lint + tests.
- [x] Запись в [backlog/refactor-backend.md](../backlog/refactor-backend.md) обновлена: Wave U/V отмечены как выполненные (`[PARTIAL]`, Wave W остаётся открытым).

**Exit:** при открытом окне ingestion в browser DevTools на одну джобу — **одно** долгое HTTP-соединение `/events` вместо `setInterval(2000)`; access-лог чист; при reload вкладки события «доезжают» с момента последнего `Last-Event-ID`; при принудительном закрытии SSE (например, отключив сеть на 30 секунд) UI автоматически переходит на polling и обратно.

---

## 5. Wave W — Redis + Dramatiq воркер (Phase 1 → Phase 2 grade)

**Цель:** ingest исполняется в **отдельном процессе** на отдельной очереди; рестарт API больше не убивает работу; SSE-шина становится cross-process (несколько API-инстансов получают события от одного воркера). **Добавляются два сервиса в compose:** `redis` и `worker`.

**Источник анализа:** §1, §2.1.

### 5.1 ADR + спека

1. **ADR `docs/adr/0XX-ingest-worker-redis.md`** (свободный номер по `docs/adr/README.md`):
   - Контекст: Wave U/V исчерпали полезные дешёвые меры; ingest в потоке внутри API ограничивает горизонтальное масштабирование и теряет работу при рестарте.
   - Решение: Dramatiq + Redis. Redis также берёт на себя SSE pub/sub bus (Wave V §4.1) и горячий кэш (на горизонте — rate-limit, дедуп LLM-вызовов).
   - Альтернативы (см. таблицу §2.1) и почему отказаны.
   - Влияние на `adr/001-phase1-stack.md`: Redis перестаёт быть «лишним», переходит в core stack.
2. **Спека `docs/specs/ingest-worker-v1.md`:** очереди, формат сообщений, retry policy, idempotency keys, heartbeat, drain on shutdown, бэкенд для results (Postgres `ingest_job` уже есть, results туда же).

### 5.2 docker-compose

```yaml
redis:
  image: redis:7-alpine
  command: ["redis-server", "--appendonly", "yes", "--maxmemory", "512mb", "--maxmemory-policy", "allkeys-lru"]
  ports:
    - "16379:6379"
  volumes:
    - redis_data:/data
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 20s
    timeout: 5s
    retries: 5

worker:
  build: { context: ., dockerfile: Dockerfile }
  command: ["python", "-m", "science_graphrag.worker"]
  env_file: [.env]
  environment:
    SCIENCE_GRAPHRAG_REDIS_URL: redis://redis:6379/0
    # … те же DATABASE_URL / NEO4J_URI / QDRANT_URL / BLOB_ROOT, что у api
  volumes:
    - ./data/blobs:/data/blobs
    - ./data/artifacts:/data/artifacts
  depends_on:
    api: { condition: service_healthy }   # или непосредственно postgres/neo4j/qdrant
    redis: { condition: service_healthy }
```

API-сервис тоже получает `SCIENCE_GRAPHRAG_REDIS_URL`.

### 5.3 Backend: Dramatiq actor

1. `science_graphrag/worker/__init__.py` — `dramatiq.set_broker(RedisBroker(url=…))` + middleware (`Retries(max_retries=2)`, `AgeLimit(max_age=3*60*60*1000)`, `TimeLimit(time_limit=60*60*1000)`).
2. `@dramatiq.actor(queue_name="ingest", max_retries=2)` `def ingest_document_actor(job_id: str)`:
   - Загружает settings, читает запись `IngestJobRecordOrm` по `job_id` (workspace_id, путь к blob).
   - Делегирует в существующую функцию `_execute_single_ingest(job_id, temp_path, settings)`.
   - На каждой стадии (через контекст-менеджер из Wave U) публикует event в **Redis pub/sub** канал `ingest:events:<job_id>` (в дополнение к persist в Postgres).
3. **`IngestEventBus` v2:** реализация поверх `redis.asyncio` `pubsub`. Контракт остаётся как в Wave V; in-process реализация удаляется. SSE-эндпоинт API подписывается на Redis-канал.
4. **Идемпотентность:** входной аргумент актора — только `job_id`; полезная нагрузка (PDF) уже на диске (`/data/blobs` либо `/tmp`), доступна обоим контейнерам через примонтированный volume. Повторный запуск того же `job_id` определяется по уже закрытым стадиям (контекст-менеджер `stage()` пропускает `status="completed"`). Это позволяет Dramatiq спокойно ретраить.

### 5.4 API: только enqueue

1. `start_ingest_job` / `start_batch_ingest_job` теперь:
   - Создают `IngestJobRecordOrm` (`status="queued"`).
   - Записывают blob на диск.
   - **В одной транзакции с записью job** вызывают `ingest_document_actor.send(job_id)` — для транзакционной связки делаем outbox-паттерн «лайт»: `INSERT INTO ingest_outbox(job_id) … ; COMMIT;`, а отдельный фоновый scanner (внутри API или worker) пушит outbox в Redis. Альтернатива — соглашаться на «at-most-once enqueue» с компенсацией: при старте worker сканирует `status='queued' AND created_at < now()-30s` и подбирает потерянные. **Решение принимаем в ADR §5.1; по умолчанию — компенсационный sweep**, проще и достаточно надёжно для Phase 1.
2. `mark_stale_running_jobs_failed` **удаляется** — рестарт API больше не должен трогать чужие джобы.
3. `threading.Thread` исчезает из `ingest_jobs.py`.

### 5.5 Observability

1. Прометеевские метрики (если уже включены в Phase 1, иначе оставляем как backlog) от Dramatiq middleware: `dramatiq_messages_total{actor,status}`, `dramatiq_message_duration_seconds`.
2. OTel-спаны от Wave U продолжают работать; добавляется родительский span `dramatiq.process_message` (через готовое middleware `dramatiq-otel`).

### 5.6 Тесты

1. **Unit:** `ingest_document_actor` с моками pipeline → корректно публикует stage events в bus.
2. **Integration (новая фикстура):** docker-compose.test поднимает `redis`, `postgres`, `neo4j`, `qdrant`, `worker`, `api`; pytest посылает PDF в `POST /v1/workspaces/{id}/ingest/document`, открывает SSE, ждёт `terminal` событие, проверяет, что в Neo4j и Qdrant записи появились.
3. **Resilience-тест:** убить контейнер `worker` в момент стадии `embed`, поднять заново → джоба завершается через retry (вторая итерация `ingest_document_actor.send`); finished, без duplicate writes.
4. **API restart test:** убить `api` посреди ingest → новый `api` поднимается, открытое SSE-соединение от UI повторно подключается, события продолжают идти от `worker` через Redis.

### 5.7 Документация

1. Обновить `docs/architecture/phase-1-backbone.md` — добавить `redis`, `worker` в схему сервисов.
2. Обновить `docs/runbooks/deploy.md` — порядок старта (`redis` перед `worker`), procedure drain (`SIGTERM` → Dramatiq дорабатывает текущее сообщение, `max_age` ограничивает таймаут).
3. Обновить `docs/runbooks/backup.md` — Redis AOF-снапшоты не являются source-of-truth (job state в Postgres), но события `ingest_job_event` рекомендуется бэкапить.
4. **Записать**: «Wave A–H были разработаны до выноса воркера; некоторые runbook-команды CLI больше не делают ingest синхронно — теперь enqueue → poll/SSE». Это требует пересмотра `science-graphrag` CLI смок-команд, у которых был прямой вызов pipeline.

### 5.8 Чеклист Wave W

- [ ] ADR принят, спека `docs/specs/ingest-worker-v1.md` зафиксирована.
- [ ] `redis` и `worker` в `docker-compose.yml` и `docker-compose.dev.yml`; healthchecks проходят.
- [ ] `dramatiq[redis]` (или эквивалент) в `pyproject.toml`; `science_graphrag.worker` модуль с broker + middleware.
- [ ] `ingest_document_actor` реализован; идемпотентен по `job_id`; ретраи через Dramatiq.
- [ ] API только enqueue'ит; `threading.Thread` удалён из `ingest_jobs.py`; `mark_stale_running_jobs_failed` удалён.
- [ ] Compensation sweep для `queued`-задач старше N секунд в worker startup.
- [ ] `IngestEventBus` v2 поверх Redis pub/sub; SSE-эндпоинт работает с двумя API-инстансами.
- [ ] Integration-тест end-to-end на compose; resilience-тест на убитый воркер; API restart test.
- [ ] Документация: phase-1-backbone, deploy, backup обновлены.
- [ ] Backend pylint + isort + black; UI без изменений (Wave V уже отвечает за UI-сторону).
- [ ] Записи в [backlog/refactor-backend.md](../backlog/refactor-backend.md) **закрыты**: «[DONE] Тише access-лог», «[DONE] Stage timeline», «[DONE] SSE-канал», «[DONE] Вынести ingest в отдельный воркер на Redis-очереди».

**Exit:** на compose stack `api` можно убить и поднять заново посреди ingest — джоба продолжает идти; rebuild только `worker` достаточен для итерации по pipeline; в Phoenix виден трейс с верхним span'ом `dramatiq.process_message` и подспанами стадий.

---

## 6. Сводный чеклист по всем волнам

| Wave | Item | Уровень | Acceptance |
|------|------|---------|------------|
| **U** | Filter polling из uvicorn access-лога | Backend | `/v1/ingest/jobs/*` не пишутся в INFO; ошибки видны |
| **U** | `IngestJobStageOrm` + enum `IngestStage` (10 стадий) | Backend | миграция + ORM + unit |
| **U** | Контекст-менеджер `stage(...)` + OTel-спан | Backend | спан виден в Phoenix; unit на success/failure |
| **U** | Разметка `pipeline.py` всеми 10 стадиями | Backend | каждая стадия публикует ≥ 1 метрику |
| **U** | `IngestJobView.stages` + backward-compat `progress_*`, `logs` | API | smoke `tests/test_api_smoke.py::test_get_ingest_job_returns_stages` |
| **U** | UI `IngestStageStepper` + интеграция в `WorkspacePage` | UI | snapshot test; ручной скриншот «Загрузка статьи» |
| **V** | `sse-starlette` + `IngestEventBus` (in-process) | Backend | unit на fan-out |
| **V** | `GET /v1/ingest/jobs/{id}/events` + `Last-Event-ID` + heartbeat 15s | API | smoke на streaming chunks |
| **V** | Таблица `ingest_job_event` для replay | Backend | TTL/cleanup |
| **V** | nginx prod + dev `location` под SSE (`proxy_buffering off`, 1h timeout) | Edge | `curl -N` через `:8787` отдаёт мгновенно |
| **V** | UI `useJobStream` + graceful fallback на polling | UI | unit + manual two-tab |
| **W** | ADR `0XX-ingest-worker-redis` + спека `ingest-worker-v1` | Docs | ADR принят |
| **W** | `redis`, `worker` в compose + healthchecks | Infra | `docker compose up -d` зелёный |
| **W** | `ingest_document_actor` (Dramatiq) + middleware retry/age/time-limit | Backend | unit + integration |
| **W** | Идемпотентность по `job_id`; compensation sweep `queued`-задач | Backend | resilience-тест на убитый воркер |
| **W** | API только enqueue; `threading.Thread` удалён | Backend | API restart test |
| **W** | `IngestEventBus` v2 на Redis pub/sub | Backend | two-API smoke |
| **W** | OTel: span `dramatiq.process_message` поверх стадий | Observability | трейс в Phoenix |
| **W** | Обновить `phase-1-backbone.md`, `deploy.md`, `backup.md` | Docs | актуальные диаграммы и runbook |

---

## 7. Связь с существующими спеками и backlog

При начале каждой волны обновить:

1. [runbooks/roadmap-next-waves.md](../runbooks/roadmap-next-waves.md) — добавить секции Wave U, V, W (по образцу I–L; со ссылкой на этот документ как «источник анализа»).
2. [backlog/refactor-backend.md](../backlog/refactor-backend.md) — после прохождения каждого пункта: переводить запись из `[OPEN]` в `[DONE]` с одной строкой-нотой.
3. [backlog/refactor-frontend.md](../backlog/refactor-frontend.md) — добавить запись «UI: переход с `usePollJob` на `useJobStream` для ingest» (Wave V) и держать её `[OPEN]` до прохождения Wave V exit.
4. [adr/001-phase1-stack.md](../adr/001-phase1-stack.md) — после Wave W обновить «Local stack» секцию: Redis + worker как core-сервисы; этот ADR не отзывается, дополняется ссылкой на новый ADR Wave W.
5. [architecture/phase-1-backbone.md](../architecture/phase-1-backbone.md) — после Wave U добавить блок «Job model: stages timeline»; после Wave W — `redis` и `worker` в схему.
6. [specs/frontend-ui-api-contracts-v1.md](../specs/frontend-ui-api-contracts-v1.md) — после Wave U фиксируем расширение `IngestJobView`; после Wave V — контракт SSE-эндпоинта (`event: stage_started | stage_finished | stage_failed | terminal | ping`, payload-формат).

---

## 8. Что **не** делаем сейчас (важные «нет»)

Чтобы скоуп не растёкся:

- **Celery / Kafka / Temporal** — не рассматриваем до явного триггера (см. таблицу §2.1).
- **Воркер без Redis (procrastinate)** — отказан из-за SSE bus (см. §2.1).
- **WebSocket вместо SSE** — отказан по принципу «не вводить bi-directional, если поток односторонний» (§2.2).
- **Multi-host API в Phase 1** — не цель Wave W; задача — durability при рестарте + отдельный процесс. Multi-host остаётся в backlog до явной нагрузочной потребности.
- **Per-stage retry для всего pipeline** — Wave W даёт retry **всей джобы**; per-stage retry с saga-компенсациями — отдельная Wave когда (если) появится Temporal-кандидатура.
- **Замена Postgres-job-store на Redis** — нет: `IngestJobRecordOrm` остаётся source-of-truth, Redis — только транспорт и pub/sub.

---

## 9. Порядок исполнения и зависимости

```
Wave U (видимость, неделя)   ──►   Wave V (SSE, неделя)   ──►   Wave W (Redis+воркер, 2-3 недели)
       │                                  │                              │
       └─ запись стадий в БД              └─ контракт IngestEventBus     └─ замена реализации bus
          + UI степпер                       (in-process)                   на Redis pub/sub
```

Wave U **обязателен** перед V (без модели стадий нечего стримить). Wave V **желателен, но не строго обязателен** перед W: можно начать W раньше, но тогда придётся дважды менять UI-сторону. Рекомендация — **U → V → W подряд**, не параллелить.
