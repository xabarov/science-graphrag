# Промпты для Nano Banana под слайды защиты

**Проект:** `Интеллектуальная система поддержки научного исследования на основе GraphRAG`  
**Курс:** `NLP. Advanced`  
**Связанный HTML-черновик:** `docs/report/nlp-advanced-defense-slides.html`  
**Назначение документа:** дать готовые промпты для генерации ключевых визуалов так, чтобы они выглядели как единая презентация, а не как набор разнородных картинок.

---

## Общий визуальный язык

Для всех генераций лучше держать единый стиль:

- светлый академический фон;
- ощущение `research / editorial / premium presentation`;
- без кричащих градиентов и без типичного AI-glossy вида;
- чистые блоки, тонкие линии, много воздуха;
- акцентные цвета: тёплый терракотовый, тёмный графит, мягкий сине-серый;
- визуал должен выглядеть как часть защиты по computer science / NLP, а не как маркетинговый баннер.

## Обязательные содержательные правила

### 1. Текста в изображениях должно быть как можно меньше

Главное правило: `Nano Banana` лучше использовать для **схем, форм, карточек, композиции и визуальной логики**, а не для набора подписей.

Поэтому:

- **не писать заголовок слайда внутри картинки**;
- **не писать длинные русские подписи**;
- **не использовать предложения внутри изображения**;
- лучше делать визуал проще и чище, даже если он становится более абстрактным.

### 2. Если текст всё же нужен, он должен быть минимальным

Приоритет такой:

1. вообще без текста;
2. короткие общие подписи на английском;
3. только в крайнем случае короткие технические названия.

Подходящие варианты текста внутри картинки:

- `Input`
- `Extraction`
- `Storage`
- `Graph`
- `Retrieval`
- `Supervisor`
- `Answer`
- `Citations`
- `Methods`
- `Datasets`
- `Latency`
- `Quality`

Неподходящие варианты:

- длинные русские заголовки;
- предложения;
- пояснительные абзацы;
- метрика + длинная интерпретация в одной карточке.

### 3. Использовать только реальные метрики проекта

В визуалах нельзя придумывать абстрактные KPI вроде `accuracy`, `overall score`, `confidence`, `AI quality`, `reliability index`, если их нет в нашем отчёте.

Если на картинке появляются метрики или подписи вокруг метрик, нужно опираться на реальные обозначения из проекта:

- `P / R / F1`;
- `ROUGE-L`;
- `token containment`;
- `forbidden_violation_count`;
- `hit_count`;
- `recall`;
- `precision`;
- `latency_p95`;
- judge score `4.8/6`;
- `ARI`;
- `failed_count`;
- `trust_signal`.

Если нужен слайд именно про результаты, лучше использовать такие проектные сочетания:

- `Методы (L2) — P / R / F1`;
- `Датасеты (L2) — P / R / F1`;
- `Graph CITES (Neo4j) — P / R / F1`;
- `workspace_scoped_live — forbidden_violation_count = 0`;
- `hybrid_ablation_live — hit_count = 5/5`;
- `multihop_v2 — recall ≈ 0.667, precision низкая`;
- `claims_paraphrase — macro P / R / F1`;
- `agent_tools_live — latency_p95 = 25 983 ms, judge = 4.8/6`;
- `dedup — ARI = 0.88–1.00`.

### Что важно

1. Большую часть текста лучше держать в `HTML`, а не внутри картинки.
2. Для `Nano Banana` лучше просить:
   - схему;
   - инфографику;
   - clean explanatory visual;
   - diagram-style composition.
3. Лучше избегать длинного текста внутри изображения, потому что потом это труднее править.

---

## Глобальный base prompt

Этот base prompt можно добавлять к каждому промпту:

```text
Create a clean academic presentation visual for a master's-level NLP / GraphRAG defense. 
Style: editorial, premium, minimal, research-oriented, light background, subtle paper texture, thin dividers, soft shadows, strong information hierarchy, no flashy gradients, no neon, no generic AI art look.
Palette: warm off-white background, dark graphite text, muted terracotta accent, cool gray-blue secondary accent.
Composition: highly legible, balanced, spacious, suitable for embedding into a 16:9 HTML slide.
Prefer diagrammatic clarity over decoration. Avoid clutter. Avoid long paragraphs of text.
Avoid text-heavy visuals.
Do not place the slide title inside the image.
If labels are necessary, keep them extremely short and prefer simple English words or short technical terms, not sentences.
Do not invent generic metrics. If metrics are shown, use only real project metrics such as P / R / F1, ROUGE-L, forbidden_violation_count, hit_count, recall, precision, latency_p95, ARI, failed_count, trust_signal.
```

