# Roadmap: science-graphrag

Документ задаёт **управленческий и технический план** создания проекта GraphRAG для помощи учёному при работе с литературой, генерации гипотез и навигации по исследованиям. Он дополняет и структурирует материал из [idea.md](idea.md).

**Статус:** living document — обновлять по мере реализации фаз.

---

## 1. Контекст и продуктовая цель

### 1.1. Проблема

Исследователю нужно не только «найти статьи», но и:

- связывать методы, данные, результаты и теории;
- видеть пробелы и противоречия в литературе;
- опираться на **трассируемые** утверждения с привязкой к источникам.

### 1.2. North star

Система помогает учёному в:

- **навигации** по корпусу и цитированию;
- **синтезе** знаний из нескольких работ с цитатами и provenance;
- **поиске противоречий и открытых вопросов**;
- **поддержке генерации идей** (гипотезы, комбинации методов, перенос между областями) — с явным разложением на утверждения и свидетельства.

### 1.3. Принципы (из idea.md)

- Не строить «идеальную онтологию науки» сразу — использовать **многоуровневую рабочую схему**: библиографический слой → семантический → эпистемический → слой идей.
- Каждая важная научная сущность должна быть **привязана к источнику**; идеи должны быть **разложимы до утверждений и доказательств**.
- LLM — **extractor и генератор кандидатов**; каноническая правда по метаданным и идентификаторам — через **внешние реестры** (OpenAlex, Crossref, ORCID, ROR и т.д.), см. [idea.md §7](idea.md).

---

## 2. Стратегия реализации: greenfield vs копирование

| Подход | Суть | Решение для science-graphrag |
|--------|------|------------------------------|
| **Copy-first** | Скопировать репозиторий-аналог и заменить фронт, онтологию, benchmarks | **Не выбрано** — высокий риск перетащить доменно-специфичные решения и технический долг. |
| **Greenfield + selective reuse** | Новый проект с нуля; из референса брать **паттерны**, документацию, идеи архитектуры | **Выбрано** — явное проектирование scholarly-онтологии, extraction и UX под исследователя. |

**Референсный проект:** [osint-gr](/home/roman/pyprojects/ML/Prod/osint-gr) — зрелая структура docs, ADR, benchmark families, testing strategy, CI/gates. Использовать как **образец процессов и разбиения подсистем**, не как источник прямого копирования кода доменного слоя.

---

## 3. Целевая архитектура (верхний уровень)

```mermaid
flowchart LR
    subgraph ingest [Ingestion]
        PDF[PDF_FullText]
        NORM[Normalization]
        EXT[Extraction_Stages]
        ENR[External_Enrichment]
    end
    subgraph stores [Stores]
        BLOB[Blobs]
        META[Relational_Metadata]
        G[Graph_DB]
        V[Vector_DB]
    end
    subgraph query [Query_Time]
        RET[Retrieval]
        TRA[Graph_Traversal]
        SYN[Synthesis_Grounded]
    end
    subgraph ui [Frontend]
        WS[Workspace]
        RE[Reader_Evidence]
    end
    PDF --> NORM --> EXT --> ENR
    EXT --> BLOB
    EXT --> META
    ENR --> G
    EXT --> G
    RET --> G
    RET --> V
    TRA --> G
    RET --> SYN
    TRA --> SYN
    SYN --> ui
    META --> ui
```

**Слои данных (логически):**

1. **Scholarly backbone** — `Work`, `Author`, `Institution`, `Venue`, `Authorship`, цитирование, версии работ.
2. **Scientific semantic layer** — темы, задачи, методы, концепты, сущности предметной области, модели.
3. **Epistemic / claims layer** — утверждения, ограничения, конфликты, открытые вопросы (после стабилизации слоёв 1–2).
4. **Ideation layer** — гипотезы, комбинации, пробелы (опционально, post-MVP).

Подробная модель первого слоя и каскад промптов — в [idea.md](idea.md).

---

## 4. Матрица переиспользования: osint-gr

