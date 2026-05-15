Да — таких tools и MCP-серверов уже довольно много. Ниже собрал **самые полезные инструменты для LLM-агента в научных исследованиях**, особенно в духе `arxiv_search`, `arxiv_fetch`, `semantic_scholar_search` и т.п.

**Нативная архитектура external HTTP tools в этом репозитории:** [ADR 030](../adr/030-external-research-tools-architecture.md) (`science_graphrag/agent/tools/external/`).

**Статус реализации, архитектурная сверка и UI/UX-рекомендации:** [External Research Tools: ADR 030 vs Implementation Review](external-research-tools-implementation-review-2026-05-15.md).

## Коротко: что искать

Если тебе нужны research-tools для агента, обычно полезны такие категории:

- **Поиск статей**
  - `search_arxiv`
  - `search_semantic_scholar`
  - `search_openalex`
  - `search_crossref`
  - `search_pubmed`
- **Получение карточки статьи**
  - `get_arxiv_paper`
  - `get_semantic_scholar_paper`
  - `get_paper_details`
  - `find_paper`
- **Чтение полного текста / PDF**
  - `download_arxiv_pdf`
  - `read_arxiv_paper`
  - `convert_paper`
  - `get_paper_section`
- **Цитирования и ссылки**
  - `get_citations`
  - `get_references`
  - `get_paper_network`
  - `recommend_papers`
- **Экспорт и библиография**
  - `export_bibtex`
  - `get_arxiv_paper_bibtex`
- **Авторы / профили**
  - `search_authors`
  - `get_author_profile`
  - `get_author_works`

---

## Нашёл несколько хороших готовых решений

### 1. `academic-tools-mcp`
GitHub: `hunter-heidenreich/academic-tools-mcp`

Очень близко к тому, что ты описал: набор MCP tools для академического ресёрча.

**Источники:**
- OpenAlex
- arXiv
- bioRxiv / medRxiv
- Crossref
- OpenCitations
- Wikipedia
- ACL Anthology

**Примеры tools:**
- `search_arxiv`
- `get_arxiv_paper_metadata`
- `get_arxiv_paper_abstract`
- `get_arxiv_paper_authors`
- `get_arxiv_paper_bibtex`
- `download_arxiv_pdf`
- `convert_paper`
- `get_paper_sections`
- `get_paper_section`
- `search_crossref_by_title`
- `get_crossref_references`
- `get_opencitations_citations`
- `get_opencitations_references`

**Чем хорош:**
- есть и **поиск**, и **fetch metadata**, и **PDF pipeline**
- удобно для агента, который должен **найти статью → скачать PDF → распарсить по секциям**

---

### 2. `academic-research-mcp`
GitHub: `alisoroushmd/academic-research-mcp`

Это уже более **унифицированный research hub**.

**Источники:**
- OpenAlex
- Semantic Scholar
- CrossRef
- PubMed
- arXiv
- medRxiv / bioRxiv
- Google Scholar
- ORCID
- Unpaywall

**Примеры tools:**
- `smart_search`
- `find_paper`
- `search_papers`
- `search_authors`
- `get_author`
- `get_author_works`
- `get_paper_network`
- `recommend_papers`
- `batch_get_papers`

**Чем хорош:**
- если нужен не просто `arxiv_search`, а **единый интерфейс** над многими научными базами
- полезен для systematic review и biomedical use cases
- есть доступ к **citation graph**, **recommendations**, **batch lookup**

---

### 3. `paper-search-mcp`
GitHub: `xiaoxiaoxiaotao/paper-search-mcp`

Более компактный, но очень практичный вариант.

**Источники:**
- Semantic Scholar
- arXiv

**Примеры tools:**
- `search_semantic_scholar`
- `get_semantic_scholar_paper`
- `search_arxiv`
- `get_arxiv_paper`
- `read_arxiv_paper`
- `export_bibtex`
- `align_paper_by_title`
- `build_literature_digest`

**Чем хорош:**
- идеален, если тебе нужен **минимальный, но полезный набор**
- хорошо покрывает сценарий:
  - найти paper в Semantic Scholar
  - найти preprint в arXiv
  - прочитать PDF
  - собрать digest литературы

---

### 4. `crossref-academic-mcp-server`
PyPI: `crossref-academic-mcp-server`

Фокус на:
- Crossref
- OpenAlex
- Semantic Scholar

**Tools:**
- `search_papers`
- `get_paper_details`
- `get_citations`
- `get_author_profile`
- `search_topics`

**Чем хорош:**
- если тебе важны **DOI**, **метаданные**, **citation lookup**
- более “metadata/citation centric”, чем “PDF reading centric”

---

### 5. `ScholarFetch`
GitHub: `laibniz/scholarfetch`

Это уже не просто toolset, а **целая research environment** для человека и агента.

**Источники:**
- Elsevier / Scopus
- OpenAlex
- Crossref
- arXiv
- Europe PMC
- Springer Nature
- Semantic Scholar

**Возможности:**
- поиск
- author resolution
- reference traversal
- abstract / full text retrieval
- сохранение reading list в рамках MCP session
- экспорт корпуса: citations / abstracts / BibTeX / full text

**Чем хорош:**
- если агент должен не просто разово вызвать `search_arxiv`, а **вести исследовательскую сессию**
- например:
  - найти статьи
  - развернуть references
  - собрать reading list
  - экспортнуть корпус для summarization