---

## Слайд 4. Технологический стек

### Задача визуала

Показать стек как систему ролей:

- backend / runtime;
- storages;
- LLM / retrieval pipeline;
- UI / observability;
- evaluation.

### Рекомендуемый prompt

```text
Create a sophisticated 16:9 presentation infographic showing the technology stack of a scientific GraphRAG system.

The visual should organize the stack into five clean groups:
1) Backend and runtime
2) Storage layer
3) NLP / LLM pipeline
4) Interface and observability
5) Evaluation and benchmarking

Use a refined editorial style with a light academic background, thin connectors, elegant cards, subtle geometry, and restrained colors.
The composition should feel like a modern research defense slide, not a product ad.

Important:
- no excessive text
- no screenshots
- no code
- no 3D icons
- no glossy startup aesthetic

Use abstract symbolic cues for:
- Python / backend
- graph database
- vector search
- API / UI
- observability
- benchmark evaluation

Do not put the slide title inside the image.
If labels are used, keep them minimal and in simple English, for example:
- Backend
- Storage
- NLP
- UI
- Eval

The final image must look like a polished systems overview that can sit beside HTML text on a thesis defense slide.
```

### Если нужен более структурный вариант

```text
Create a clean systems infographic for a GraphRAG project technology stack.
Use five vertically aligned sections with subtle labels and minimalist symbolic illustrations:
Backend and runtime, Storage, NLP pipeline, Interface and observability, Evaluation.
Light editorial style, beige paper background, graphite lines, terracotta accents, elegant whitespace, flat diagram look.
No long text, no photorealism, no futuristic neon.
No slide title inside the image. Keep labels extremely short.
```

### Что потом вставлять в HTML

- либо целиком на слайд 4;
- либо справа от текстовых карточек как supporting visual.

---

## Слайд 5. Главная архитектурная схема

### Задача визуала

Это самый важный визуал всей защиты. Он должен объяснять pipeline:

`PDF / Markdown / Text -> normalization -> extraction -> Postgres + Neo4j + Qdrant -> supervisor -> retrieval_agent / graph_agent / writer_agent -> answer with citations`

### Критическое архитектурное ограничение

Для этого слайда нужно явно запрещать неправильную интерпретацию multi-agent части:

- ingestion pipeline и chat runtime — **разные фазы системы**;
- во время пользовательского чата **ingestion не происходит**;
- ingest готовит данные заранее и записывает их в `PostgreSQL`, `Neo4j`, `Qdrant`;
- chat runtime читает уже подготовленные данные из этих хранилищ;
- `retrieval_agent`, `graph_agent`, `writer_agent` **не общаются напрямую друг с другом**;
- между агентами **не должно быть боковых стрелок**;
- между агентами **не должно быть peer-to-peer links**;
- вся оркестрация идёт **только через `supervisor`**;
- визуально это лучше показывать как `supervisor -> agents`, а не как сеть агентов между собой;
- общая схема должна выглядеть как `offline ingest -> stores`, отдельно `online chat -> supervisor + agents -> stores -> answer`.

### Рекомендуемый основной prompt

