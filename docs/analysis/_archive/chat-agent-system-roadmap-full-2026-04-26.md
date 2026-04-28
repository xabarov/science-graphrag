# Agent chat system roadmap — 2026-04-26 (**ARCHIVED FULL COPY**)

> **2026-04-27:** Живой канон перенесён в короткий [`../chat-agent-system-roadmap-2026-04-26.md`](../chat-agent-system-roadmap-2026-04-26.md) (упрощённая архитектура + явные будущие треки `tool_search` и compaction). Этот файл сохранён только как **исторический** детальный план (CH-волны, шесть specialist subgraphs, длинная taxonomy). Не обновлять как primary.

---

## Historical document body (unchanged export)

**Статус:** draft / living working doc (трек `CH` — **CH1–CH3: Wave A**; **CH4 + долги CH1–CH3 (частично) + observability-задел: Wave B**, 2026-04-26; **Wave Next: Agent Chat Hardening + CH5 v1**, 2026-04-26; **Phoenix agent tracing plan refreshed 2026-04-27**, см. §10/§11)
**Цель:** спроектировать продуктовую агентную систему чата для research-workspace в `SciGraph`: multi-turn, tool-based, grounded on graph + chunks + workspace context, с понятной эволюцией от текущего `POST /v2/agent/query`.

**Основано на анализе:**
- текущего runtime и UI чата в `SciGraph`
- агентных паттернов в `osint-gr/backend/osint_graphrag/agents`
- tool-search, subagent и context-compression паттернов в `openclaude/src`

**Companion doc (frontend/UI):** detailed implementation plan for agent chat presentation, shimmer states, and subagent visibility lives in [`agent-chat-frontend-ui-plan-2026-04-26.md`](../agent-chat-frontend-ui-plan-2026-04-26.md).

**Почему это нужно:** текущий чат уже имеет SSE, `AgentState`, `tool_trace`, supervisor и specialist nodes, но ещё не является полноценным research chat runtime: API принимает один `question`, инструменты узкие, нет явного tool discovery, нет устойчивого multi-turn memory/compression, а use cases исследователя шире, чем `idea_search + summarize_workspace + cypher`.

---

## 1. Product north star

Пользователь работает не с абстрактным LLM-чатом, а с **исследовательским ассистентом по своей рабочей области**. Он должен:

1. понимать текущий scope (`workspace`, статья, набор статей, сущности);
2. уметь выбирать правильный способ поиска: graph, semantic chunks, keyword chunks, metadata/catalog;
3. отвечать с доказательствами: цитаты, paper ids, graph paths, authors, venues, years;
4. держать длинный диалог без взрыва контекста;
5. различать режимы ответа: факт, обзор, сравнение, hypothesis/ideation, bibliography export;
6. быть наблюдаемым и проверяемым через trace/events/evals.

**Ключевой принцип:** orchestration должна быть **agent-friendly**, но инструменты должны быть **domain-shaped**, а не "one raw search tool does everything".

### 1.1 Доверие через тесты (в том числе live API)

Агентная система без **хорошего набора тестов** не заслуживает доверия: поведение недетерминировано, контракт API и envelope эволюционируют, а регрессии в маршрутизации, туллинге и multi-turn легко прячутся за «вроде отвечает».

Нужен **многослойный контроль качества**:

1. **Юнит- и контракт-тесты** (envelope, `tool_trace`, manifest/sync, digest/session, парсинг SSE на фронте) — быстрый feedback в CI, без реального LLM.
2. **In-process API** (`TestClient`, моки графа) — паритет JSON/SSE и форма ответа без поднятого сервера.
3. **Поверх live API с реальным агентом** (поднятый backend, Neo4j/Qdrant по необходимости, настоящий `POST /v2/agent/query`) — иначе нет уверенности, что цепочка «LLM → tools → сторы → ответ» не сломана моками и что multi-turn/SSE ведут себя как в проде. Такие прогоны осознанно дороже: их держат **опционально** (отдельный job, переменная окружения, ручной gate перед релизом), но **полностью от них отказываться нельзя**, если продукту нужен операционный уровень доверия.

В репозитории задел: `scripts/live_check/` (pre-flight конфига + HTTP-проверки к поднятому API), опциональные pytest под `tests/live/` при `AGENT_LIVE_BASE`. Их следует развивать по мере усложнения чата (сценарии, фикстурный workspace, пороговые проверки `tool_trace`).

---

## 2. Research use cases

### 2.1 Базовые use cases из запроса

1. Какие статьи у меня сейчас в рабочей области?
2. Какие идеи есть в статье `X`?
3. Как связано `X` с `Y`?
4. Кто авторы статьи `X`?
5. Приведи цитату, в которой утверждается `X`.
6. Какие новые идеи для следующей публикации можно предложить, опираясь на область / набор статей?
7. Составь список литературы по ГОСТ.

### 2.2 Что ещё исследователь естественно спросит

1. Какие статьи в workspace самые центральные / наиболее цитируемые / самые новые?
2. Как эволюционировала идея `X` по годам?
3. Какие статьи противоречат друг другу по тезису `X`?
4. Какие методы, датасеты и метрики чаще всего встречаются в этой теме?
5. Какие пробелы в related work видны по текущему корпусу?
6. Какие 5 работ надо прочитать следующими и почему?
7. Какие статьи ближе всего к paper `X`, но используют другой подход?
8. Какие papers связывают темы `X` и `Y`, даже если напрямую не названы одинаково?
9. В каких местах статьи `X` обсуждается ограничение / future work / weakness?
10. Собери краткий related work по теме `X` с группировкой по школам/подходам.
11. Подготовь аргументы "за" и "против" гипотезы `H`, опираясь на corpus.
12. Найди первоисточник идеи / датасета / архитектурного мотива.
13. Какие авторы и лаборатории чаще всего встречаются в этой области?
14. Где в моём workspace есть потенциальные methodological gaps для новой статьи?
15. Экспортируй список источников в формате ГОСТ, а позже, возможно, и в BibTeX/APA.

### 2.3 Классы ответов

Для runtime полезно разделять не только intent, но и **answer class**:

1. **Inventory / catalog**: список статей, авторов, датасетов, тем.
2. **Fact lookup**: кто автор, какой год, какой venue, есть ли статья в workspace.
3. **Grounded explanation**: идеи статьи, summary, related work cluster.
4. **Relation tracing**: как `X` связано с `Y`, path explanation, influence chain.
5. **Quote extraction**: найти фрагмент/цитату под утверждение.
6. **Synthesis / comparison**: сравнить papers, направления, доказательства за/против.
7. **Ideation**: предложить новые гипотезы, experiments, research gaps.
8. **Export / formatting**: bibliography list, GOST output.

У каждого класса свой threshold "достаточно доказательств", свой preferred tool mix и свои acceptance/tests.

---

## 3. Current state snapshot

### 3.1 Что уже есть в `SciGraph`

1. `POST /v2/agent/query` уже умеет sync JSON и SSE.
2. `science_graphrag/agent/graph/state.py` уже содержит `messages`, `workspace_id`, `citations`, `tool_trace`, `budget_remaining`, `specialist_results`, `routing_log`.
3. Есть LangGraph supervisor и specialist nodes:
   - `retrieval_agent`
   - `graph_agent`
   - `writer_agent`
4. Есть текущие tools:
   - `idea_search`
   - `summarize_workspace`
   - `cypher_query`
   - `entity_search`
   - `edge_search`
   - `final_answer`
5. UI уже перешёл к chat-shaped surface:
   - `ChatComposer`
   - `ChatMessageThread`
   - session sidebar / session state
   - streaming через `useAgentStream`

### 3.2 Чего не хватает

1. Полноценного **multi-turn backend contract**: сейчас главным входом остаётся один `question`.
2. Богатого **research tool taxonomy**: нет paper-centric, citation-centric, bibliography-centric tool layer.
3. **Tool discovery**: агент должен либо знать все tools сразу, либо жёстко зашит в supervisor.
4. **Context compression**: нет устойчивой модели long chat memory с несколькими уровнями компактирования.
5. Явного разделения между:
   - "выполни фактологический lookup"
   - "сделай graph traversal"
   - "собери evidence pack"
   - "предложи новую идею"
   - "отформатируй библиографию"