| Подсистема | Действие | Комментарий |
|------------|----------|-------------|
| Документация: `docs/architecture`, `docs/adr`, roadmap, policies, runbooks | **Reuse (паттерн)** | Воспроизвести структуру каталогов и дисциплину ADR под science-domain. |
| Разделение benchmark families (KG / IR / stream / gates) | **Reuse (паттерн)** | Адаптировать таксономию под scholarly сценарии (см. §8). |
| Testing strategy: unit / integration / smoke, merge-blocking subset | **Reuse (паттерн)** | Определить свои маркеры и gates под наличие инфраструктуры. |
| Docker / compose: граф + вектор + SQL + объекты | **Adapt** | Тот же класс стека часто уместен; конкретные сервисы и версии — решение проекта. |
| FastAPI shell, auth, middleware | **Adapt** | Каркас HTTP — по необходимости; доменные роуты — новые. |
| Agent orchestration, subagents, tool registry | **Adapt** | Идея «оркестратор + инструменты» переносима; инструменты — literature/graph/citation, не OSINT-case. |
| Онтология, extractors, KG models | **Rebuild** | Полная замена под scholarly graph (Work, Claim, Method, …). |
| Frontend: чат и расследовательский UI | **Rebuild** | UX под **исследовательский workflow** (корпус, чтение, граф, доказательства), не копировать сценарии расследования. |
| Benchmark fixtures и eval-кейсы | **Rebuild** | Новые корпуса, JSON-кейсы, эталоны под извлечение и RAG. |

---

## 5. Фазы разработки

Для каждой фазы ниже: **цель**, **артефакты**, **риски**, **критерии выхода (exit criteria)**.

### Phase 0 — Product frame и фундамент репозитория

**Цель:** зафиксировать scope MVP, north star и минимальную структуру репозитория и документации.

**Deliverables:**

- Краткий PRD или раздел в README: пользователи, сценарии, non-goals MVP.
- Каркас `docs/`: `architecture/`, `adr/`, ссылка на этот roadmap и на [idea.md](idea.md).
- Decision log (ADR-000 или `docs/adr/000-greenfield-strategy.md`): greenfield + selective reuse от osint-gr.

**Риски:** размытый MVP → расползание scope. **Митигация:** явный список «не в MVP».

**Exit criteria:** согласованы структура репо, north star, список модулей (ingestion, graph, retrieval, API, UI, eval).

**Статус Phase 0:** закрыта (2026-03-30): см. корневой [README.md](../README.md), [docs/README.md](README.md), [adr/000-greenfield-strategy.md](adr/000-greenfield-strategy.md), каталоги модулей в корне репозитория.

---

### Phase 1 — Scholarly backbone и ingestion MVP

**Цель:** рабочая вертикаль «документ → нормализация → метаданные/авторы/ссылки → обогащение → граф цитирования».

**Deliverables (по факту реализации):**

| Статус | Что |
|--------|-----|
| **Сделано** | Граф первого слоя в Neo4j: `Work`, `Authorship`, `Author`, `Institution`, `Venue`, `CITES`, `PUBLISHED_IN`, `HAS_AUTHORSHIP`, `OF_AUTHOR`, `AFFILIATED_WITH` — см. [adr/002-layer1-graph-model.md](adr/002-layer1-graph-model.md). |
| **Сделано** | Ingestion: PDF/text/markdown → `article.md` → нормализация → **LLM-first** извлечение `WorkDraft` / `AuthorshipDraft` / `ReferenceDraft` с эвристическим fallback (`science_graphrag/ingestion/llm/stage_extraction.py`). |
| **Сделано** | Task-aware **document slices** (front matter, references scope) для промптов Layer 1; **section-aware chunks** + Qdrant; см. [architecture/chunking-strategy.md](architecture/chunking-strategy.md), [adr/003-chunking-and-dedup-strategy.md](adr/003-chunking-and-dedup-strategy.md). |
| **Сделано** | Рёбра **`CITES`**: по DOI (OpenAlex при успехе), иначе по **`arxiv_id`**, иначе по паре **title + year** (`title_fingerprint`) — см. `science_graphrag/ingestion/pipeline.py`. |
| **Сделано** | Обогащение реестром: **OpenAlex** по DOI для основной работы и для цитируемых с DOI. |
| **Сделано** | Хранилища: blobs, Postgres (`documents`, `ingestion_runs`), Neo4j, Qdrant; артефакты `article.md` + `extraction_diagnostics.json`. |
| **Частично** | Canonical ID / **dedup для `Work`** (DOI, arXiv, fingerprint) — без полного merge-каталога между корпусами. |
| **Частично** | **Author / Institution**: `:Author` с детерминированным id по нормализованному имени (одно написание → один узел между работами); `Institution.ror_id` — опционально через ROR API при `SCIENCE_GRAPHRAG_ROR_LOOKUP_ENABLED=true`. |
| **Частично** | Ребро **`RELATED_VERSION_OF`**: журнальный DOI + arXiv в OpenAlex `ids` → связь опубликованной работы с preprint-узлом. |
| **Сделано** | **Batch/corpus ingest**: `science-graphrag ingest-corpus <dir>` (рекурсивно `.pdf`/`.md`/`.txt`) и пост-аудит кластеров дублей `Work` по DOI / OpenAlex / fingerprint / arXiv в Neo4j. |
| **Отложено** | Интеграции **Crossref**, **ORCID** как отдельные клиенты; полноценный ROR-каталог и merge институций между корпусами. |