```text
Create a high-end architecture diagram for a GraphRAG scientific research system, designed for a thesis defense slide in 16:9 format.

Show two separate phases of the system, not one continuous pipeline.

Phase 1: offline ingest
documents (PDF / Markdown / Text) ->
normalization into article markdown ->
LLM extraction pipeline ->
three storage systems (PostgreSQL, Neo4j, Qdrant).

Phase 2: online chat runtime
user query ->
supervisor / orchestrator ->
three specialized agents (retrieval agent, graph agent, writer agent) ->
read from PostgreSQL, Neo4j, Qdrant ->
final answer with citations.

The visual must be elegant, minimal, diagrammatic, and extremely legible.
Use a light academic style with muted terracotta accents, graphite text, soft paper background, fine connector arrows, subtle depth, and clear grouping.

Emphasize that:
- ingestion happens offline before chat
- chat runtime does not perform ingestion
- PostgreSQL stores operational state
- Neo4j stores graph knowledge
- Qdrant stores semantic retrieval data
- the supervisor routes between specialized agents
- the output is a grounded answer with citations
- the specialized agents do not communicate directly with each other
- there must be no direct arrows between retrieval agent, graph agent, and writer agent
- all routing goes through the supervisor only

Do not put the slide title inside the image.
If the diagram contains labels, keep them very short and preferably in English.
Examples of acceptable labels:
- Input
- Normalize
- Extract
- Postgres
- Neo4j
- Qdrant
- Supervisor
- Retrieval
- Graph
- Writer
- Citations

Avoid:
- generic corporate blue diagrams
- glossy 3D effects
- too much text
- dense technical clutter
- dark background
- fake dashboard elements
- direct connections between retrieval agent, graph agent, and writer agent
- any visual suggestion that the agents exchange messages peer-to-peer

The image should look like a polished architecture figure from a strong engineering research presentation.
```

### Вариант с акцентом на смысл, а не на бренды

```text
Create a refined architecture infographic for a research GraphRAG pipeline.
The visual should emphasize two phases rather than one continuous flow:
offline ingest on one side, online chat runtime on the other side, with shared storage systems between them.
Use functional roles rather than vendor logos:
input documents, normalization, structured extraction, operational state, graph knowledge, vector retrieval, supervisor routing, specialized agents, cited answer.
Style: light, editorial, academic, minimal, premium, clean geometry, subtle paper texture.
The specialized agents must be shown as separate nodes connected only to the supervisor, not to each other.
No slide title inside the image. If labels are used, keep them minimal.
```

### Вариант для более абстрактной и красивой схемы

```text
Create an elegant conceptual systems diagram for a GraphRAG research assistant.
Use layered blocks and directional flow to show:
offline document ingestion, knowledge extraction, shared storage systems, online supervisor routing, specialized reasoning agents, grounded answer generation.
Make it visually memorable but still rigorous and academic.
No clutter, no neon, no infographic overkill.
Do not draw lateral links between specialized agents; they should connect only through the supervisor.
Do not suggest that ingestion happens during the chat phase.
No slide title inside the image. If the image includes labels, use only a few short labels.
```

### Что важно проверить после генерации

1. Стрелки читаются слева направо.
2. Не потерялась тройка `PostgreSQL / Neo4j / Qdrant`.
3. Видно, что `supervisor` расположен после storage layer.
4. Финальный блок явно намекает на `answer with citations`.
5. Между `retrieval_agent`, `graph_agent`, `writer_agent` нет прямых связей.
6. Не создаётся впечатление, что ingestion выполняется во время чата.

---

## Слайд 6. Продукт / реализация

### Когда использовать Nano Banana

Если не хочется делать только реальный screenshot, можно сделать supporting visual:

- абстрактный UI composition;
- editorial collage of implementation artifacts;
- композицию "interface + graph + code + evaluation".

### Prompt для supporting visual

```text
Create a clean editorial collage for a scientific software project presentation.
The collage should suggest a real implemented system without looking like marketing material.

Visually combine:
- a research interface screen
- graph structure fragments
- code / module hints
- evaluation artifacts

The result should feel like a serious engineering project with both product and research components.
Style: light academic background, layered paper cards, subtle shadows, muted terracotta and graphite palette, minimal and premium.

Avoid fake UI overload, unreadable tiny text, neon colors, and generic AI dashboard aesthetics.
Do not place the slide title inside the image. If small captions are added, keep them minimal.
```

### Но предпочтительный вариант

Для слайда 6 лучше всё же использовать реальные скриншоты проекта, а `Nano Banana` здесь нужен только как вспомогательный фон/коллаж, если захочется визуально усилить композицию.

---

## Слайд 7. Результаты и метрики

### Задача визуала

Не заменять таблицу из HTML, а дать supporting visual вокруг идеи:

- извлечение структуры;
- retrieval;
- graph traversal;
- agent mode;
- честная оценка.

### Prompt для метрик-visual