6. Нормального answer contract для `quote`, `relation_path`, `gost bibliography`, `idea suggestions with supporting papers`.

### 3.3 Что стоит переиспользовать, а не переписывать

1. `AgentState` и LangGraph skeleton.
2. `tool_trace` и SSE pipeline.
3. Разделение на supervisor + specialists.
4. UI chat thread / sessions / composer.
5. `cypher_safety` и общий graph-readonly guard.

---

## 4. Lessons from adjacent codebases

### 4.1 Из `osint-gr`

Наиболее полезные паттерны:

1. **Operations-first orchestration**: не только raw tool-calling, но и высокоуровневые операции.
2. **Fallback chains**: graph -> vector -> file или parallel graph + vector.
3. **Evidence-first contracts**: единый тип доказательств до финального synthesis.
4. **Answer classes**: разные режимы ответа имеют разные требования к evidence sufficiency.
5. **Product-safe stream events**: UI видит шаги расследования, но не сырые скрытые промпты.

Что не надо переносить буквально:

1. OSINT-specific entity model (`Person`, `Institution`, `case_id`, Milvus partitions).
2. Дублирующиеся runtime branches как долговременную норму.
3. Размытый термин "Cypher tool", если под ним реально Text2Cypher, а не raw read-only query.

### 4.2 Из `openclaude`

Наиболее полезные паттерны:

1. **Deferred tools + tool search**: не грузить агенту весь каталог схем сразу.
2. **Fork/subagent side-calls** для специальных задач: summary, rerank, idea expansion, relevance judging.
3. **Многоуровневое context compression**:
   - session memory
   - partial compact
   - full compact with boundary
4. **Короткие progress summaries** для длинных шагов в UI.
5. **Coordinator with restricted tool pool**: оркестратор не обязан владеть всеми тяжёлыми tools напрямую.

Что дорого переносить целиком:

1. полный CLI/team/coordinator infrastructure;
2. beta-specific tool loading protocol;
3. remote/tmux/worktree execution model.

---

## 5. Proposed target architecture

### 5.1 Runtime roles

Предлагается четырехслойная архитектура:

1. **Chat API layer**
   - принимает `thread`, `workspace scope`, optional `focus paper`, `response_mode`
   - стримит events для UI

2. **Coordinator / supervisor**
   - понимает intent / answer class
   - запрашивает tool search
   - решает, какой specialist нужен
   - следит за budget и context window

3. **Specialist agents**
   - `catalog_specialist`
   - `retrieval_specialist`
   - `graph_specialist`
   - `citation_specialist`
   - `ideation_specialist`
   - `bibliography_specialist`

4. **Evidence synthesis layer**
   - собирает evidence pack
   - строит grounded answer
   - добавляет citation blocks / path explanation / export payload

На старте не обязательно реализовывать все specialists как отдельные LangGraph subgraphs. Можно идти поэтапно:

1. сначала один coordinator + расширенный tool registry;
2. затем вынести `graph_specialist` и `citation_specialist`;
3. затем ideation/bibliography.

### 5.2 Coordinator contract

Coordinator не должен сразу видеть весь corpus в prompt. Его задача:

1. классифицировать запрос;
2. выбрать answer class;
3. запросить shortlist tools;
4. собрать plan на 1-3 шага;
5. вызвать specialist или operation;
6. при необходимости запросить compact context;
7. завершить answer synthesis.

Минимальные новые coordinator-level actions:

1. `tool_search`
2. `load_scope_context`
3. `route_to_specialist`
4. `request_context_compact`
5. `finalize_answer`

### 5.3 Suggested specialists

#### A. Catalog specialist

Для вопросов:
- какие статьи в workspace
- сколько статей
- какие авторы / venues / годы
- какие papers подходят под фильтр

Основные tools:
- `workspace_overview`
- `workspace_list_papers`
- `paper_lookup`
- `paper_metadata`
- `paper_authors`
- `paper_counts`

#### B. Retrieval specialist

Для вопросов:
- идеи статьи
- где обсуждается тезис
- похожие работы
- related work cluster

Основные tools:
- `semantic_chunk_search`
- `keyword_chunk_search`
- `paper_section_search`
- `paper_idea_extract`
- `related_papers_search`

#### C. Graph specialist

Для вопросов:
- как связано `X` с `Y`
- кто связан с кем
- цепочка влияния / lineage
- authorship/citation neighborhood

Основные tools:
- `entity_lookup`
- `graph_neighbors`
- `graph_path_between`
- `paper_relations`
- `graph_schema`
- `cypher_readonly_query` (advanced / guarded)

#### D. Citation specialist

Для вопросов:
- приведи цитату
- найди место, где утверждается `X`
- покажи supporting evidence / counter-evidence

Основные tools:
- `claim_quote_search`
- `quote_verify`
- `citation_context_window`
- `supporting_evidence_pack`

#### E. Ideation specialist

Для вопросов:
- какие новые идеи для публикации
- какие gaps в области
- чем дополнить current manuscript

Основные tools:
- `field_gap_scan`
- `hypothesis_seed_generator`
- `novelty_crosscheck`
- `supporting_papers_for_idea`

#### F. Bibliography specialist

Для вопросов:
- составь список литературы по ГОСТ
- собери reading list
- экспортируй bibliography

Основные tools:
- `collect_bibliography_candidates`
- `bibliography_formatter_gost`
- `reading_queue_builder`

### 5.4 MVP execution model

Чтобы команда не читала этот документ как "сначала строим полный multi-agent swarm", фиксируем минимальную исполнимую модель.

#### V1 execution model

1. `agent_v2` принимает thread-aware request.
2. coordinator определяет `answer_class`, scope и нужный tool subset.
3. coordinator вызывает `tool_search`.
4. coordinator работает **не со всеми tools**, а с shortlist.
5. specialist в V1 может быть **не отдельным subgraph**, а логическим execution profile:
   - tagged subset tools
   - specialist prompt prefix
   - specialist-specific budget rules
6. tool calls могут идти либо напрямую из coordinator loop, либо через lightweight specialist node.
7. synthesis layer в V1 может быть обычным `writer` step в конце того же LangGraph run.

#### Practical interpretation

До `CH6` термин "specialist" читаем так:

1. это отдельная роль и набор разрешённых tools;
2. это не обязательно отдельный process/subagent;
3. это может быть один LangGraph node с разными prompt/tool profiles.

Это позволяет:

1. не переписывать runtime big-bang;
2. сначала внедрить taxonomy/tool search/multi-turn;
3. только потом изолировать specialists в отдельные subgraphs там, где это реально даёт выигрыш.

---

## 6. Tool taxonomy

### 6.1 Why tool taxonomy matters

Если дать модели только `idea_search`, `entity_search` и `cypher_query`, она будет:

1. перегружать один tool неподходящими задачами;
2. раньше времени уходить в raw graph queries;
3. терять distinction между "найти evidence" и "синтезировать answer";
4. хуже объяснять пользователю, что она делает.

Поэтому tools надо группировать по слою ответственности.

### 6.2 Proposed tool families

#### Family A. Scope / catalog tools

1. `workspace_overview(workspace_id)`
2. `workspace_list_papers(workspace_id, filters, sort)`
3. `paper_lookup(query, workspace_id?)`
4. `paper_metadata(work_id)`
5. `paper_authors(work_id)`
6. `paper_references(work_id)`
7. `paper_citations(work_id)`
8. `paper_counts(workspace_id)`

#### Family B. Retrieval tools

1. `semantic_chunk_search(query, workspace_id?, work_id?, top_k)`
2. `keyword_chunk_search(query, workspace_id?, work_id?, top_k)`
3. `paper_section_search(work_id, section_hint, query?)`
4. `paper_idea_extract(work_id)`
5. `related_papers_search(query_or_work_id, mode)`