**Риски:** шум в entity resolution; слабые PDF. **Митигация:** метрики по слою 1 отдельно; ручная разметка малого gold-set.

**Exit criteria:** подтверждён **надёжный single-document (и малый корпус вручную)** ingest: связный библиографический граф с осмысленными `CITES` там, где извлечение даёт DOI / arXiv / title+year. **Сделано для корпуса:** CLI `ingest-corpus`, пост-аудит дублей `Work` в Neo4j, multi-case benchmark suite. Цель «десятки работ **без критического** дублирования Work» остаётся: сейчас есть **обнаружение** кластеров-дублей, без автоматического merge-каталога.

**Статус Phase 1:** **runnable MVP** (2026-03-30, обновлено **2026-03-31**): пакет `science_graphrag`, `docker-compose.yml`, CLI `science-graphrag ingest` / **`ingest-corpus`**, документы [architecture/phase-1-backbone.md](architecture/phase-1-backbone.md), [adr/001-phase1-stack.md](adr/001-phase1-stack.md), [adr/002-layer1-graph-model.md](adr/002-layer1-graph-model.md), [benchmarks/strategy-v1.md](benchmarks/strategy-v1.md).

**Дополнение (2026-03-30):** после PDF→Markdown ingestion использует **task-aware document slices** (front matter / references scope) для Layer 1 LLM и **section-aware chunks** с детерминированными id для Qdrant; см. [architecture/chunking-strategy.md](architecture/chunking-strategy.md), [adr/003-chunking-and-dedup-strategy.md](adr/003-chunking-and-dedup-strategy.md).

**Дополнение (2026-03-31):** batch-ingest + Neo4j `find_work_dedup_violations`; канонический `:Author` по имени; опциональный ROR; `RELATED_VERSION_OF` при arXiv в OpenAlex для DOI-работы; реальные CV-pdf фикстуры (pypdf→MD) — см. Phase 4.

---

### Phase 2 — Scientific ontology v1

**Цель:** версионированная онтология научного слоя поверх backbone.

**Deliverables:**

- Спецификация сущностей: `ResearchTopic`, `Problem`, `Question`, `Hypothesis`, `Claim`, `Concept`, `Entity` (или подтипы), `Method`, `Model`, `Dataset`, `Software` — в объёме MVP vs later ([idea.md начало](idea.md)).
- Таксономия отношений (например: работа исследует тему, метод применён к задаче, утверждение поддержано экспериментом — уточнять в ADR).
- Матрица Source of Truth: что из текста, что из реестров, что только с confidence.
- ADR: scope ontology v1, anti-bloat (не раздувать типы узлов без benchmark-покрытия).

**Риски:** онтология «на все случаи жизни» без данных. **Митигация:** жёсткий MVP-поднабор сущностей и связей.

**Exit criteria:** зафиксирован документ ontology v1 + policy изменений; согласовано с Phase 3 extraction.