```text
Create a refined academic metrics visual for a GraphRAG thesis defense slide.

The image should communicate four result dimensions:
1) structured extraction quality
2) graph citation quality
3) retrieval effectiveness
4) end-to-end agent performance

If metric labels or values are shown, use only real project metrics and write the narrative labels in Russian.
Do not put the slide title inside the image.
Prefer fewer labels and more visual structure.
If text is needed, keep it short and preferably in English.
Good metric examples:
- Methods: P / R / F1 = 0.617 / 0.680 / 0.601
- Datasets: P / R / F1 = 0.790 / 0.879 / 0.792
- Graph CITES (Neo4j): P / R / F1 = 0.784 / 0.909 / 0.821
- workspace_scoped_live: forbidden_violation_count = 0
- hybrid_ablation_live: hit_count = 5/5
- multihop_v2: recall ≈ 0.667, precision low
- claims_paraphrase: macro P / R / F1
- agent_tools_live: latency_p95 = 25 983 ms, judge = 4.8/6

Do not use invented or irrelevant metrics such as overall score, accuracy, AUC, BLEU, NDCG, confidence index, reliability score.

Use minimalist metric cards, subtle separators, diagram-like presentation, and a strong editorial layout.
This should look like a serious research results slide support visual, not a startup KPI dashboard.

Style:
- light warm background
- graphite typography
- terracotta accent
- muted gray-blue secondary elements
- clean hierarchy
- spacious composition

Avoid neon charts, glossy dashboard tiles, fake analytics screens, and excessive decoration.
```

### Prompt для акцента на honest evaluation

```text
Create a conceptual research presentation visual about honest evaluation in a GraphRAG project.
Show the contrast between easy benchmarks and strict benchmarks using elegant minimal diagram language.
The visual should suggest that strong systems must expose weaknesses instead of hiding them.
Use a restrained editorial academic style, light background, clean geometry, muted terracotta accent, and no dramatic or flashy effects.
Do not put the slide title inside the image.
If captions are present, use short English phrases like:
- Easy benchmark
- Strict benchmark
- Honest eval
- Strengths
- Limits
Do not show invented benchmark metrics; prefer terms like P / R / F1, failed_count, trust_signal, latency_p95 only if metrics are needed.
```

### Как использовать

- либо вставить как фон/поддержку справа от HTML-метрик;
- либо взять отдельный crop для блока про `claims_paraphrase` и честную оценку.

---

## Слайд 8. Демо / видео

### Что можно сгенерировать

Обычно на этом слайде лучше реальный стоп-кадр из видео, но если нужен placeholder-постер, можно сделать poster image.

### Prompt для poster frame

```text
Create a clean poster-style presentation visual for a GraphRAG system demo slide.
The image should suggest a live scientific question-answering workflow with citations, graph reasoning, and retrieval over papers.
Use a premium academic style, light background, restrained editorial composition, subtle interface hints, and clear focal hierarchy.
No fake futuristic AI assistant face, no neon holograms, no sci-fi clichés.
Do not put the slide title inside the image. If there is any caption text, keep it minimal.
```

---

## Негативные указания, которые полезно добавлять

Если генерации начинают уходить в слишком "AI-looking" стиль, полезно добавлять:

```text
Avoid neon gradients, futuristic holograms, purple-blue startup visuals, generic AI dashboard aesthetics, glossy 3D objects, excessive icons, photorealistic robots, unreadable microtext, and cluttered infographic composition.
```

---

## Практика работы

### Рекомендуемый порядок

1. Сначала сгенерировать `слайд 5` как главный visual.
2. Потом `слайд 4` как secondary visual.
3. Потом решить, нужен ли отдельный visual для `слайда 7`.
4. Для `слайда 8` использовать либо реальный стоп-кадр, либо очень нейтральный poster frame.

### Как выбирать лучший результат

Выбирать не самый "красивый", а тот, который:

- быстрее всего читается;
- не отвлекает от твоего устного рассказа;
- не ломает академический тон защиты;
- хорошо сочетается с текущим `HTML`.

---

## Следующий шаг после генерации

После того как будут готовы картинки:

1. сохранить их в `docs/report/assets/` или соседнюю папку для презентации;
2. вставить их в `docs/report/nlp-advanced-defense-slides.html`;
3. при необходимости ослабить часть текста на соответствующих слайдах, если visual уже несёт смысл.
