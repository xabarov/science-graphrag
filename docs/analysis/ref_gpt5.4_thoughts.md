Да, **в целом вы на правильном пути**, но я бы уточнил: правильный путь — **не “делать агент ради агента”**, а **разложить задачу извлечения библиографии на несколько более простых и измеримых подзадач**, где агентность — только один из возможных механизмов оркестрации.

Сейчас по вашему описанию видно важное:

- чистые эвристики ломаются на разнообразии верстки;
- один большой LLM-вызов на весь список ссылок тоже ломается, особенно при длинном выходе и строгом формате;
- агент с тулзами уже выглядит лучше как способ **итеративно локализовать секцию**, **проверить гипотезу**, **добрать контекст**.

Но при этом в текущем виде spike, который ты показал, решает в основном задачу **оценки количества ссылок**, а не **надежного извлечения полного списка ссылок**. Это важное различие.

---

# Короткий вывод

## 1. Вы на правильном пути?

**Да, но с поправкой:**  
правильный путь — это **tool-assisted pipeline / planner-executor**, а не обязательно “полноценный автономный агент”.

Для вашей задачи я бы считал наиболее перспективной архитектуру:

1. **локализация bibliography zone**  
2. **сегментация списка ссылок на отдельные записи**
3. **нормализация / парсинг отдельных записей**
4. **валидация и дедупликация**
5. **fallback-стратегии на сложные документы**

Агент можно использовать в пунктах 1–2, но не обязательно держать его в центре всей системы.

---

## 2. Какой план работы и экспериментов?

Если коротко:  
**не пытайтесь сразу “достать весь reference list агентом”**.  
Сначала постройте **evaluation harness** и сравните несколько уровней пайплайна:

- baseline heuristics
- heuristics + LLM section locator
- heuristics + LLM segmenter
- agent with tools
- hybrid best-of pipeline

---

# Почему ваш текущий вектор разумный

У вас правильная интуиция по нескольким причинам.

## Что агентный подход реально может улучшить

### 1. Декомпозиция задачи
LLM плохо справляется, когда вы говорите ему:

> “Вот огромная статья. Найди все references и верни 84 объекта в строгой схеме JSON”.

Это тяжелая задача одновременно по:
- поиску релевантного места,
- пониманию структуры,
- длинному контексту,
- длинному структурированному ответу.

Агент с тулзами превращает это в более легкий цикл:

- найди заголовок `References`
- посмотри соседние строки
- проверь паттерн нумерации
- выдели диапазон
- затем обработай диапазон отдельно

Это намного более естественно.

### 2. Tool use лучше, чем “галлюцинация по памяти”
Если модель видит только часть текста и не может интерактивно посмотреть соседние строки, она часто додумывает структуру.  
Наличие `grep`/`get_lines`/`count_candidates` снижает это.

### 3. Снижение требований к одному ответу
Вместо одного огромного JSON можно делать:
- сначала диапазон,
- потом список raw entries,
- потом по одной / батчами нормализовать.

Это обычно заметно стабильнее.

---

# Но где я вижу главный риск

Ваш текущий вопрос формулируется как:

> “Есть идея сделать это агент + нужные тулзы”

И здесь главный риск — **перепутать инструмент с решением**.

Для reference extraction проблема почти всегда не в том, что “не хватает агентности”, а в том, что есть несколько независимых сложностей:

- разнообразная разметка references section;
- references могут быть:
  - нумерованные,
  - ненумерованные,
  - автор-год,
  - в 2 колонки,
  - слепленные OCR,
  - с переносами,
  - с footnotes / appendix contamination;
- границы записей плохо определяются;
- золотой формат выхода часто неоднозначен;
- DOI / arXiv / PMID могут быть частично присутствующими.

То есть **ядро задачи — robust segmentation and normalization**, а не просто поиск секции.

---

# Мой взгляд на целевую архитектуру

Я бы рекомендовал думать о системе так:

## Вариант целевой схемы

```text
Document
  -> Preprocess markdown/text normalization
  -> Detect candidate bibliography zones
  -> Rank/select best zone
  -> Segment zone into individual references
  -> Parse each reference into structured fields
  -> Validate / deduplicate / enrich
  -> Output bibliography objects + confidence + traces
```

## Где тут агент полезен
Агент полезен в:
- выборе candidate zone;
- выборе стратегии сегментации;
- интерактивной проверке спорных случаев.

## Где агент не обязателен
Агент не обязателен в:
- парсинге DOI;
- регулярной нормализации;
- дедупликации;
- извлечении известных паттернов;
- batched extraction per entry.

---

# Что я бы делал practically

