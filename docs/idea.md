# Я планирую сделать graphrag для помощи у

**User - --**

Я планирую сделать graphrag для помощи учёному при генерации новых идейи работы с литературой и статьями по его тематике. 

Давай подумаем об онтологии. Какие узлы и связи нам могут пригодиться?

**Assistant - --**

Ниже — практичная онтология для **GraphRAG**, ориентированного на помощь учёному в:

- генерации гипотез,
- навигации по литературе,
- поиске противоречий и пробелов,
- связывании методов, данных, результатов и теорий.

Я бы проектировал её не как “идеальную общую онтологию науки”, а как **многоуровневую рабочую схему**, где есть:

1. **библиографический слой** — что это за источник, кто, когда, где;
2. **семантический научный слой** — о чём статья, что утверждает, как проверяет;
3. **эпистемический слой** — насколько уверенно, в каких условиях, где есть конфликт;
4. **прикладной слой для идей** — что можно комбинировать, переносить между областями, где пробелы.

---

# 1. Главный принцип: не пытаться сразу сделать “всё”

Лучше разделить узлы на 3 класса:

- **Документные сущности**: статья, автор, журнал, проект, датасет.
- **Научные сущности**: задача, гипотеза, метод, переменная, результат, метрика, объект исследования.
- **Интерпретационные сущности**: утверждение, доказательство/обоснование, ограничение, противоречие, открытый вопрос.

Если сделать граф только из “статей и цитирований”, это будет хороший поиск литературы, но слабый инструмент для генерации идей.

Если сделать граф только из “концептов”, без документного слоя, будет трудно трассировать, **откуда что взялось**.

Для учёного нужен баланс:
- каждая важная научная сущность должна быть **привязана к источнику**;
- каждая идея должна быть **разложима до утверждений и свидетельств**.

---

# 2. Минимальный набор узлов

## 2.1. Библиографические узлы

### `Paper`
Научная статья / препринт / обзор / глава.

**Поля:**
- `title`
- `abstract`
- `year`
- `doi`
- `venue`
- `publication_type` (`article`, `review`, `preprint`, `conference`, ...)
- `full_text`
- `domain`
- `keywords`

### `Author`
Автор статьи.

**Поля:**
- `name`
- `orcid`
- `affiliation_history`

### `Institution`
Организация.

### `Venue`
Журнал / конференция.

### `Project` / `Grant`
Полезно, если хочешь связывать исследования по финансированию или программе.

### `Dataset`
Датасет, корпус, база наблюдений.

### `Software` / `Tool`
Пакет, библиотека, прибор, вычислительный инструмент.

---

## 2.2. Научные узлы

### `ResearchTopic`
Тема / область / подзадача.

Примеры:
- “single-cell transcriptomics”
- “catalyst stability”
- “causal representation learning”

### `Problem`
Конкретная научная проблема.

Примеры:
- “предсказание токсичности соединений”
- “оценка причинного эффекта при скрытом конфаундинге”

### `Question`
Исследовательский вопрос.

Примеры:
- “Влияет ли X на Y при условии Z?”
- “Можно ли уменьшить variance метода M без потери bias?”

### `Hypothesis`
Гипотеза.

Примеры:
- “Эффект A обусловлен механизмом B”
- “Метод M работает лучше из-за инвариантности к C”

### `Claim`
Утверждение из статьи.

Это один из **самых важных узлов**.

Примеры:
- “Метод M превосходит baseline B на датасете D”
- “Белок P регулирует процесс Q”
- “Наблюдаемый эффект исчезает при контроле фактора F”

### `Concept`
Общий научный концепт / сущность предметной области.

Примеры:
- “oxidative stress”
- “latent variable”
- “band gap”
- “attention mechanism”

### `Entity`
Если нужна доменная конкретика:
- ген,
- белок,
- молекула,
- материал,
- болезнь,
- организм,
- регион мозга,
- астрономический объект,
- и т.д.

Можно сделать:
- либо общий тип `Entity` с подтипами,
- либо специализированные узлы: `Gene`, `Protein`, `Material`, `Disease`.