**Статус Phase 2 (2026-03-31):** **черновик + scope ADR** — [specs/ontology-v1-mvp.md](specs/ontology-v1-mvp.md), принятый [adr/004-ontology-v1-scope.md](adr/004-ontology-v1-scope.md); контракт Phase 3 для первого semantic-stage: [specs/extraction/semantic-method-dataset-v1.md](specs/extraction/semantic-method-dataset-v1.md). Имплементация узлов/рёбер в Neo4j — следующая волна.

---

### Phase 3 — Extraction pipeline и prompt contracts

**Цель:** воспроизводимое извлечение научного слоя с контрактами и метриками по этапам.

**Deliverables:**

- Независимые stages: metadata (уже из Phase 1), затем научные сущности/связи, затем claims/evidence (по готовности).
- Версионированные спецификации промптов и JSON-схем (вынести из [idea.md](idea.md) в `docs/specs/extraction/` по мере стабилизации).
- Поля: `confidence`, provenance (span/work id), failure modes, fallback (пропуск vs низкая уверенность).

**Риски:** один «большой промпт» на всё. **Митигация:** каскад как в [idea.md §8](idea.md).

**Exit criteria:** для каждого активного stage есть schema, контракт выхода, путь деградации и способ измерения качества (связь с Phase 4).

---

### Phase 4 — Benchmarks и eval-система

**Цель:** качество измеряется системно; регрессии ловятся автоматически там, где возможно.

#### 4.1. Семейства бенчмарков (аналог логики osint-gr benchmark families)

| Family | Вопрос качества | Примечание для science-graphrag |
|--------|-----------------|--------------------------------|
| **KG extraction** | Precision/Recall/F1 против эталона (граф или тройки) | Слой 1: метаданные, авторы, ссылки; слой 2: сущности/связи. |
| **Retrieval / citation** | Попадание в релевантные чанки/работы, attribution | Вопросы с заранее заданными gold-документами или чанками. |
| **Answer / synthesis** | Структурные инварианты ответа: цитаты, trace, отсутствие «голого» текста | Аналог «stage 6»-мышления: не обязательно совпадение формулировок. |
| **Hypothesis / idea-assist** | Полезность и безопасность идей | Часто **human-in-the-loop** + rubric; не блокирует merge как единственный gate. |

#### 4.2. Внешние датасеты и реестры (ориентиры из idea.md)

- **OpenAlex** — backbone для works/authors/institutions/sources; валидация и weak supervision.
- **SciERC** — классический IE/relations на научном тексте.
- **SciREX** — документный scientific IE.
- **ORKG** — примеры структурирования research contributions.
- Дополнительно упоминаемые направления: SciER (dataset/method/task) и др. — подбирать под конкретные слои извлечения.

Использование: не обязательно «end-to-end продукт», а **подмножества** для калибровки экстракторов и регрессий.

#### 4.3. Собственный benchmark pack (где нет gold-standard)

- Малый **gold-set** (10–50 работ или фрагментов) с ручной разметкой под критичные типы.
- Формат кейсов: JSON (id, входные артефакты, ожидаемые узлы/рёбра или допустимые варианты).
- Процесс adjudication и версионирование эталона.
- Отчёты регрессий (JSON/Markdown), сравнение с baseline.

**Риски:** дорогая разметка; утечка train/test при итерациях промптов. **Митигация:** holdout; фиксация версий промптов и моделей в отчётах.

**Exit criteria:** документ `docs/benchmarks/strategy-v1.md` (или раздел здесь) + минимальный автоматический прогон хотя бы для слоя 1 extraction; план merge vs nightly gates.

**Статус Phase 4:** **в процессе** (2026-03-30, углубление **2026-03-31**).

**Политика: бенчмарки с LLM как эталон качества.** Локальные и ручные регрессионные прогоны, по которым судят о качестве извлечения (метаданные, ссылки, семантический слой) и о содержимом Neo4j после ingest, следует выполнять **с включённым LLM** (`SCIENCE_GRAPHRAG_EXTRACTION_LLM_ENABLED=true`, ключ и base URL в `.env` — см. [eval/README.md](../eval/README.md), `MAIN_LLM_*` / `SCIENCE_GRAPHRAG_EXTRACTION_LLM_*`). Прогон **без** LLM остаётся для быстрых эвристик и merge CI; его метрики и граф **не** считаются эталоном поведения в продакшене.