<details>
<summary><strong>1. Сначала зафиксировать, что именно считается успехом</strong></summary>

Без этого легко потратить недели на красивый spike, который сложно оценить.

Нужно определить 3 уровня метрик:

## Уровень A: section detection
Насколько хорошо система находит блок библиографии.

Метрики:
- precision/recall по строкам или символам;
- IoU по диапазону секции;
- hit@1 для правильного candidate span.

## Уровень B: reference segmentation
Насколько хорошо блок разбивается на отдельные записи.

Метрики:
- exact match по числу записей;
- boundary F1 по началу/концу записей;
- edit-distance / overlap against gold entries.

## Уровень C: structured parsing
Насколько правильно извлекаются поля:
- title
- authors
- year
- venue
- doi
- arxiv_id

Метрики:
- field-level precision/recall/F1;
- DOI accuracy;
- title similarity.

Если у вас пока нет полного gold, начните хотя бы с:
- gold bibliography span,
- gold count,
- gold raw entries.
</details>

---

<details>
<summary><strong>2. Собрать нормальный evaluation set</strong></summary>

Это, вероятно, самый важный шаг.

Нужен набор примерно из:
- $100$–$300$ документов для быстрого iteration loop,
- желательно стратифицированных по типам.

Разбейте документы по классам:

- статьи с явным `## References`
- `Bibliography`
- `Works Cited`
- numbered references
- author-year references
- one-column / two-column extraction artifacts
- OCR noisy docs
- references split by page breaks
- appendix/footnotes contamination
- docs without bibliography
- docs with supplementary references

Для каждого документа желательно иметь:
- gold section start/end
- gold count
- по возможности gold raw reference entries

И отдельно:
- “hard set” из самых неприятных кейсов.
</details>

---

<details>
<summary><strong>3. Построить сильный deterministic baseline</strong></summary>

Прежде чем вкладываться в агента, я бы усилил baseline до хорошего уровня.  
Потому что агент чаще всего выигрывает не у хорошего baseline, а у слабого.

Что стоит добавить в baseline:

## Улучшенный section detector
Не просто regex по `References`, а scoring нескольких сигналов:

- heading match:
  - `references`
  - `bibliography`
  - `works cited`
  - `literature cited`
- proximity to end of document
- increase in citation-like density
- DOI/URL/year density
- numbered item density:
  - `^\[\d+\]`
  - `^\d+\.\s`