### `Method`
Метод, алгоритм, экспериментальная техника, протокол.

Примеры:
- “Western blot”
- “difference-in-differences”
- “transformer”
- “density functional theory”

### `Model`
Теоретическая модель / статистическая модель / симуляционная модель.

###

**User - --**

Давай сделаем декомпозицию. Начнём с первого слоя. Распиши подробно узлы и типы отношений, а также промпты для извлечения. Погугли, есть ли какие-то датасеты, на которых мы могли бы померить качество извлечения. Если таких нет, давай подумаем о том, как мы будем делать бенчмарк 

**Assistant - --**

Отлично. Давай действительно **декомпозируем онтологию по слоям** и начнём с **первого слоя: библиографический / document layer**.

Это самый правильный старт, потому что:

- он даёт **стабильный backbone графа**;
- его можно относительно надёжно извлекать;
- для него уже есть внешние источники истины и частично готовые датасеты;
- на нём удобно строить пайплайн качества до того, как мы перейдём к более “скользким” сущностям вроде гипотез, claims и mechanisms.

Я сначала опишу **цель слоя**, потом:
1. **узлы**,
2. **отношения**,
3. **нормализацию и canonical IDs**,
4. **промпты для извлечения**,
5. **как мерить качество**,
6. **какие публичные датасеты и источники можно использовать**,
7. **что делать, если прямого gold-standard под наш GraphRAG нет**.