---

## Какие tools реально нужны агенту

Если ты хочешь спроектировать **свой research toolkit** для LLM-агента, я бы рекомендовал минимальный набор такого вида:

### Базовый минимум
- `search_arxiv(query, max_results, sort_by)`
- `get_arxiv_paper(arxiv_id)`
- `fetch_arxiv_pdf(arxiv_id)`
- `search_semantic_scholar(query, limit)`
- `get_semantic_scholar_paper(paper_id)`
- `search_openalex(query, limit)`
- `get_paper_by_doi(doi)`

### Для чтения и анализа
- `extract_pdf_text(url_or_id)`
- `get_paper_sections(paper_id)`
- `get_paper_section(paper_id, section_name)`
- `summarize_paper(paper_id)`
- `extract_citations(paper_id)`
- `extract_bibtex(paper_id)`

### Для citation graph
- `get_references(paper_id)`
- `get_citations(paper_id)`
- `get_related_papers(paper_id)`
- `recommend_similar_papers(paper_id)`

### Для researcher workflow
- `save_to_reading_list(paper_id)`
- `list_reading_list()`
- `export_reading_list(format="bibtex|json|markdown")`

---

## Самые полезные академические API, под которые обычно делают tools

Если смотреть не только на готовые MCP-сервера, но и на сами backend-источники, чаще всего используют:

| Источник | Для чего полезен |
|---|---|
| `arXiv` | preprints, особенно CS/ML/Math/Physics |
| `Semantic Scholar` | citation graph, influence, related papers |
| `OpenAlex` | большая открытая база работ, авторов, институтов |
| `Crossref` | DOI resolution, библиографические метаданные |
| `PubMed` | biomedical / clinical papers |
| `Europe PMC` | life sciences, abstracts, some full text |
| `bioRxiv` / `medRxiv` | биомедицинские preprints |
| `Unpaywall` | поиск легально доступных open-access PDF |
| `ORCID` | профили исследователей |
| `OpenCitations` | citation links |

---

## Если нужен именно ответ “какие названия tools бывают”

Вот список в стиле, который обычно ожидает агент:

```text
search_arxiv
get_arxiv_paper
get_arxiv_paper_metadata
get_arxiv_paper_abstract
get_arxiv_paper_authors
get_arxiv_paper_bibtex
download_arxiv_pdf
read_arxiv_paper

search_semantic_scholar
get_semantic_scholar_paper
get_citations
get_references
recommend_papers

search_openalex
get_openalex_work
search_crossref_by_title
get_paper_details
find_paper_by_doi

search_pubmed
get_pubmed_article
search_biorxiv
search_medrxiv

export_bibtex
align_paper_by_title
build_literature_digest
get_paper_network
search_authors
get_author_profile
get_author_works
```

---

## Что бы я рекомендовал тебе на практике

<details>
<summary><b>Если нужна простая рекомендация</b></summary>

- **Хочешь максимально близко к `arxiv_search` / `arxiv_fetch`:**  
  смотри `academic-tools-mcp` и `paper-search-mcp`

- **Хочешь один большой research gateway для агента:**  
  смотри `academic-research-mcp`

- **Хочешь stateful research workflow с reading list и export corpus:**  
  смотри `ScholarFetch`

</details>

---

## Реализация в этом репозитории (science-graphrag)

Во встроенном agent runtime (без отдельного MCP-сервера) уже есть LangChain tools:

- **`web_search`** — Crossref-backed metadata search (`api.crossref.org/works`), не универсальный веб-поиск.
- **`web_fetch`** — HTTPS fetch + summary для разрешённых scholarly URLs; есть SSRF guardrails, byte cap, cache.
- **`arxiv_search`** — поиск препринтов через официальный Atom API `export.arxiv.org` (HTTP-клиент в коде), в ответе abstracts и ссылки abs/pdf; `evidence_origin: external_web`, `web_sources` для пайплайна web-citations.
- **`arxiv_fetch`** — одна запись по arXiv id или URL (metadata + abstract). Полный текст PDF на первом этапе не извлекается: при запросе PDF-текста возвращается `unsupported_pdf_text`.
- **`unpaywall_lookup`** — DOI → OA status + best legal open-access landing/PDF URL через Unpaywall v2; PDF не скачивает.
- **`doi_resolver`** — отдельный operator-gated metadata bridge: DOI/OpenAlex + Crossref fallback + optional workspace work-id mapping.

Детерминированные признаки запроса (`asks_for_web_research`, `asks_for_arxiv`, `asks_for_unpaywall`) и shortlist/routing rules — в `question_features.py`, `tool_search.py`, `route_planner.py`.

Не реализованы нативно: Semantic Scholar, OpenAlex search, PubMed, bioRxiv/medRxiv, PDF section extraction, citation graph traversal и stateful reading list. Приоритеты и статус стабильности см. в implementation review выше.

---

## Могу помочь дальше

Я могу следующим сообщением сделать одно из трёх:

1. **Собрать тебе shortlist лучших MCP tools** под твой стек  
2. **Предложить схему names/signatures** для собственного research tool API  
3. **Найти ещё конкретно open-source MCP servers** с `arxiv`, `Semantic Scholar`, `PubMed`, `OpenAlex`

Если хочешь, я могу сразу сделать **таблицу “tool name → что делает → откуда берёт данные”** в более системном виде.