**Уже есть:**

- [docs/benchmarks/strategy-v1.md](benchmarks/strategy-v1.md), [benchmarks/README.md](benchmarks/README.md), [eval/README.md](../eval/README.md).
- **Gold-set layer1** (каталог `tests/fixtures/benchmarks/layer1/<case_id>/`): YOLOv1; синтетические шаблоны (`doi_refs_heavy`, `arxiv_refs_heavy`, `noisy_layout_stub`); **реальные статьи** из pypdf→MD (`retinanet_focal_realpdf`, `fcos_realpdf`, скрипт `scripts/build_real_pdf_layer1_fixture.py`, см. `SOURCE.txt` в кейсе).
- **Draft-level** раннер: `eval/layer1/`, CLI `science-graphrag-layer1-benchmark`; в отчёте **`run_metadata`** (модель + `layer1_prompt_fingerprint`).
- **Suite:** один прогон по всем кейсам: `--suite` на корне фикстур (layer-1 и graph-v1).
- **Graph-level** eval: `eval/graph_v1/`, CLI `science-graphrag-graph-benchmark`, `graph_expectations` в `gold.json`; опционально **`max_work_dedup_violations`**, **`min_related_version_edges` / `max_related_version_edges`** (см. [benchmarks/graph-level-eval-v1.md](benchmarks/graph-level-eval-v1.md)).
- **Merge CI:** `.github/workflows/ci.yml` — `pytest -m "not integration"` на push/PR в `main`/`master`.
- **Nightly / manual CI:** `.github/workflows/integration-nightly.yml` — контейнеры Neo4j + Qdrant, `pytest tests -m integration` (`workflow_dispatch` + еженедельный cron).
- **Интеграция локально:** `pytest -m integration` — `tests/integration/test_full_ingest_integration.py` (Neo4j+Qdrant; skip при недоступности); политика merge vs nightly — [benchmarks/graph-level-eval-v1.md](benchmarks/graph-level-eval-v1.md).
- Общие хелперы suite: `eval/bench_common.py`; тесты discovery/dedup/OpenAlex-хелперов.

**Дальше (backlog Phase 4, приоритет):**

1. **Nightly+:** при необходимости добавить в `integration-nightly.yml` прогон `science-graphrag-*-benchmark … --suite` с секретами LLM / полный graph suite с живым OpenAlex (сейчас только integration-тесты).
2. **Graph suite в CI:** тяжёлый шаг; либо отдельный job на nightly, либо один лёгкий кейс без OpenAlex на merge.
3. **Gold для real-pdf:** заполнить `authorships[]` и при необходимости ужесточить `graph_expectations` под прогон **с включённым LLM** (отдельный job).
4. Новые **families** и gold по мере Phase 2+ — [benchmarks/benchmark-expansion-v1.md](benchmarks/benchmark-expansion-v1.md).

---

### Phase 5 — Retrieval и GraphRAG backend

**Цель:** query-time контур: lexical + vector + обход графа + синтез с опорой на источники.

**Deliverables:**

- Классы запросов учёного: поиск литературы, сравнение методов, трассировка claim → evidence, противоречия, открытые вопросы.
- API и контракты: запрос → retrieval trace → ответ с цитатами/ссылками на чанки и работы.
- Политики: когда углубляться в граф vs вектор; лимиты контекста.

**Риски:** галлюцинации при синтезе. **Митигация:** обязательные citations; тесты из Phase 4.

**Exit criteria:** end-to-end путь для **3–5** ключевых user journeys с воспроизводимым trace.

**Статус Phase 5 (2026-03-31):** **MVP in progress** — реализован минимальный API-контур (`/health`, `POST /v1/query`) и прототип UI в `science_graphrag/api/static/index.html`; для полного UI-flow из Phase 6 ещё нужны отдельные UI-facing endpoints (`works`, `work detail`, `graph neighborhood`, `chunks/evidence`) и стабилизация контрактов.