- author-year density:
  - lines with `$[A-Z][a-z]+,\s[A-Z]\.``
  - years like `$\(?(19|20)\d{2}\)?$`
- section termination cues:
  - `appendix`
  - `supplementary`
  - acknowledgements continuation
  - figure/table captions

## Line normalization
До поиска:
- склеить hyphenation where appropriate;
- нормализовать unicode dashes / spaces;
- убрать page headers/footers if detectable;
- пометить page boundaries.

## Candidate segmentation heuristics
Для bibliography zone:
- split on numbered starts,
- split on author-year starts,
- merge continuation lines,
- identify DOI / arXiv markers.

Уже такой baseline может резко сократить потребность в агенте.
</details>

---

# Где агент действительно может дать value

Если использовать его правильно, я бы дал ему не задачу:

> “Извлеки все ссылки”

а задачу:

> “Определи лучший диапазон строк, содержащий bibliography, и стратегию сегментации”

То есть агент должен быть **router/planner**, а не “полный extractor”.

---

# Какой агентный workflow я бы попробовал

## Вариант A: агент только для локализации секции

Тулзы:
- `search_headings(patterns)`
- `get_lines(start, end)`
- `count_reference_markers(start, end)`
- `estimate_reference_density(start, end)`
- `find_section_candidates()`

Выход:
- `start_line`
- `end_line`
- `section_type`
- `confidence`
- `reasoning_summary`

Потом уже deterministic / separate LLM stage разбирает этот кусок.

### Почему это хорошо
- короткий structured output;
- проще измерять;
- меньше ошибок формата;
- меньше токенов;
- легче дебажить.

---

## Вариант B: агент для локализации + сегментации
Тулзы:
- все из варианта A
- `preview_segment_boundaries`
- `split_numbered_references`
- `split_author_year_references`
- `merge_continuations`

Выход:
- bibliography span
- список raw entries, но лучше **не сразу в полном JSON-схеме**, а как массив строк/чанков

Затем второй этап:
- per-entry parsing

### Почему это лучше, чем один giant structured output
Потому что вы отделяете:
- “где references”
от
- “как разбить”
от
- “как распарсить запись”

---

## Вариант C: агент как fallback only
Это мой любимый вариант для production.

Основной поток:
1. deterministic parser
2. confidence scoring
3. если confidence низкий — agent-assisted recovery

### Почему это сильная стратегия
- дешево на большинстве документов;
- agent используется только там, где baseline не уверен;
- проще контролировать latency/cost.

---

# Какие тулзы я бы добавил

Ваши текущие `grep_article` и `get_lines` — нормальный старт, но для production-полезности я бы добавил более семантические инструменты.

## Must-have тулзы

### 1. `find_bibliography_candidates`
Возвращает несколько candidate spans с признаками.

Например:

```json
[
  {
    "start_line": 820,
    "end_line": 940,
    "heading": "References",
    "score": 0.91,
    "signals": {
      "heading_match": true,
      "near_document_end": true,
      "numbered_density": 0.72,
      "doi_density": 0.33
    }
  }
]
```

Это намного лучше, чем заставлять модель самой “grep-ать” всё подряд.

### 2. `count_reference_markers`
Считает признаки внутри диапазона:
- количество строк, начинающихся с `[n]`
- `n.`
- author-year starts
- DOI count
- year count

### 3. `segment_reference_block`
Детерминированная сегментация bibliography span на raw entries.

Возвращает:
- entries
- boundary confidence
- unresolved fragments

### 4. `parse_reference_entry`
Парсит одну запись, а не весь список.

### 5. `validate_reference_list`
Проверяет:
- нет ли suspiciously short entries;
- нет ли giant merged entries;
- count consistency;
- DOI uniqueness anomalies.

---

# Насчет regex: удобно ли агенту ими пользоваться?

Честно: **ограниченно удобно**.

Даже хороший LLM умеет придумывать regex, но в tool-calling возникают практические проблемы:

- escaping в JSON;
- различия между “хочу grep-like” и реальным Python `re`;
- сложно отлаживать многошаговые regex;
- line-based search недостаточен для многострочных references;
- regex почти всегда хорош для **сигналов**, но слаб как единственный механизм сегментации.

То есть regex-инструмент полезен как вспомогательный, но я бы не строил на нем основной агентный UX.

Лучше дать агенту более высокоуровневые тулзы:
- “найди кандидаты секции”
- “разбей блок на записи”
- “посчитай паттерны”

а не только “вот regex и удачи”.

---

# Нужен ли grep?

**Да, как debug/support tool — да.**  
**Как основной production tool — нет, недостаточно.**

Grep полезен, чтобы:
- проверить наличие `References`;
- найти паттерны `[1]`, `doi:`, `arXiv:`;
- быстро инспектировать документ.

Но для production extraction я бы считал необходимыми **более предметные инструменты** поверх grep.

---

# Основные недостатки текущего подхода

## 1. Цель spike не совпадает с реальной задачей
Если агент оптимизирован на:
> “оцени количество references”

это не то же самое, что:
> “извлеки полный и корректный список references”.

Для count можно пройти почти “по запаху”, а для extraction нужны надежные boundaries.

## 2. Агент может стать дорогой оберткой вокруг тех же эвристик
Если у вас главный tool — `heuristic_references`, то агент не создает нового extraction capability.  
Он лишь:
- вызывает текущий heuristic,
- иногда проверяет участок текста,
- затем формулирует ответ.

Это полезно для исследования, но может не дать качественного скачка.

## 3. Недостаточно специализированные тулзы
`grep` и `get_lines` слишком низкоуровневые.  
Агент тратит шаги на “ручной просмотр”, вместо того чтобы работать с осмысленными сигналами.

## 4. Трудно контролировать качество без confidence model
Нужен механизм, который говорит:
- baseline confident
- baseline uncertain
- segmentation suspicious
- parse failed

Иначе вы не поймете, когда вызывать fallback.

## 5. Много ошибок будут не от модели, а от представления текста
Если markdown / text extraction плохие:
- две колонки перемешаны,
- page headers в середине,
- line breaks кривые,

то агент не спасет полностью.  
Нужен preprocessing.

---

# Мой рекомендуемый план работ

## Фаза 0. Зафиксировать target output
Надо решить, что именно вы хотите получить в production:

### Вариант 1
Только:
- bibliography span
- count
- raw entries

### Вариант 2
Плюс structured metadata:
- title
- authors
- year
- doi/arxiv

Я бы шел так:

- **Stage 1 target:** reliable raw reference entries
- **Stage 2 target:** structured parsing per entry

Не пытайтесь решить оба идеально одновременно.

---

## Фаза 1. Eval harness
Сделайте единый pipeline runner, который для каждого документа сохраняет:

- найденный bibliography span
- raw entries
- count
- structured fields
- confidence
- traces/tool calls
- latency/cost

И считает метрики по benchmark set.

Это must-have.

---

## Фаза 2. Сильный baseline без агента
Сделайте хороший deterministic / hybrid baseline:

- improved section detection
- improved segmentation
- DOI/arXiv extraction
- continuation line merge
- confidence score

Это даст:
- сильную отправную точку,
- понимание, где именно baseline ломается.

---

## Фаза 3. LLM не на весь список, а на подзадачи
Запустите серию экспериментов:

### Эксперимент A
LLM только выбирает bibliography span из candidate spans.

Вход:
- top-$k$ кандидатов,
- короткие превью,
- сигналы.

Выход:
- ID лучшего кандидата.

### Эксперимент B
LLM выбирает segmentation strategy:
- numbered
- hanging-indent-like continuation
- author-year
- mixed

### Эксперимент C
LLM чинит только ambiguous fragments после deterministic segmentation.

Это намного лучше, чем сразу просить полный список.

---

## Фаза 4. Agent only as orchestrator
Если после A/B/C видно пользу, стройте агента, но как orchestrator:

- вызвать `find_bibliography_candidates`
- посмотреть 2–3 превью
- выбрать span
- вызвать `segment_reference_block`
- если quality flags плохие — вызвать repair tool
- вернуть raw entries

Не давать агенту делать всё руками через grep.

---

## Фаза 5. Parsing per entry
Когда raw entries уже надежны, делайте второй pipeline:

- parse one entry
- validate
- enrich by DOI/arXiv normalization
- deduplicate

Для long lists это стабильнее:
- батчами по 5–10 записей,
- или вообще по одной записи.

---

# Предлагаемый набор экспериментов

## Экспериментальный набор 1: Section localization

Сравнить:

1. pure regex heading baseline
2. heuristic ranker
3. LLM candidate selector
4. agent with grep/get_lines
5. hybrid ranker + LLM re-rank

Метрики:
- span IoU
- start/end line distance
- hit rate

## Экспериментальный набор 2: Segmentation

Сравнить:

1. split by numbered markers
2. heuristic line-merge
3. LLM segmentation on extracted zone
4. agent-assisted segmentation
5. hybrid heuristic + LLM repair

Метрики:
- count error
- boundary F1
- exact raw entry match

## Экспериментальный набор 3: Full extraction

Сравнить end-to-end:

1. old heuristic parser
2. one-shot structured LLM
3. section-then-segment-then-parse
4. agent orchestrated hybrid

Метрики:
- entry-level F1
- field-level F1
- DOI accuracy
- cost/doc
- latency/doc
- failure rate

---

# Что бы я ожидал по результатам

Мой прогноз такой:

## Скорее всего не победит
- one-shot LLM full structured extraction on long bibliography

## Скорее всего даст хороший practical результат
- deterministic candidate detection
- LLM-assisted selection/repair
- per-entry parsing
- agent only for ambiguous cases

## Может быть полезен, но не как core
- full tool-using agent on every document

---

# Практический roadmap на 2–4 недели

## Неделя 1
- собрать eval set
- зафиксировать gold для span/count/raw entries хотя бы на части данных
- построить baseline metrics

## Неделя 2
- улучшить deterministic section detector
- улучшить segmentation heuristics
- ввести confidence scoring

## Неделя 3
- сделать 2–3 высокоуровневых tool’а:
  - `find_bibliography_candidates`
  - `segment_reference_block`
  - `quality_check_reference_block`
- протестировать LLM/agent как selector/repair layer

## Неделя 4
- сравнить:
  - baseline
  - hybrid without agent
  - hybrid with agent fallback
- выбрать production path по quality/cost/latency

---

# Мой прямой ответ на ваши 2 вопроса

## 1. Мы на правильном пути?

**Да, если вы воспринимаете агент как средство оркестрации и fallback, а не как магическое решение.**

**Нет, если ставка делается на то, что агент сам “умно достанет references” из любых статей при помощи grep и regex.**  
Это вряд ли будет достаточно надежно.

Наиболее правильный путь, на мой взгляд:

- **hybrid pipeline**
- **evaluation-first**
- **LLM на локальные подзадачи**
- **агент только там, где он реально добавляет адаптивность**

---

## 2. Какой план работы? Экспериментов?

**Рекомендуемый план:**

1. построить benchmark и метрики;
2. усилить deterministic baseline;
3. декомпозировать задачу:
   - localization
   - segmentation
   - per-entry parsing
4. протестировать LLM на этих подзадачах отдельно;
5. только потом собирать agent orchestrator;
6. в production скорее использовать:
   - baseline first
   - agent fallback on hard cases