#### Family C. Graph tools

1. `entity_lookup(name_or_alias, kinds?)`
2. `graph_neighbors(node_id, edge_types?, depth=1)`
3. `graph_path_between(source, target, max_hops)`
4. `paper_relations(work_id, relation_type?)`
5. `graph_schema()`
6. `cypher_readonly_query(query, params?)`

#### Family D. Evidence / quote tools

1. `claim_quote_search(claim, workspace_id?, work_id?, top_k)`
2. `quote_verify(claim, quote_text, work_id)`
3. `citation_context_window(chunk_id_or_citation_id)`
4. `supporting_evidence_pack(topic_or_claim)`
5. `counter_evidence_pack(topic_or_claim)`

#### Family E. Ideation tools

1. `field_gap_scan(topic, workspace_id?)`
2. `hypothesis_seed_generator(topic, constraints?)`
3. `novelty_crosscheck(hypothesis, workspace_id?)`
4. `supporting_papers_for_idea(hypothesis)`

#### Family F. Bibliography / export tools

1. `collect_bibliography_candidates(topic_or_thread)`
2. `bibliography_formatter_gost(work_ids_or_refs)`
3. `reading_queue_builder(topic, depth, diversity_mode)`

### 6.3 Raw Cypher policy

`cypher_readonly_query` нужен, но **не должен быть default tool для обычного вопроса**.

Политика:

1. сначала использовать domain tools;
2. raw cypher доступен только graph specialist;
3. перед ним почти всегда должен быть доступен `graph_schema()`;
4. только read-only, allowlist labels/types, max row cap;
5. все raw cypher calls обязательно попадают в trace и eval.

---

## 7. Tool search and deferred loading

### 7.1 Problem

Полный prompt со всеми tool schemas быстро раздуется, особенно если появятся:

1. catalog tools;
2. graph tools;
3. quote tools;
4. bibliography tools;
5. future MCP-like integrations.

### 7.2 Proposed pattern

Использовать двухступенчатую схему:

1. coordinator по умолчанию видит только:
   - короткий `tool catalog`
   - names + one-line descriptions + tags
2. отдельный `tool_search(query, answer_class, scope)` возвращает shortlist tools и/или full schema для selected tools

### 7.3 Expected benefits

1. меньше токенов на каждом turn;
2. проще добавлять новые tools;
3. меньше шанс, что агент будет вызывать неподходящие инструменты;
4. лучше согласуется с растущим research surface.

### 7.4 Minimal `tool_search` contract

`tool_search` в первой версии не обязан быть LLM-based. Достаточно rule/tag-based shortlisting.

**Input:**

1. `query`
2. `answer_class`
3. `scope` (`workspace`, `paper`, `global`)
4. `specialist_hint`
5. `max_tools`

**Output:**

1. `selected_tools`
2. `selection_reason`
3. `suppressed_tools`
4. `schema_refs`
5. `confidence`

**Fallback policy:**

1. если shortlist пустой -> route to conservative catalog/retrieval baseline
2. если shortlist слишком широкий -> обрезать по capability priority и budget
3. если запрос ambiguous -> вернуть 2-3 tool families, а не все tools подряд

### 7.5 Minimal implementation shape

Нужны два артефакта:

1. `tool_manifest.py`
   - machine-readable registry with tags/capabilities
2. `tool_search.py`
   - shortlist by query class, tags, scope, specialist

На первом шаге `tool_search` может быть rule-based, не LLM-based.

---

## 8. Context compression design

### 8.1 Why this is mandatory

Research chat быстро упирается в:

1. длинную историю диалога;
2. повторяющиеся evidence blocks;
3. многократные ссылки на те же papers/entities;
4. переходы от "что есть" к "сравни" к "придумай новое".

Без compression runtime либо забудет контекст, либо станет дорогим и нестабильным.

### 8.2 Proposed minimum: 3+ levels

#### Level 0. Raw evidence pack

Это не compression сам по себе, а стандартизованный turn artifact:

1. top chunks
2. graph rows / paths
3. paper metadata
4. citations / quote candidates

Нужен для reproducibility и evals.

#### Level 1. Turn digest

Короткая структурированная сводка по одному completed turn:

1. user intent
2. answer class
3. selected papers/entities
4. core findings
5. unresolved points
6. evidence ids

Это хранится рядом с session turns и может быстро реинжектиться в prompt.

#### Level 2. Rolling session memory

Компактная summary нескольких turn'ов:

1. активная тема диалога
2. важные papers
3. важные entities
4. уже подтверждённые тезисы
5. уже отвергнутые hypotheses
6. open questions

Обновляется не на каждый token, а по завершении meaningful turn.

#### Level 3. Workspace knowledge capsules

Лениво вычисляемые, переиспользуемые compact artifacts:

1. `workspace capsule`
2. `paper capsule`
3. `entity capsule`
4. `topic capsule`

Примеры:

1. summary paper `X`
2. compressed idea map for workspace
3. key relation clusters around topic `Y`

#### Level 4. Full compact boundary

Для очень длинных тредов:

1. старые turns сворачиваются в boundary summary;
2. runtime знает, что это уже compacted history;
3. raw history остаётся доступной для audit/debug, но не держится в каждом prompt.

### 8.3 Compression ownership

1. coordinator решает, когда просить compact;
2. compact может делать отдельный lightweight summarizer side-agent;
3. synthesis layer получает уже digest/capsule, а не весь transcript.

### 8.4 Compression triggers

Чтобы compression не оставался "идеей на потом", фиксируем минимальную operational policy:

1. `turn_digest`
   - создаётся после каждого meaningful completed turn
2. `rolling_session_memory`
   - обновляется каждые `N` turn'ов или при достижении token threshold
3. `workspace/paper/topic capsule`
   - строится лениво по требованию или переиспользуется из cache
4. `full compact boundary`
   - срабатывает только когда thread history уже не помещается в допустимый prompt budget

### 8.5 Persistence policy (draft)

1. raw evidence pack: short-lived, trace/debug artifact
2. turn digest: persist with session
3. rolling session memory: persist with session
4. capsules: cacheable reusable artifacts
5. full compact boundary: persist as explicit boundary marker, raw turns не удаляются из audit trail

---

## 9. Response contracts

Новой системе нужен не один универсальный `answer: str`, а семейство совместимых contracts.

### 9.1 Base response envelope

Остаётся общий envelope:

1. `answer`
2. `citations`
3. `tool_trace`
4. `duration_ms`
5. `run_metadata`
6. `answer_class`
7. `evidence_summary`
8. `warnings`

### 9.2 Optional typed payloads

Для richer UX добавить опциональные payloads:

1. `inventory`
   - papers/authors/venues/counts
2. `relation_trace`
   - nodes, edges, path explanation
3. `quote_candidates`
   - quote text, source section, confidence
4. `idea_suggestions`
   - hypothesis, novelty rationale, supporting works, risks
5. `bibliography`
   - formatted entries, source work ids, format=`gost`

### 9.3 Evidence requirements by answer class

1. `fact_lookup`:
   - metadata or graph fact is enough
2. `quote_extraction`:
   - exact quote candidate + source context required
3. `relation_tracing`:
   - graph path or combined graph+text explanation required
4. `ideation`:
   - at least 2-3 supporting works or explicit warning that suggestion is weak
5. `bibliography_export`:
   - source list must be normalized before formatting

### 9.4 Canonical response examples

#### Fact lookup

```json
{
  "answer_class": "fact_lookup",
  "answer": "У статьи X четыре автора: ...",
  "citations": [{"work_id": "w1"}],
  "inventory": {
    "authors": [{"name": "Author A"}, {"name": "Author B"}]
  },
  "warnings": []
}
```

#### Quote extraction

```json
{
  "answer_class": "quote_extraction",
  "answer": "В статье X это утверждение выражено так: \"...\"",
  "citations": [{"work_id": "w1", "chunk_id": "c7"}],
  "quote_candidates": [
    {
      "quote_text": "...",
      "work_id": "w1",
      "section": "Discussion"
    }
  ],
  "warnings": []
}
```