---

### Phase 6 — Frontend под исследовательский workflow

**Цель:** UI не как «общий чат», а рабочее место исследователя.

**Поверхности (приоритизация — отдельным UX-доком):**

- Workspace корпуса / проекта.
- Чтение статьи + панель извлечённых сущностей и связей.
- Обзор графа (фильтры по типам узлов).
- Панель доказательств и цитат к ответу системы.
- Композер запросов; опционально «доска идей» (post-MVP).

**MVP flow:** ingest корпуса → просмотр графа/метаданных → вопрос с grounded ответом → инспекция цитат.

**Риски:** тяжёлый UI до готовности данных. **Митигация:** сначала минимальный reader + chat с citations, затем graph explorer.

**Exit criteria:** карта экранов, модель состояния, контракты API для UI; реализация MVP-набора согласно приоритетам.

**Статус Phase 6 (2026-03-31):** **parallel track approved** — допускается запуск в две волны:  
1) `frontend shell + mock-driven screens + contract-first planning`;  
2) полная интеграция после стабилизации Phase 5 API-контрактов.  
См. [architecture/frontend-parallel-track-strategy.md](architecture/frontend-parallel-track-strategy.md), [specs/frontend-ui-api-contracts-v1.md](specs/frontend-ui-api-contracts-v1.md), [architecture/frontend-phase6-bridge-backlog.md](architecture/frontend-phase6-bridge-backlog.md).

---

### Phase 7 — Quality gates, документация, пилот

**Цель:** зрелость процесса и проверка ценности на реальном мини-корпусе.

**Deliverables:**

- CI: unit; integration; подмножество benchmarks на merge; при необходимости smoke с инфраструктурой (nightly/manual). **Частично (2026-03-31):** merge-gate — `.github/workflows/ci.yml` (`pytest -m "not integration"`); integration — `.github/workflows/integration-nightly.yml` (сервисы Neo4j/Qdrant + `pytest -m integration`, ручной/еженедельный запуск). Полный benchmark suite в CI пока не обязателен.
- Runbooks: деплой, бэкапы, ключи API внешних реестров.
- Пилот: узкий научный домен, критерии успеха (время до ответа, доля ответов с корректными цитатами, субъективная полезность).

**Post-MVP (milestones в roadmap):** мульти-статьёвый синтез, граф противоречий, расширенная оценка idea-assist.

**Exit criteria:** пилот завершён с зафиксированными выводами и backlog на следующую волну.

---

## 6. Зависимости между фазами

```mermaid
flowchart TD
    phase0[Phase0_Foundation] --> phase1[Phase1_ScholarlyBackbone]
    phase1 --> phase2[Phase2_OntologyV1]
    phase2 --> phase3[Phase3_ExtractionContracts]
    phase3 --> phase4[Phase4_Benchmarks]
    phase3 --> phase5[Phase5_RetrievalBackend]
    phase5 --> phase6[Phase6_FrontendResearchUX]
    phase4 --> phase7[Phase7_QualityGatesAndPilot]
    phase6 --> phase7
```

Параллельно допустимо:  
- вести `shell/contracts`-волну Phase 6 параллельно с доработкой Phase 5;  
- переводить UI на full integration только после стабилизации API-контрактов;  
- Phase 4 итеративно углублять с Phase 1–3.

---

## 7. Риски проекта (сводка)

| Риск | Митигация |
|------|-----------|
| Раздувание онтологии без данных | Ontology v1 + anti-bloat ADR; расширение только с benchmark |
| Нехватка gold-разметки | Внешние benchmarks + малый in-house gold; weak metrics на регистрах |
| Перегруз фронта до стабильной модели | Сначала data/API контракты и минимальный UI |
| Зависимость от внешних API | Кэш, лимиты, offline-деградация для чтения уже загруженного |

---

## 8. Связанные документы