Поискал, что есть по научному IE и библиографическим данным. Для первого слоя особенно полезны OpenAlex как внешний реестр научных сущностей, SciERC как классический benchmark по entity/relation extraction на научных текстах, SciREX как документный benchmark для scientific IE, а также ORKG как пример структурирования research contributions. Для более нового scientific IE есть также SciER, ориентированный на dataset/method/task extraction. ([docs.openalex.org](https://docs.openalex.org/?utm_source=openai))

---

# 1. Что входит в первый слой

Под “первым слоем” я предлагаю понимать:

> **всё, что позволяет однозначно идентифицировать научный документ и его место в исследовательской экосистеме, не влезая пока глубоко в научное содержание.**

То есть слой отвечает на вопросы:

- что это за работа?
- кто авторы?
- где опубликовано?
- когда?
- к какой организации привязано?
- что она цитирует / кем цитируется?
- это статья, препринт, обзор, датасет, софт?
- где найти full text / DOI / arXiv / PubMed ID?

Это не “смысл статьи”, а её **каркас идентичности и связности**.

---

# 2. Узлы первого слоя

Я бы рекомендовал **не делать слишком много типов сразу**. Для MVP достаточно 6–8 типов.

## 2.1. `Work`
Главный узел слоя. Не только paper, а вообще scholarly object.

### Что может быть `Work`
- journal article
- conference paper
- preprint
- review
- book chapter
- dataset paper
- software paper
- thesis
- report

### Зачем именно `Work`, а не только `Paper`
Потому что OpenAlex и современные scholarly graphs обычно используют более общее понятие work; это упрощает масштабирование на datasets/software later. OpenAlex описывает сущности scholarly ecosystem, включая works, authors, sources, institutions, topics и связанные объекты. ([developers.openalex.org](https://developers.openalex.org/api-reference/introduction?utm_source=openai))

### Ключевые атрибуты `Work`
- `work_id` — внутренний ID
- `title`
- `normalized_title`
- `abstract`
- `publication_year`
- `publication_date`
- `doi`
- `arxiv_id`
- `pmid`
- `pmcid`
- `work_type`
- `language`
- `venue_name`
- `publisher`
- `volume`
- `issue`
- `pages`
- `open_access_status`
- `url_landing`
- `url_pdf`
- `is_retracted`
- `source_systems` — откуда пришло: Crossref/OpenAlex/PubMed/manual
- `ingestion_confidence`

### Дополнительные полезные поля
- `citation_count`
- `reference_count`
- `has_full_text`
- `license`
- `keywords_raw`

---

## 2.2. `Author`
Узел автора как отдельной персоны.

### Атрибуты
- `author_id`
- `full_name`
- `normalized_name`
- `orcid`
- `alternative_names`
- `email` — если есть и допустимо хранить
- `homepage_url`
- `disambiguation_confidence`

### Почему важен отдельный узел
- авторский поиск,
- mapping научных школ,
- co-authorship graph,
- перенос идей между группами,
- анализ trust / reputation / domain expertise.

---

## 2.3. `Institution`
Организация автора на момент публикации или вообще в профиле.

### Атрибуты
- `institution_id`
- `name`
- `normalized_name`
- `ror_id`
- `country`
- `city`
- `department` — опционально, иногда лучше как отдельный узел
- `institution_type` — university, company, hospital, lab, nonprofit

### Комментарий
На старте можно не выделять `Department` отдельно, а хранить department как атрибут аффилиации.

---

## 2.4. `Venue`
Где работа опубликована.

### Типы
- journal
- conference
- workshop
- repository
- preprint server
- book series

### Атрибуты
- `venue_id`
- `name`
- `normalized_name`
- `issn`
- `eissn`
- `publisher`
- `venue_type`

---

## 2.5. `OrganizationUnit` или `Affiliation` as edge-object
Тут важное решение.

Обычная проблема: связь “автор связан с институтом” почти всегда **контекстная**, потому что аффилиация зависит от конкретной статьи.

Поэтому я рекомендую не хранить просто:

- `Author - AFFILIATED_WITH -> Institution`

а делать либо:
- связь с атрибутами,
- либо промежуточный узел `Authorship`,
- либо узел `AffiliationStatement`.

Для GraphRAG лучше всего **`Authorship` как reified relation**.

---

## 2.6. `Authorship`
Это технический, но крайне полезный узел.

### Зачем
Он позволяет хранить:
- порядок автора,
- corresponding author,
- конкретную аффилиацию именно в этой статье,
- equal contribution,
- author role.

### Атрибуты
- `authorship_id`
- `author_position`
- `is_corresponding`
- `equal_contribution`
- `raw_affiliation_string`
- `email`
- `extraction_confidence`

---

## 2.7. `Identifier`
Опциональный узел, не обязателен в MVP.

Если хочешь очень чистую модель, можно сделать идентификаторы отдельными узлами:
- DOI
- ORCID
- ROR
- PMID
- PMCID
- arXiv ID
- ISSN

Но для первого MVP я бы держал их как **атрибуты**, а не отдельные узлы. Иначе граф быстро раздуется.

---

## 2.8. `Funder` / `Grant`
Опционально для layer 1.5.

Полезно, но я бы не включал в самый первый extraction sprint.

---

# 3. Отношения первого слоя

Ниже — **минимально достаточный набор**.

## 3.1. `Work - HAS_AUTHORSHIP -> Authorship`
Связь статьи с конкретным фактом авторства.

## 3.2. `Authorship - OF_AUTHOR -> Author`
Кто является автором.

## 3.3. `Authorship - AFFILIATED_WITH -> Institution`
С какой организацией связан именно в этой публикации.

## 3.4. `Work - PUBLISHED_IN -> Venue`
Где опубликовано.

## 3.5. `Work - CITES -> Work`
Связь цитирования.

Это одна из базовых связей для GraphRAG:
- citation expansion,
- backward chaining,
- lineage идей,
- обзоры, основанные на citation neighborhoods.

## 3.6. `Work - RELATED_VERSION_OF -> Work`
Например:
- preprint ↔ journal version,
- conference paper ↔ extended journal article,
- corrigendum ↔ original article.

Очень полезно, чтобы GraphRAG не плодил дубликаты.

## 3.7. `Work - HAS_DATASET -> Work|Dataset`
Если пока не вводим `Dataset` как отдельный узел, можно временно связывать с `Work`.
Но честно: для слоя 1 лучше это пока не делать.

## 3.8. `Work - HAS_SOFTWARE -> Work|Software`
Аналогично.

---

# 4. Рекомендуемая модель графа первого слоя

Ниже — мой preferred вариант.

```text
(Work)-[:HAS_AUTHORSHIP]->(Authorship)-[:OF_AUTHOR]->(Author)
(Authorship)-[:AFFILIATED_WITH]->(Institution)
(Work)-[:PUBLISHED_IN]->(Venue)
(Work)-[:CITES]->(Work)
(Work)-[:RELATED_VERSION_OF]->(Work)
```

Это лучше, чем плоское:

```text
(Work)-[:AUTHORED_BY]->(Author)
(Author)-[:AFFILIATED_WITH]->(Institution)
```

потому что второе ломается на:
- нескольких аффилиациях,
- разных аффилиациях по разным работам,
- порядке авторов,
- corresponding author,
- equal contribution.

---

# 5. Кардинальности и ограничения

## `Work`
- `HAS_AUTHORSHIP`: $1..N$
- `PUBLISHED_IN`: $0..1$ или $0..N$ если учитывать repository + journal
- `CITES`: $0..N$
- `RELATED_VERSION_OF`: $0..N$

## `Authorship`
- `OF_AUTHOR`: ровно $1$
- `AFFILIATED_WITH`: $0..N$

## `Author`
- может иметь много `Authorship`

## `Venue`
- много `Work`

---

# 6. Нормализация и canonicalization

Первый слой почти полностью упирается в **entity resolution**.

Если этого не сделать, граф будет зашумлён:
- один и тот же автор в 5 вариантах,
- одна и та же статья как arXiv, DOI и publisher page,
- один и тот же институт как “MIT”, “Massachusetts Institute of Technology”, “MIT CSAIL”.

## 6.1. Для `Work`
Приоритет канонического ID:
1. DOI
2. PMID / PMCID
3. arXiv ID
4. OpenAlex ID
5. внутренний hash от title + year + first author

## 6.2. Для `Author`
Приоритет:
1. ORCID
2. OpenAlex author ID
3. нормализованное имя + institution + coauthor signature

## 6.3. Для `Institution`
Приоритет:
1. ROR
2. GRID/другой внешний ID, если нужен legacy
3. нормализованное имя + страна

## 6.4. Для `Venue`
Приоритет:
1. ISSN / eISSN
2. OpenAlex source ID
3. нормализованное название

OpenAlex специально полезен здесь как внешний backbone для works/authors/institutions/sources/topics и API/снапшоты для этих сущностей. ([developers.openalex.org](https://developers.openalex.org/api-reference/introduction?utm_source=openai))

---

# 7. Что извлекать из текста, а что подтягивать из внешних API

Очень важное архитектурное правило:

## Извлекаем из PDF / full text:
- title
- abstract
- author list
- raw affiliations
- venue mention
- year/date
- references list
- version hints
- identifiers, если присутствуют

## Обогащаем через внешние реестры:
- DOI verification
- ORCID resolution
- institution resolution via ROR/OpenAlex
- citation graph enrichment
- venue normalization
- duplicate merging

То есть LLM/парсер не должен быть единственным источником истины. Он должен быть **extractor + candidate generator**, а canonical truth лучше собирать через metadata registries.

---

# 8. Промпты для извлечения: общая стратегия

Я бы не делал один огромный промпт “извлеки всё”. Лучше сделать **каскад промптов**:

1. `document_metadata_extraction`
2. `authors_and_affiliations_extraction`
3. `references_extraction`
4. `version_linking_extraction`
5. `normalization_prompt` или post-processing rules

Так легче:
- дебажить,
- считать quality по компонентам,
- дообучать/заменять этапы.

---

# 9. Промпт 1: извлечение метаданных документа

## Цель
Извлечь поля `Work` из front matter, abstract page, header, footer.

## Вход
- title page / first 1–2 pages / extracted structured text

## Выход
Строгий JSON.

```text
Ты извлекаешь библиографические метаданные научной работы.

Задача:
1. Определи, является ли текст научной публикацией.
2. Извлеки только явно присутствующие в тексте данные.
3. Не додумывай DOI, venue, год или авторов.
4. Если поле отсутствует или неуверенно, верни null.
5. Если есть несколько кандидатов, верни наиболее вероятный и добавь альтернативы в notes.
6. Сохраняй оригинальное написание строк, а отдельно дай нормализованные версии там, где это уместно.

Верни JSON строго по схеме:

{
  "is_scholarly_work": true,
  "work": {
    "title": "",
    "normalized_title": "",
    "abstract": "",
    "publication_year": null,
    "publication_date": null,
    "work_type": null,
    "doi": null,
    "arxiv_id": null,
    "pmid": null,
    "pmcid": null,
    "language": null,
    "venue_name": null,
    "publisher": null,
    "volume": null,
    "issue": null,
    "pages": null,
    "url_landing": null,
    "url_pdf": null,
    "open_access_status": null,
    "is_retracted": null
  },
  "evidence": {
    "title_span": "",
    "abstract_span": "",
    "identifier_spans": [],
    "venue_span": "",
    "date_span": ""
  },
  "notes": []
}

Правила:
- publication_year — только если явно указан.
- work_type — одно из: journal_article, conference_paper, preprint, review, book_chapter, thesis, report, unknown.
- doi — только если выглядит как DOI.
- arxiv_id — только если явно указан arXiv.
- abstract — только если это действительно abstract, а не introduction.
- normalized_title — title в нормализованном виде: без лишних пробелов, без line breaks.
```

---

# 10. Промпт 2: авторы и аффилиации

Это отдельный prompt, потому что author-affiliation parsing почти всегда сложнее, чем title/DOI.

```text
Ты извлекаешь авторов и их аффилиации из научной публикации.

Задача:
1. Найди всех авторов в порядке появления.
2. Для каждого автора извлеки raw имя как в тексте.
3. Найди связанные аффилиации, индексы аффилиаций и email, если есть.
4. Если соответствие автор ↔ affiliation неоднозначно, отрази это явно.
5. Не объединяй разных авторов.
6. Не выдумывай institution normalization; сначала сохрани raw строку.

Верни JSON строго по схеме:

{
  "authorships": [
    {
      "author_position": 1,
      "author_raw_name": "",
      "author_normalized_name": "",
      "affiliation_markers": [],
      "raw_affiliations": [],
      "email": null,
      "is_corresponding": null,
      "equal_contribution": null,
      "confidence": 0.0,
      "evidence": {
        "author_span": "",
        "affiliation_spans": [],
        "email_span": ""
      }
    }
  ],
  "unmapped_affiliations": [],
  "notes": []
}

Правила:
- Сохраняй порядок авторов.
- Если у автора несколько аффилиаций, перечисли все.
- Если email общий, не приписывай его конкретному автору без явных оснований.
- confidence от 0 до 1.
- author_normalized_name — убери лишние пробелы, но не меняй порядок имени и фамилии без необходимости.
```

---

# 11. Промпт 3: нормализация аффилиаций в Institution

Эта стадия может быть LLM-based или rule-based + external lookup.

```text
Ты нормализуешь аффилиации научных авторов до канонических организаций.

Вход:
- raw affiliation string
- страна/город, если есть
- список кандидатов организаций

Задача:
1. Определи, соответствует ли строка конкретной организации.
2. Выбери лучший кандидат.
3. Если уверенности недостаточно, верни no_match.
4. Если в строке указаны и department, и institution, institution выдели отдельно.

Верни JSON:

{
  "raw_affiliation": "",
  "department": null,
  "institution_name": null,
  "country": null,
  "matched_candidate_id": null,
  "matched_candidate_name": null,
  "match_status": "matched",
  "confidence": 0.0,
  "reason": ""
}

match_status ∈ ["matched", "ambiguous", "no_match"]
```

Эта стадия особенно хорошо работает, если кандидатов подаёт не LLM, а retrieval по ROR/OpenAlex.

---

# 12. Промпт 4: извлечение references

Для первого слоя это очень важно, потому что `CITES` — одна из самых ценных связей.

```text
Ты извлекаешь список литературы из научной публикации.

Задача:
1. Найди секцию references / bibliography.
2. Раздели её на отдельные записи.
3. Для каждой записи извлеки как можно больше библиографических полей.
4. Не выдумывай отсутств