#### Bibliography export

```json
{
  "answer_class": "bibliography_export",
  "answer": "Подготовил список литературы по ГОСТ.",
  "citations": [{"work_id": "w1"}, {"work_id": "w2"}],
  "bibliography": {
    "format": "gost",
    "entries": ["...", "..."]
  },
  "warnings": []
}
```

---

## 10. Observability and evals

### 10.1 Required traceability

Каждый turn должен фиксировать **два уровня traceability**:

1. **Product/API trace (`tool_trace`, SSE/debug events, envelope):** компактный, стабильный контракт для UI/evals.
2. **Phoenix/OpenTelemetry trace:** техническое дерево latency/token/tool/retrieval спанов для отладки, стоимости и регрессий.

Минимальный API/eval слой:

1. selected answer class
2. selected specialist
3. selected tools
4. compact events
5. evidence ids used in final answer
6. warnings like `weak_evidence`, `graph_only`, `text_only`, `no_quote_found`

Минимальный Phoenix слой:

1. `agent.query` — один CHAIN root на user turn; `session.id = thread_id`, `user.id = workspace_id`, `agent.runtime`, `agent.max_tool_calls`.
2. `agent.turn_policy` / `agent.supervisor.route` / `agent.specialist.<name>` — CHAIN-спаны для routing decisions, budget, confidence/fallback.
3. `llm.agent.*` — LLM-спаны для classifier/supervisor/writer с `llm.model_name` и token counts; CHAIN-спаны не должны сами нести `llm.*`.
4. `tool.<tool_name>` — TOOL-спан для каждого domain tool из `tool_trace`, с `tool.parameters`, `row_count`, `truncated`, error/status.
5. `retrieval.qdrant.<tool_name>` — RETRIEVER-спан для semantic/quote search, с `retrieval.documents.*` и Qdrant collection/filter metadata.
6. `embedding.agent.<tool_name>` — EMBEDDING-спан для query embedding, отдельно от retrieval.
7. root/span output содержит только короткий summary (`answer_class`, `tool_call_count`, `warning_codes`, `citation_count`), без сырых длинных prompt/chunk payload.

`tool_trace` и Phoenix не заменяют друг друга: `tool_trace` нужен для продукта и deterministic eval, Phoenix — для объяснения latency/cost/retrieval/LLM дерева. Для release-quality observability они должны коррелировать по именам tools и ошибкам.

### 10.2 UI stream events

Полезные продуктовые SSE events:

1. `intent_classified`
2. `tool_search_result`
3. `specialist_selected`
4. `tool_call`
5. `tool_result`
6. `context_compacted`
7. `evidence_ready`
8. `final_answer`
9. `warning`

### 10.3 Benchmark families to add

Отдельные eval families под research chat:

1. `chat_inventory_v1`
2. `chat_paper_ideas_v1`
3. `chat_relation_trace_v1`
4. `chat_quote_grounding_v1`
5. `chat_authors_metadata_v1`
6. `chat_ideation_grounded_v1`
7. `chat_bibliography_gost_v1`
8. `chat_multi_turn_memory_v1`
9. `chat_tool_selection_v1`
10. `chat_context_compaction_v1`

### 10.4 Benchmark workspace baseline (chat regression)

Для chat-agent регрессии и Phoenix-audit зафиксирована **одна** эталонная benchmark-backed область:

- **`ws-pilot-od`** — manifest: `tests/fixtures/benchmarks/chat_agent_roadmap/baseline_workspace_manifest.json`.

Перед live suite: **workspace readiness audit** (наличие `Work`, авторов, исходящих `CITES`, чанков в Qdrant и `workspace_ids` на чанках). Реализация: `scripts/chat_agent_workspace_readiness_audit.py` / `eval/chat_agent/workspace_audit.py`.

Roadmap-aligned кейсы и артефакты прогона: `science-graphrag-chat-agent-roadmap` (см. [`eval/README.md`](../../eval/README.md), [`agent-chat-tools-and-trace-audit-master-2026-04-28.md`](../agent-chat-tools-and-trace-audit-master-2026-04-28.md)).

### 10.5 Phoenix agent tracing status

Актуальный companion по Phoenix: [`phoenix-tracing-coverage-2026-04-25.md`](../phoenix-tracing-coverage-2026-04-25.md).

Текущее состояние (2026-04-27):

1. Есть `agent.query`, `phoenix_trace_id`, `session.id` от `thread_id`, `PHOENIX_TRACE_SCOPE=full` в live harness.
2. Есть частичная ручная разметка TOOL/EMBEDDING (`idea_search`, `paper_quote_search`).
3. Нет полного TOOL coverage для всех domain tools.
4. Нет RETRIEVER-спанов с `retrieval.documents.*` для Qdrant search.
5. LLM attribution для supervisor/classifier надо подтвердить тестом или закрепить ручными `llm.agent.*` spans.
6. `trace_audit.json` пока gate'ит наличие `phoenix_trace_id`, но не форму span tree.

Следующий observability milestone перед расширением specialists: закрыть X2.2–X2.9 из Phoenix companion, чтобы CH6/CH7 не умножали неинструментированные ветки.

---

## 11. Implementation roadmap

Ниже предлагается отдельный трек `CH` (Chat Agent).

**Wave A (2026-04-26):** реализованы **CH1 + CH2 + CH3** одним пластом. Канон контракта: [`docs/specs/agent-chat-v1.md`](../specs/agent-chat-v1.md). Стартовые фикстуры: `tests/fixtures/benchmarks/chat_wave_a/`. Рефакторинг крупного `workspace_paper_tools.py` — в `docs/backlog/refactor-backend.md`.

**Wave B (2026-04-26):** **CH4 v1** (in-memory session по `thread_id`, `history_digest`, `build_initial_agent_state`, digest после тёрна, SSE `context_compacted`, `session_init` в `tool_trace`) + закрытие части долгов Wave A: расширенные `warnings` в `chat_envelope`, typed-блоки в `AskAnswerPanel` / `ChatTypedBlocks.jsx`, wire `threadId`/`historyDigest` из `AskPanel`/`useAskSubmit`, GOST `event`/`pages`, `filtered_work_ids` + warnings у библиографии, `qdrant_unavailable` у quote-tool, writer + `tool_search` (skip с meta), `tests/test_tool_manifest_sync.py`, расширение `test_tool_search`, smoke фикстуры в CI (`tests/eval/test_chat_wave_a_inventory.py`), `phoenix_trace_id` из активного OTel span. **Не в Wave B:** полный CH5 (capsules, full compact), CH6, CH7. **Update 2026-04-27:** добавлен отдельный roadmap harness `science_graphrag-chat-agent-roadmap` (`eval/chat_agent/roadmap_runner.py`), эталонная область **`ws-pilot-od`**, pre-flight audit Neo4j+Qdrant (`eval/chat_agent/workspace_audit.py`, `scripts/chat_agent_workspace_readiness_audit.py`), per-case артефакты и отчёт [`agent-chat-tools-and-trace-audit-master-2026-04-28.md`](../agent-chat-tools-and-trace-audit-master-2026-04-28.md).