| Документ | Назначение |
|----------|------------|
| [architecture/frontend-parallel-track-strategy.md](architecture/frontend-parallel-track-strategy.md) | Strategy параллельного frontend-трека до полного закрытия Phase 5 |
| [specs/frontend-ui-api-contracts-v1.md](specs/frontend-ui-api-contracts-v1.md) | Минимальные frontend-facing API контракты v1 |
| [architecture/frontend-phase6-bridge-backlog.md](architecture/frontend-phase6-bridge-backlog.md) | Стартовый backlog: frontend shell + backend bridge endpoints |
| [benchmarks/graph-level-eval-v1.md](benchmarks/graph-level-eval-v1.md) | План graph-level benchmark после ingest |
| [benchmarks/benchmark-expansion-v1.md](benchmarks/benchmark-expansion-v1.md) | Расширение корпуса и семейств бенчмарков |
| [idea.md](idea.md) | Онтология по слоям, первый слой графа, нормализация, промпты, внешние источники |
| Референс: `osint-gr/docs/README.md` | Образец индекса документации |
| Референс: `osint-gr/docs/architecture/benchmark-families.md` | Идея семейств бенчмарков |
| Референс: `osint-gr/docs/testing/testing-strategy.md` | Уровни тестов и gates |

---

## 9. История изменений

| Версия | Дата | Изменения |
|--------|------|-----------|
| 1.0 | 2026-03-31 | Phase 5/6 bridge: зафиксирован параллельный frontend-трек (`shell + mocks + contract-first`), добавлены UI API contracts v1 и общий backlog для frontend shell + backend bridge endpoints; roadmap синхронизирован с фактическим статусом API MVP (`POST /v1/query`). |
| 0.9 | 2026-03-31 | Phase 4: зафиксирована политика — ручные/репрезентативные бенчмарки с **LLM** как эталон качества; без LLM — только быстрые эвристики / merge CI. |
| 0.8 | 2026-03-31 | Phase 4/7: nightly CI Postgres + интеграции ingest/SQL/batch; layer1 + graph yolov1 бенчмарки без LLM; `case_tiers.json`, `--tier`; real-pdf gold: dedup graph, authorships для SSD/DETR. Phase 2/3: [adr/004-ontology-v1-scope.md](adr/004-ontology-v1-scope.md), [specs/extraction/semantic-method-dataset-v1.md](specs/extraction/semantic-method-dataset-v1.md) |
| 0.7 | 2026-03-31 | Phase 2: черновик [specs/ontology-v1-mvp.md](specs/ontology-v1-mvp.md); Phase 4: graph-v1 метрики `max_work_dedup_violations`, `RELATED_VERSION_OF` (через `graph_expectations`); GitHub Actions **integration-nightly** (Neo4j+Qdrant + `pytest -m integration`); roadmap: backlog 4.3 пересортирован после закрытия merge-gate / nightly-базиса / инвариантов графа |
| 0.6 | 2026-03-31 | Phase 1: `ingest-corpus`, Neo4j dedup audit, canonical Author id, опциональный ROR, `RELATED_VERSION_OF` из OpenAlex; Phase 4: benchmark **suite** (`--suite`), `bench_common`, integration ingest test, расширенный gold-set (синтетика + real-pdf), документация merge/nightly; Phase 7: старт CI merge-gate |
| 0.5 | 2026-03-30 | LLM-first layer-1 extraction; YOLOv1 layer-1 benchmark (`eval/layer1`); initial graph-level eval (`eval/graph_v1`); `CITES` без DOI (arxiv / title+year); Phase 1 deliverables разбиты на done/partial/deferred; Phase 4 статус in progress; план расширения benchmark |
| 0.4 | 2026-03-30 | Task-aware chunking, document slices, ADR 003, semantic-chunks spec, Qdrant chunk fingerprints |
| 0.3 | 2026-03-30 | Phase 1: `science_graphrag`, Docker stack, Neo4j/Postgres/Qdrant ingest, ADR 001–002, benchmarks strategy v1 |
| 0.2 | 2026-03-30 | Phase 0: корневой README (PRD), индекс `docs/`, ADR-000, каркас модулей `ingestion`…`eval` |
| 0.1 | 2026-03-30 | Первоначальный roadmap по плану greenfield + фазы 0–7 |