**Wave Next — Agent Chat Hardening + CH5 v1 (2026-04-26, реализовано):**
1. **Аудит качества:** CH1–CH4 v1 подтверждены in-process тестами; главные риски закрывались persistence, политикой CH5 и live/eval gate — зафиксировано в этом roadmap и в спеке.
2. **Persisted session memory:** `SCIENCE_GRAPHRAG_AGENT_SESSION_MEMORY_BACKEND=redis` + `RedisSessionMemoryBackend` (TTL, ключ с префиксом), инициализация в `science_graphrag/api/main.py` через `configure_session_memory_backend`; fallback на in-memory при недоступном Redis; Docker Compose для сервиса `api` выставляет `redis` по умолчанию.
3. **CH5 v1 (compaction policy):** `context_compacted.compaction` расширен полями `kinds` (`turn_digest`, `rolling_memory`, `workspace_capsule` при порогах), `digest_count`, `boundary`; sync JSON — `run_metadata.compaction` + `session_digest_count` для паритета с SSE; **workspace_capsule** (детерминированный артефакт последних intent-ов) подмешивается в первый user-турн через `<workspace_capsule>` в `format_user_with_memory`.
4. **Quality gate:** `scripts/live_check/http_suite.py` при `AGENT_LIVE_GATE_CH4=1` проверяет и sync JSON с `thread_id` (`run_metadata.compaction.kinds`); pytest `tests/live/test_agent_v2_http_optional.py` — отдельный кейс `test_live_agent_v2_gate_ch4_sync_json_with_thread`; контрактный runner `python -m eval.chat_agent`.
5. **UI + тесты:** блок «Server session memory» в `AskAnswerPanel`, `run_metadata` в `normalizeQueryResponse`, сохранение `run_metadata` в `AskPanel` details; RTL/`vitest` для `AskAnswerPanel` и `useAskSubmit`.

**Остаётся вне этого slice:** полноценный coordinator-triggered compaction, LLM-capsules, full compact boundary как отдельный продуктовый слой; CH6–CH7. **Прогресс 2026-04-27:** первый **use-case** runner поверх контрактного `eval/chat_agent` — `science-graphrag-chat-agent-roadmap` (см. trace-audit doc); полноценный nightly «как agent_tools» по-прежнему опционален и расширяется отдельно.

**Update 2026-04-27 — Coordinator Gate v0 + target direction:** после инцидента «`привет` → список статей» добавлен первый явный coordinator-seam: `TurnPolicy` / `classify_turn_policy` в `science_graphrag/agent/coordination/turn_policy.py`, `coordinator_gate` в `tool_trace`, `intent_classified` в SSE/debug events, `chat` / `clarification` answer classes, no-tools/direct writer path и safe fallback `invalid router output -> writer_agent` вместо `retrieval_agent`. Это **не целевое состояние intent routing**: текущие regex/rule hints считаются временным guardrail v0 для очевидных случаев (greeting/meta/ambiguous short turn), а не попыткой покрыть язык списками фраз. Целевой следующий шаг — сохранить интерфейс `TurnPolicy`, но заменить keyword-heavy реализацию на hybrid/LLM `TurnPolicyClassifier` со structured output, confidence, eval-набором и safe fallback to clarification.

### Wave CH1 — Contracts and answer classes

**Статус:** **DONE (Wave A, 2026-04-26)**; **дополнено Wave B (2026-04-26)** — см. комментарии ниже.

**Сделано в репо (кратко):**
- Спека: [`docs/specs/agent-chat-v1.md`](../specs/agent-chat-v1.md) (request/response, SSE vocabulary, optional typed payloads).
- API: `science_graphrag/api/agent_v2.py` — optional `thread_id` / `history_digest` (резерв), `answer_class_hint`; в ответе `answer_class`, `evidence_summary`, `warnings`, `inventory` / `quote_candidates` / `bibliography` и др.; SSE: `intent_classified`, `specialist_selected`, `tool_search_result`, `evidence_ready`, плюс существующие `tool_call` / `tool_result` / `final_answer` / `error`.
- Паритет **sync JSON ↔ SSE** для `tool_trace`: финальный стрим использует `collect_tool_trace` (как JSON-путь), со стримом `stream_mode=["updates","values"]` в `langgraph`.
- Envelope: `science_graphrag/agent/chat_envelope.py` + наполнение в `science_graphrag/agent/runtime.py` (`AgentRunOutput`).
- UI: `ui/src/services/agent/agentStreamParse.js`, `ui/src/hooks/useAgentStream.js`, `ui/src/services/research/queryModel.js` (`normalizeQueryResponse` пробрасывает поля), `useAskSubmit.js`.

**Wave B — догон CH1 (комментарий):**
- В `build_chat_envelope` добавлены предупреждения: `weak_evidence`, `no_quote_found`, `graph_only`, `text_only` (плюс `no_workspace`); тесты расширены в `tests/test_chat_envelope.py`.
- Typed UI: `ui/src/components/work/ChatTypedBlocks.jsx` + секции в `AskAnswerPanel.jsx`; в `AskPanel` в `details` тёрна сохраняются `inventory` / `quote_candidates` / `bibliography` / `warnings` для истории в `ChatMessageThread`.
- **`relation_trace` / `idea_suggestions`** по-прежнему не заполняются в envelope (заготовка под CH6/CH7).

**Тесты:** `tests/test_api_agent_v2_stream_parity.py`, `ui/src/services/agent/agentStreamParse.test.js`, `tests/test_chat_envelope.py` (расширен Wave B). Дополнительно к §1.1: опциональные live-прогоны — `scripts/live_check/agent_v2_http.py`, `tests/live/test_agent_v2_http_optional.py` (при заданном `AGENT_LIVE_BASE`).

**Goal:** зафиксировать продуктовый контракт нового research chat.

**Exact deliverable:**
1. request/response spec
2. answer class enum
3. SSE event vocabulary v1
4. 2-3 canonical payload examples

**Out of scope:**
1. specialist split
2. tool search engine
3. long-context compression policy implementation

**Сделать:**
1. описать `thread-aware` request schema;
2. зафиксировать `answer_class`;
3. определить typed payloads для inventory / relation / quote / bibliography / ideation;
4. описать SSE event taxonomy.

**Основные файлы:**
1. `docs/specs/` новый spec
2. `science_graphrag/api/agent_v2.py`
3. `ui/src/hooks/useAgentStream.js`
4. `ui/src/components/work/ChatMessageThread.jsx`

**Acceptance:**
1. backend и UI используют один event vocabulary;
2. новый контракт обратно совместим с простым `answer`;
3. есть тесты на parse/normalize событий.

### Wave CH2 — Tool taxonomy v1

**Статус:** **DONE (Wave A, 2026-04-26)**; **частично усилено Wave B** — см. комментарии.

**Сделано в репо (кратко):**
- Каталог / papers: `workspace_overview`, `workspace_list_papers`, `paper_lookup`, `paper_metadata`, `paper_authors`, `paper_counts` в `science_graphrag/agent/tools/workspace_paper_tools.py` (сборка через `build_workspace_paper_langchain_tools`); подключение в `build_retrieval_tools` (`science_graphrag/agent/tools/__init__.py`).
- Цитаты / evidence: `paper_quote_search` (Qdrant chunks + embeddings, `quote_candidates` в payload).
- Библиография: детерминированный GOST-лайн `science_graphrag/agent/bibliography/gost.py`, инструмент `format_bibliography_gost`.
- `cypher_query` / graph tools без изменения роли: остаётся в `graph_agent`, не default path для CH2-сценариев выше.
- `tool_trace` / `ToolCallTrace` — совместимы с существующими eval-метриками; новые имена тулов — в логике shortlist/кэша подграфов.

**Тесты / заметка:** `tests/test_tool_search.py` (косвенно покрывает наличие `format_bibliography_gost` в наборе). Отдельный глубокий e2e «без cypher» — на усмотрение ночных/ручных прогонов.

**Wave B — догон CH2 (комментарий):**
- `paper_quote_search`: при сбое эмбеддинга/Qdrant — payload с `error: "qdrant_unavailable"`, без падения графа.
- `format_bibliography_gost`: в ответе `bibliography.filtered_work_ids`, `warnings` при отфильтрованных `work_id`; GOST-строка расширена полями `event`, `pages` (см. `agent/bibliography/gost.py`, `tests/test_bibliography_gost.py`).
- Осталось из долга Wave A: **не** обёрнуты все Neo4j-вызовы в остальных catalog-tools в единый `try/except` (как у quote); лимиты по-прежнему захардкожены; разбиение `workspace_paper_tools.py` — backlog.

**Goal:** уйти от "6 generic tools" к продуктовой research taxonomy.

**Exact deliverable:**
1. inventory/catalog tools
2. quote/evidence tools
3. bibliography formatter contract
4. raw cypher policy as advanced tool

**Out of scope:**
1. deferred loading
2. full multi-turn memory
3. ideation grounding

**Сделать:**
1. добавить paper/catalog tools;
2. добавить quote/evidence tools;
3. вынести bibliography formatter;
4. отделить domain tools от raw cypher;
5. сохранить `tool_trace` совместимым.

**Основные файлы:**
1. `science_graphrag/agent/tools/`
2. `science_graphrag/agent/tools/__init__.py`
3. `science_graphrag/agent/trace.py`
4. `tests/agent/`

**Acceptance:**
1. inventory, authors, quote и bibliography use cases покрываются без raw cypher;
2. cypher остаётся guarded advanced tool;
3. eval/fixtures можно писать на tool-call level.

### Wave CH3 — Tool manifest and tool search

**Статус:** **DONE (Wave A, 2026-04-26)** (rule-based v1, не LLM-discovery); **дополнено Wave B** — см. комментарии.

**Сделано в репо (кратко):**
- `science_graphrag/agent/tool_manifest.py` — метаданные (`family`, `tags`, `risk`, `scope`, `specialist`, `requires_workspace`) для тулов Wave A.
- `science_graphrag/agent/tool_search.py` — rule-based `shortlist_tools_for_specialist` с fallback на полный набор и подмешиванием `idea_search` + `summarize_workspace` для retrieval, чтобы shortlist не «схлопывался» до одного тулa.
- Интеграция в **специалистов**, а не в корневой supervisor: динамический кэш скомпилированных ReAct-subgraph по ключу `(tool names)` в `retrieval_agent.py` / `graph_agent.py`; события `tool_search_result` уходят в `AgentState.debug_events` (редьюсер `add`) и дублируются в SSE (`type: tool_search_result` при `values`).
- Rollout: `SCIENCE_GRAPHRAG_AGENT_RULE_TOOL_SEARCH_ENABLED` в `science_graphrag/config.py` (см. `.env.example`); при `false` — полный набор тулов у специалиста.
- `supervisor.py` не дорабатывался отдельно под CH3: маршрутизация по-прежнему LLM-токеном; «координация shortlist» перенесена внутрь specialist nodes (см. acceptance roadmap: прагматичный срез).

**Wave B — догон CH3 (комментарий):**
- `writer_agent`: вызов `shortlist_tools_for_specialist` + `debug_events` с `tool_search_result` (для `writer_agent` — `reason: writer_minimal_set`, один `final_answer`).
- **Анти-дрейф:** `tests/test_tool_manifest_sync.py` — имена из `build_tool_registry` совпадают с `TOOL_MANIFEST` (14 тулов; обновлён `tests/agent/test_tools_registry.py`).
- `test_tool_search.py` расширен (writer skip, graph/retrieval edge cases). Магические пороги в `tool_search.py` **не** вынесены в конфиг (остаётся долгом).
- **Wave C note (2026-04-27):** введён `TurnPolicy` как coordinator-level contract перед specialist routing. Это отдельный уровень от `tool_search`: он решает, можно ли вообще запускать tools на текущем turn (`no_tools` / `clarify` / `allow_tools`). Rule/regex implementation внутри `turn_policy.py` — временный v0 guardrail; не расширять его как основной способ понимания user intent. Следующий этап должен заменить его на hybrid/LLM classifier, сохранив контракт и trace/SSE vocabulary.

**Тесты:** `tests/test_tool_search.py`, `tests/test_tool_manifest_sync.py`.

**Goal:** внедрить deferred tool loading.

**Exact deliverable:**
1. `tool_manifest`
2. shortlist-based `tool_search`
3. coordinator integration for selected tools only

**Out of scope:**
1. LLM-based tool search
2. specialist subgraph isolation
3. advanced memory compression

**Сделать:**
1. ввести `tool_manifest`;
2. сделать `tool_search`;
3. coordinator видит только shortlist/relevant schemas;
4. tags/capabilities для tools становятся first-class metadata.

**Основные файлы:**
1. новый `science_graphrag/agent/tool_manifest.py`
2. новый `science_graphrag/agent/tool_search.py`
3. `science_graphrag/agent/graph/supervisor.py`

**Acceptance:**
1. token budget на system/tool context снижен;
2. tool selection становится объяснимой;
3. trace показывает, почему был выбран tool subset.

### Wave CH4 — Multi-turn state and session memory

**Статус:** **DONE (Wave B: in-process v1; Wave Next: optional Redis persistence, 2026-04-26)** — см. комментарии.

**Сделано в репо (Wave B v1 + Wave Next):**
1. Request: `thread_id`, `history_digest` (JSON-строка или массив dict) — см. [`docs/specs/agent-chat-v1.md`](../specs/agent-chat-v1.md); парсинг в `agent_v2.py`, прокидка в `RetrievalAgent.run()` и в `build_initial_agent_state()`.
2. `AgentState`: `thread_id`, `session_summary`, `answer_class`, `history_digest`; первое пользовательское сообщение собирается через `format_user_with_memory` (`agent/context/session_store.py`); **Wave Next:** при наличии capsule в store — префикс `<workspace_capsule>` (см. `session_backend` / `graph/state.py`).
3. После тёрна: `build_turn_digest` + `update_session_after_turn` через `SessionMemoryBackend` (**Wave B:** in-process по умолчанию; **Wave Next:** опционально **Redis** с TTL, `configure_session_memory_backend` в `api/main.py`); при SSE — событие `context_compacted`; в `collect_tool_trace` при наличии `thread_id` — шаг `session_init`.
4. UI: `useAskSubmit` передаёт `threadId` (= `activeSessionId`) и `buildAgentHistoryDigest(history)`; уникальные id тёрнов в `askSessionState.js` (`newTurnId`). Явное поле `backendThreadId` в сессии **не** введено: договорённость «session id = thread id для API». **Wave Next:** блок server session memory в `AskAnswerPanel`, `run_metadata` в `queryModel` / `AskPanel` details; тесты `useAskSubmit`, `ChatMessageThread` (empty state), расширение `AskAnswerPanel` / `researchApi`.

**Основные файлы:** `science_graphrag/agent/graph/state.py`, `science_graphrag/agent/context/*`, `science_graphrag/agent/runtime.py`, `science_graphrag/api/agent_v2.py`, `science_graphrag/api/main.py`, `ui/src/components/work/useAskSubmit.js`, `ui/src/components/work/askSessionState.js`, `ui/src/components/work/AskPanel.jsx`, `ui/src/components/work/AskAnswerPanel.jsx`, `ui/src/services/research/queryModel.js`.

**Тесты:** `tests/test_context_session.py`, `tests/test_session_redis_backend.py` (опционально при Redis), правки `tests/test_api_agent_v2_stream_parity.py`, `tests/test_api_agent_v2_json_thread.py`, `tests/live/test_agent_v2_http_optional.py` (sync CH4 gate), `eval/chat_agent` (`python -m eval.chat_agent`).

**Осталось (после Wave Next):**
- Регрессионные e2e multi-turn против **реального** LangGraph+LLM (сейчас сильный слой — in-process + live gate).
- Альтернативный backend session store (Postgres) при необходимости операционной политики.

**Acceptance (Wave B):**
1. Follow-up в том же `thread_id` получает префикс `<session_memory>` из серверного store (клиент шлёт тот же id сессии).
2. Digest — компактный JSON, не сырые tool outputs.
3. Базовые unit-тесты на store/digest есть; полный e2e multi-turn — впереди.

**Wave C — Chat hardening (post–Wave B, CH5 foundation prep):** синхронизация [`docs/specs/agent-chat-v1.md`](../specs/agent-chat-v1.md) со статусом Wave B; единый контракт `warnings` (в т.ч. библиография) на top-level + в `bibliography`; **частично сделано:** явная политика `history_digest` → `warnings` / SSE `warning` с кодом `history_digest_invalid`; JSON-паритет с SSE по post-turn памяти через поле `session_summary_excerpt` в sync-ответе и в `final_answer`; нормализация входа для rule-based `tool_search` (без шума от `<session_memory>` / digest XML); расширенный regression: `session_init`, `context_compacted`, follow-up в том же `thread_id`, rich envelope parity JSON↔SSE; UI: `evidence_summary`, i18n warnings, SSE `context_compacted` / `warning` / `tool_search_result`, опционально `answerClassHint`; split `workspace_paper_tools.py` по backlog; optional live gate `scripts/live_check/agent_v2_http.py`. **Wave Next дополнил:** optional Redis session store, расширенный `compaction` в SSE/sync, UI session memory block, live gate для sync JSON + `run_metadata.compaction`. **По-прежнему не в этом slice:** полный CH5 (LLM/capsules из стора, boundary audit), CH6–CH7.

### Wave CH5 — Multi-level context compression

**Комментарий (Wave Next v1):** **turn_digest** + rolling summary остаются базой; добавлены **политика `kinds` / `digest_count` / `boundary` в SSE и sync `run_metadata`**, детерминированный **workspace_capsule** в промпте, расширенные smoke/fixtures (`tests/eval/test_chat_context_compaction_smoke.py`) и runner `python -m eval.chat_agent`. **Ещё не сделано:** topic/paper capsules с обращением к сторам, coordinator-triggered compaction, full compact boundary с отдельным audit trail, тяжёлый eval runner на траектории LLM.

**Goal:** добавить обязательный compact stack.

**Сделать (остаток после Wave Next v1):**
1. ~~`turn_digest` + триггеры / eval smoke / sync metadata~~ **частично закрыто Wave Next** (см. комментарий выше); дальше — coordinator-triggered digest и артефакты в trace/debug_events по отдельному дизайну.
2. ~~`rolling_session_memory` как отдельный слой в `compaction.kinds`~~ **минимально закрыто Wave Next** (`rolling_memory` в `kinds` по порогу digest count); расширение семантики — позже.
3. **workspace/paper/topic capsules** из стора / LLM — **не** сделано (сейчас только детерминированный workspace capsule из intent-ов).
4. **`full compact boundary`** с audit trail — **не** сделано (есть только `boundary.status: candidate` при заполнении окна digest).

**Основные файлы:**
1. `science_graphrag/agent/context/` (создан Wave B — расширять)
2. `science_graphrag/agent/graph/supervisor.py`
3. `science_graphrag/agent/llm/chat.py`

**Acceptance:**
1. длинные диалоги не деградируют по latency/token cost;
2. summary artifacts доступны для trace/debug;
3. есть eval family `chat_context_compaction_v1`.

### Wave CH6 — Specialist split

**Goal:** превратить логические домены в реальные specialists/subgraphs.

**Сделать:**
1. выделить `catalog_specialist`
2. усилить `graph_specialist`
3. выделить `citation_specialist`
4. выделить `bibliography_specialist`
5. ideation пока можно оставить lightweight specialist

**Основные файлы:**
1. `science_graphrag/agent/graph/nodes/`
2. `science_graphrag/agent/graph/supervisor.py`
3. `science_graphrag/agent/runtime.py`

**Acceptance:**
1. supervisor не перегружен всеми tools сразу;
2. relation/quote/bibliography use cases показывают cleaner tool traces;
3. recursion/budget policies задокументированы.

### Wave CH7 — Grounded ideation

**Goal:** встроить ideation как first-class use case, не как отдельный полуизолированный endpoint.

**Сделать:**
1. связать `idea_assist` flow с chat runtime;
2. добавить novelty/support evidence checks;
3. ввести structured `idea_suggestions` payload;
4. явно различать grounded idea vs speculative suggestion.

**Основные файлы:**
1. `science_graphrag/api/idea_assist.py`
2. `science_graphrag/agent/idea_workflow.py`
3. новый ideation specialist/tool layer

**Acceptance:**
1. идеи опираются на corpus evidence;
2. UI показывает supporting papers;
3. benchmark `chat_ideation_grounded_v1` зелёный честно.

### Wave CH8 — Bibliography and exports

**Комментарий (Wave B):** GOST formatter и explicit `bibliography` в API уже были (CH2/A); Wave B добавил **UI** (список + копирование в `BibliographyBlock`), предупреждения по filtered ids, расширение строки GOST. **Не сделано:** reading queue builder, отдельный benchmark `chat_bibliography_gost_v1`.

**Goal:** закрыть "собери мне литературу" продуктово.

**Сделать:**
1. GOST formatter (есть + доработки Wave B — см. CH2); дальше — книги/тома и т.д. по продукту
2. reading queue builder;
3. explicit bibliography payload in API (**есть** в envelope; при необходимости — расширить схему)
4. copy/export affordances in UI (**частично Wave B:** копирование списка в `BibliographyBlock`)

**Основные файлы:**
1. новые formatter/export modules
2. `science_graphrag/api/agent_v2.py`
3. `ui/src/components/work/AskAnswerPanel.jsx`
4. `ui/src/components/work/ChatMessageThread.jsx`

**Acceptance:**
1. bibliography response не является просто plain text paragraph;
2. output можно копировать как готовый список;
3. benchmark `chat_bibliography_gost_v1` существует.

### Wave CH9 — Eval + rollout hardening

**Goal:** сделать систему управляемой, честной и release-ready.

**Сделано (2026-04-27, v0):**
- Эталонная область + pre-flight audit + roadmap harness с сохранением `tool_trace` / `phoenix_trace_id` и suite summary — см. §10.4 и [`agent-chat-tools-and-trace-audit-master-2026-04-28.md`](../agent-chat-tools-and-trace-audit-master-2026-04-28.md).
- Root `agent.query` + `phoenix_trace_id` уже дают корреляцию live case → Phoenix; это baseline observability, не финальное качество span tree.

**Сделать:**
1. benchmark families CH;
2. trace dashboards for agent chat;
3. failure policies and warnings;
4. nightly smoke on selected researcher queries;
5. UX polish stream events / warnings / partial answers.
6. **Coordinator intent evals:** отдельный набор кейсов для `TurnPolicy` / classifier (`small_talk`, `meta`, `ambiguous`, `inventory`, `quote`, `relation`, `bibliography`, `ideation`) с обязательными проверками `tool_policy`, `answer_class`, `route_hint`, отсутствия tool calls на `no_tools` и safe fallback при невалидном structured output.
7. **Phoenix span tree gate:** закрыть X2.2–X2.9 — TOOL-спаны для всех domain tools, RETRIEVER для Qdrant search, LLM attribution для supervisor/classifier/writer, deterministic `InMemorySpanExporter` smoke и best-effort Phoenix snapshot.
8. **Trace correlation metrics:** в roadmap runner добавить diagnostics уровня observability: `tool_trace_vs_span_match`, `missing_tool_spans`, `missing_retriever_spans`, `missing_llm_token_attrs`.

**Acceptance:**
1. видно, где agent hallucinated or lacked evidence;
2. honest downgrade rules работают;
3. rollout можно включать по feature flag;
4. coordinator gate не деградирует в словарь ключевых фраз: новые языковые варианты закрываются evals + classifier behavior, а не бесконечным расширением regex.
5. **baseline workspace + harness:** один задокументированный `workspace_id` для chat regression; pre-flight audit не даёт suite стартовать на `blocked`; для каждого curated кейса сохраняются артефакты, достаточные для сопоставления с Phoenix (см. trace-audit checklist §4).
6. **Phoenix observability:** answer-quality PASS и observability PASS разделены; live baseline может быть зелёным по метрикам ответа, но красным по span coverage.

---

## 12. Recommended delivery order

> Идентификаторы волн `CH1..CH9` нужны для ссылки и трекинга, но **не обязаны совпадать с фактическим порядком доставки**.

Если делать прагматично, то порядок такой:

1. **CH1** contracts
2. **CH2** tool taxonomy
3. **CH3** tool search
4. **CH4** multi-turn state
5. **CH5** compression
6. **CH5.5 / Coordinator Gate hybridization**: заменить `TurnPolicy` v0 regex/rules на hybrid/LLM classifier with structured output + evals, сохранив no-tools/direct writer path and safe fallbacks
7. **CH5.6 / Phoenix Agent Tracing**: закрыть X2 best-practice span tree до расширения specialist graph, чтобы новые ветки сразу наследовали наблюдаемость
8. **CH6** specialist split
9. **CH8** bibliography
10. **CH7** grounded ideation
11. **CH9** eval hardening

Почему так:

1. без CH1-CH3 система останется "чатом вокруг старых tools";
2. без CH4-CH5 не получится длинный research dialogue;
3. без hybrid coordinator gate новые specialists будут получать те же ложные входы (`small_talk` / `ambiguous` / meta turns) и воспроизводить старый дефект на новом уровне;
4. без Phoenix Agent Tracing specialist split усложнит отладку: появятся новые ветки, но не будет видно, где потерялись tool/retriever/LLM шаги;
5. bibliography легче делать после catalog/retrieval tool layer;
6. ideation стоит поднимать только когда уже есть grounding and memory;
7. eval/hardening должны сопровождать всё, но как отдельная closing wave удобно собрать в CH9.

---

## 13. File hot spots in current repo

### Backend

1. `science_graphrag/api/agent_v2.py`
2. `science_graphrag/agent/graph/state.py`
3. `science_graphrag/agent/graph/supervisor.py`
4. `science_graphrag/agent/graph/nodes/retrieval_agent.py`
5. `science_graphrag/agent/graph/nodes/graph_agent.py`
6. `science_graphrag/agent/graph/nodes/writer_agent.py`
7. `science_graphrag/agent/tools/`
8. `science_graphrag/agent/llm/chat.py`
9. `science_graphrag/agent/runtime.py`

### Frontend

1. `ui/src/components/work/ChatComposer.jsx`
2. `ui/src/components/work/ChatMessageThread.jsx`
3. `ui/src/components/work/AskAnswerPanel.jsx`
4. `ui/src/components/work/askSessionState.js`
5. `ui/src/components/work/useAskSubmit.js`
6. `ui/src/hooks/useAgentStream.js`
7. `ui/src/pages/ChatPage.jsx`

### Evals

1. `eval/agent_tools/runner.py`
2. `eval/agent_tools/metrics.py`
3. новые `eval/chat_*`
4. `tests/agent/`
5. `tests/eval/`

---

## 14. Key product decisions

### Decision A

**Чат должен быть thread-aware на backend**, а не только на UI.

### Decision B

**Tool registry должен стать domain-shaped**, а не generic search-shaped.

### Decision C

**Tool search обязателен** после расширения набора tools.

### Decision D

**Нужно минимум три уровня context compression**, иначе long-form research chat не взлетит.

### Decision E

**Raw cypher остаётся advanced/guarded tool**, а не главным API для большинства вопросов.

### Decision F

**Ideation и bibliography должны быть встроены в общий chat runtime**, а не жить полностью отдельно.

### Decision G

**Coordinator — first-class runtime role, но не keyword dictionary.** `TurnPolicy` остаётся стабильным интерфейсом (`conversation_intent`, `answer_class`, `tool_policy`, `route_hint`, `reason/confidence`), а regex/rule implementation допускается только как narrow deterministic guardrail. Целевой coordinator — hybrid: deterministic prefilters for obvious cases, structured LLM classifier for ambiguous/research intent, eval-governed rollout, safe fallback to clarification rather than retrieval.

### Decision H

**Phoenix trace tree — release artifact, а не optional debug.** Для agent chat недостаточно вернуть `phoenix_trace_id`: в Phoenix должен быть читаемый turn-level trace `agent.query → policy/supervisor/specialist → tool/retriever/LLM`, коррелирующий с `tool_trace`. Новые specialists и tools принимаются только с observability contract или явным backlog item.

---

## 15. Open questions

### Blocking before CH1-CH3

**Снято / частично снято (Wave A, 2026-04-26):** для первой поставки зафиксирован **rule-based** `tool_search` (см. `science_graphrag/agent/tool_search.py`); thread/history в запросе — **optional + reserved** (`docs/specs/agent-chat-v1.md`); GOST-форматирование в агенте — **детерминированное** (`agent/bibliography/gost.py` + tool); набор typed payloads в CH1 согласован со спекой (ideation payload — заготовка под CH7).

**Обновление Wave B (2026-04-26):**
1. **tool_search:** остаётся **rule-based v1**; LLM/hybrid — отложено (CH9+ / отдельное решение).
2. **Контракт thread-aware:** канон — **`thread_id` + опциональный `history_digest`** (клиентский компакт последних тёрнов) + серверный **`session_summary`** из backend store (**Wave B:** in-process; **Wave Next:** опционально Redis при `SCIENCE_GRAPHRAG_AGENT_SESSION_MEMORY_BACKEND=redis`); полная history по-прежнему не шлётся целиком.
3. **Bibliography:** по-прежнему **детерминированный** GOST + опциональные поля карточки; LLM-fallback не вводился.
4. **Typed payloads:** в UI и envelope используются **`inventory`, `quote_candidates`, `bibliography`**; **`relation_trace`** в envelope пока не заполняется.
5. **Coordinator gate:** `TurnPolicy` v0 уже отделил no-tools/clarify/allow-tools от specialist routing, но реализация на regex/rules не должна становиться постоянной. Открыто: structured-output schema, confidence threshold, fallback policy, cost/latency model and eval gates for hybrid/LLM classifier.
6. **Phoenix agent tracing:** `agent.query` / `phoenix_trace_id` есть, но остаются открыты X2.2–X2.9: полный TOOL coverage, RETRIEVER spans, LLM attribution tests, trace-audit gate.

### Can wait until CH4+

1. Хранить ли `rolling_session_memory` только в памяти/сессии или persist в backend store? **→ Wave Next: Redis persistence опционально; по умолчанию локально — `memory`.** Postgres и прочие backend — открыто при продуктовых требованиях.
2. Насколько глубоко graph specialist должен поддерживать path explanation already in v1?
3. Стоит ли ideation specialist запускать как side-agent/fork, чтобы не загрязнять основной reasoning loop?
4. Нужен ли отдельный "reader grounding mode" для вопросов, жёстко ограниченных одной статьёй?

---

## 16. Recommendation

Следующий практический шаг: **не начинать с "полного multi-agent rewrite"**, а открыть серию небольших PR/волн:

1. ~~spec + answer classes;~~ **сделано (Wave A / CH1)**; ~~warnings + typed UI в продукте~~ **частично догнано Wave B**
2. ~~tool taxonomy;~~ **сделано (Wave A / CH2)**; ~~structured errors / bib warnings / GOST event+pages~~ **Wave B (частично)**
3. ~~tool manifest/tool search;~~ **сделано (Wave A / CH3)**; ~~writer shortlist + manifest sync test~~ **Wave B**
4. ~~multi-turn + session memory (v1);~~ **сделано (Wave B / CH4 v1 in-process)**; ~~optional Redis persistence~~ **сделано (Wave Next)** — e2e против реального LLM без моков — дальше
5. ~~CH5 compaction policy v1 (kinds, capsule, boundary hints)~~ **сделано (Wave Next)**; полный CH5 (LLM capsules, boundary audit, coordinator triggers) — **следующий крупный шаг**
6. **Coordinator Gate hybridization:** `TurnPolicy` v0 уже создал нужный seam, но следующий практический шаг — убрать keyword-heavy intent routing из роли основного механизма: добавить structured-output classifier, confidence, eval runner and rollout flag, сохранив no-tools writer path and safe fallback to clarification.
7. **Phoenix Agent Tracing:** перед CH6 закрыть span tree contract: all-domain TOOL wrapper, RETRIEVER for Qdrant, LLM attribution tests, `tool_trace`↔Phoenix audit.

Это даст работающий research chat evolution path, сохраняя совместимость с уже существующими `LangGraph`, `SSE`, `tool_trace`, Phoenix и текущим UI чата.
