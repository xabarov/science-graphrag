# Reader UX & translation roadmap — 2026-04-25

**Doc status:** `reference`

**Read hint:** reader/translation UX waves; not agent benchmark queue.

**Дата:** 2026-04-25
**Статус:** living working doc; новая серия волн **RX (Reader eXperience)** + поддерживающая серия **LX (LLM Concurrency)** в [`master-roadmap-and-refactor-plan-2026-04-25.md`](master-roadmap-and-refactor-plan-2026-04-25.md). Закрывает накопившиеся болевые точки страницы `/reader` и Reader-таба внутри Workspace.

**Триггер:** ревью UI страницы «Чтение» 2026-04-25 (см. `assets/image-ca17ce4e-3665-4d64-ab4e-2d6b5ec24c78.png`). Пользователь видит:

1. Сверху форма ввода `work_id` (UUID-хеш) — продуктово непригодна: конечный пользователь не знает и не печатает работу руками.
2. Контент сжат в ~60 % ширины экрана, справа большое пустое поле — `mainShellContentSx` капает на `1680px`, но даже в пределах капа верстка одноколоночная, заголовки/мета занимают много вертикали.
3. Блок «Извлечённый текст (чтение)» — сырые `## Section` рендерятся как plain text (`Typography whiteSpace: "pre-wrap"`); никаких заголовков, ссылок, формул, таблиц, кода.
4. Под основной статьёй блок «Чанки (дополнительно) — 32» — продуктово инструмент для дебага traceability (focused fingerprint), но пользователь его видит и не понимает зачем.
5. Если статья на английском, RU-локали интерфейса не помогает прочесть; есть встроенный LLM (агент, claims, semantic) — но **переводчика нет**, хотя бэкбон для chunked-LLM с конкуренцией уже есть (`extraction_llm_references_max_concurrency`).
6. Иконки, цвета, типографика страницы — рассинхрон с дизайн-каноном Cursor (плотная типографика 13 px, тонкие границы, акцент `rgba(99,102,241,*)`); бо́льшая часть UI — голый MUI Typography без визуальной иерархии.

**Связанные документы:**

| Документ | Что в нём |
|----------|-----------|
| [`master-roadmap-and-refactor-plan-2026-04-25.md`](master-roadmap-and-refactor-plan-2026-04-25.md) | Карта треков и параллельности; добавляется Track **RX** (Reader UX) и поддерживающий Track **LX** (LLM Concurrency) |
| [`graph-readability-followup-2026-04-25.md`](graph-readability-followup-2026-04-25.md) | Аналогичный «followup-роудмап» для графа — повторяем структуру и темп волн |
| [`workspace-ux-redesign-2026-04-25.md`](workspace-ux-redesign-2026-04-25.md) | Дизайн-канон workspace shell (hero / icons sweep / i18n) — Reader должен соответствовать |
| [`../specs/ui-i18n-guidelines.md`](../specs/ui-i18n-guidelines.md) | EN/RU контракт для i18n новых ключей (`reader.*`, `readerBody.*`, `translate.*`) |
| [`../adr/011-graph-live-ux-and-payload.md`](../adr/011-graph-live-ux-and-payload.md) | Принцип «backend отдаёт нейтральный raw + key, локализация в UI» — повторяем для языка статьи |
| [`../backlog/refactor-frontend.md`](../backlog/refactor-frontend.md) | `[OPEN] Split ReaderWorkBody.jsx (485)` — расчищает дорогу под RX1/RX2 |
| [`../backlog/refactor-backend.md`](../backlog/refactor-backend.md) | Расширяется LX1/LX2/LX3 (см. §6) |

---

## 1. Диагноз: что именно не работает

### 1.1 `work_id`-баннер в роли «главного действия»

```42:69:ui/src/pages/ReaderPage.jsx
    <Box sx={{ p: 2, ...mainShellContentSx }}>
      <PageHeader
        eyebrow={t("reader.header.eyebrow")}
        title={t("reader.header.title")}
        description={
          <>
            {t("reader.header.descBefore")}{" "}
            <code style={{ color: "rgba(129,140,248,0.95)" }}>work_id</code>
            {t("reader.header.descAfter")}
          </>
        }
      />

      <Box component="form" onSubmit={applyWorkId} sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 2 }}>
        <TextField
          label={t("reader.workIdLabel")}
          value={workIdInput}
          onChange={(ev) => setWorkIdInput(ev.target.value)}
          ...
```

Проблемы:

* `work_id` — UUID без человеко-читаемой проекции. **Кто и зачем** будет копировать UUID в форму — не определено. Реальные точки входа: «Открыть в Reader» из Workspace card, deep-link из Ask citation, кнопка «Reader (workspace)» в `/reader`.
* Когда `work_id` уже выставлен query-параметром, **второй раз показывать форму** — это шум: 90 % случаев пользователь пришёл по ссылке, ему нужен заголовок статьи и текст, а не редактирование id.
* `PageHeader` повторяет «Чтение» крупным шрифтом, плюс Drawer уже подсвечивает раздел — двойной заголовок съедает 2-3 см вертикального места до того, как пользователь увидит абстракт.
* В Workspace-табе Reader (`tabs/ReaderTab.jsx`) — наоборот, формы нет, work_id берётся из родителя, и UX внутри таба корректнее, чем у standalone-страницы. Расхождение между двумя точками входа.

**Что хочется (целевой сценарий):**

* Если `work_id` пуст — показывать **Recent works** (последние N открытых из `persistWorkId`) и кнопку «Открыть Workspace» (`/workspaces`) как два главных CTA. Без TextField на UUID.
* Если `work_id` заполнен — заголовок страницы становится **названием статьи**, а сам UUID уезжает в правый угол или в «детали» под small caps, копируется иконкой clipboard.
* Дев-режим (явный `?dev=1` или галочка в Settings) возвращает поле «Open by work_id» — для разработчиков и трассы из Phoenix.

### 1.2 Пустая правая половина и одноколоночный layout

`ReaderPage.jsx` оборачивает в `mainShellContentSx` (cap `min(1680px, 100%)`). На обычном FullHD (1920×1080) контент капается до 1680, дальше идёт пустое поле — но в скриншоте даже **внутри 1680** контент занимает только ~70 % ширины: `combinedExtractedText` отдаётся одним столбцом, без TOC, без правой колонки с метаданными.

Дополнительно `Box` верхней метаданной карточки (детали статьи + abstract) — full-width, абстракт растягивается на 1500 px одной строкой 13 px → нарушает читабельный «measure» 60–80 ch.

**Что хочется:**

* Двухколоночный layout (≥ `lg`):
  * Левая узкая колонка (240–280 px) — TOC статьи (генерим из `chunks[].section_path`), метаданные (год / DOI / venue), `Open in Workspace`, `Open Graph`, индикатор языка статьи + кнопки перевода (см. §1.6).
  * Правая основная колонка — Markdown-рендер с измеренной шириной `60–78ch` (≈ 720–860 px), центрирована.
* На `md` и ниже — обе секции в один поток, TOC сворачивается в drawer/`Accordion`.

### 1.3 «Извлечённый текст» рисуется как plain text

```245:269:ui/src/components/work/ReaderWorkBody.jsx
      {chunks && !loading && viewMode === "markdown" && combinedExtractedText ? (
        <Box sx={{ mb: 2, p: 1.5, ... }}>
          ...
          <Box sx={{ maxHeight: "min(60vh, 520px)", overflow: "auto", ... backgroundColor: "#0a0a0a" }}>
            <Typography sx={{ fontSize: "0.8125rem", ..., whiteSpace: "pre-wrap" }}>
              {combinedExtractedText.length > 120_000 ? `${combinedExtractedText.slice(0, 120_000)}…` : combinedExtractedText}
            </Typography>
          </Box>
          ...
```

Что происходит фактически:

* `combinedExtractedText` склеивается из `chunks.items` с прибавлением `## ${section_path}` и разделителей `\n---\n`.
* Рендер — `<Typography whiteSpace="pre-wrap">`. Markdown-синтаксис (`##`, `**bold**`, инлайн `code`, формулы `$...$`, таблицы, ссылки, цитаты) виден **как сырые символы**.
* Контейнер ограничен `maxHeight: min(60vh, 520px)` с внутренним скроллом — пользователь читает большую статью в 520-пиксельном «окошке» с двойной полосой прокрутки (страница + блок).
* На `> 120 000` символах хвост обрезается с `…` без сообщения и без возможности догрузить.

**Что хочется:**

* Полноценный Markdown с поддержкой:
  * Заголовки `H1..H6` (с auto-id и якорями), списки, блок-цитаты, hr.
  * Таблицы (GFM).
  * Сноски (GFM footnotes), задачные списки, `<sup>/<sub>`.
  * Инлайн и блок-код с подсветкой (≥ python/bash/json/yaml/c/cpp/text — основные сценарии для научных статей).
  * Математика (KaTeX): inline `$E=mc^2$` и блочная `$$\alpha + \beta$$` — встречается часто в извлечённых статьях.
  * `external links` через `rel="noopener noreferrer"`, безопасный `target="_blank"`.
* Высота — естественная, без внутреннего скролла; скролл — только страничный.
* Лимит `120 000 символов` снять или заменить виртуализированным рендером по разделам (rendering chunk-by-section, lazy mount).

### 1.4 «Чанки (дополнительно) — 32»: дев-инструмент в продуктовом UI

Блок чанков:

* Используется только для traceability (`focusedFingerprint` / `focusedSection` подсвечивает чанк, открытый из Ask/Evidence) и для дебага Qdrant.
* Для обычного «прочитал статью» — бесполезен. Текст чанка **уже** в основном Markdown-блоке.
* Сейчас рисуется внизу страницы под `Collapse` (свернут по умолчанию), но всё равно занимает место в DOM, увеличивает запрос (`limit=200`), имеет собственный счётчик, и пользователь видит непонятный термин «чанки».

**Что хочется:**

* По умолчанию **не показывать**. Условия активации:
  1. URL содержит trace-параметры (`chunk_fp` / `section`) — тогда автоматически развёрнут с подсветкой нужного чанка.
  2. Включён режим разработчика (Settings → «Show developer tools in Reader» или env-флаг `VITE_READER_DEV_PANEL=1`).
* Переименовать «Чанки» → «Trace context» / «Контекст ссылок» в продуктовом режиме (термин понятен исследователю); под dev-флагом — оставить технические `fp ${fingerprint}`, `section_path`, `order`.

### 1.5 Иконки, цвета, типографика — рассинхрон с дизайн-каноном

* На странице **нет ни одной иконки** (хотя в проекте подключён `@mui/icons-material@7.3.9`):
  * Загрузка work_id → нет иконки `Search` / `OpenInNew`.
  * Toggle Markdown / PDF → `Article` / `PictureAsPdf` сразу читается визуально.
  * Кнопки «Open Reader (workspace)», «Open Graph» — без иконок `OpenInFull` / `AccountTree`.
  * Карточка деталей не имеет статус-бейджа (semantic / has_chunks) — есть только сухая строка `document_id: ... · has_chunks: true · semantic: true`.
* Карточки используют разнобой `borderRadius: "6px"` в одних местах, `4px` в `Markdown box` — в проекте принято **строго `6px`** и плоский дизайн без теней (см. cursor-rules для osint-gr; в SciGraph дисциплина та же).
* Заголовок статьи — `fontWeight: 600, fontSize: "0.8125rem"` (13 px). Для **главного объекта страницы** это слишком мелко — должен быть 18–22 px (`H1` визуально).

### 1.6 Нет перевода с EN на RU (и обратно)

* Detection: язык статьи нигде не вычисляется. Backend отдаёт `abstract` и chunk-тексты «как есть», поле `language` в `Work` отсутствует (см. `science_graphrag/api/works/detail.py:183-201` — `out` без `language`).
* Translation: нет ни UI-кнопки, ни backend-эндпоинта, ни LLM-роутинга — даже несмотря на то, что **chunk-LLM с пулом конкуренции уже реализован** для references (`science_graphrag/ingestion/llm/orchestrator.py:215-256`, `extraction_llm_references_max_concurrency` в `config.py:156-161`).
* Семантически перевод нужен:
  1. Полный текст (по разделам, в исходной структуре).
  2. Только аннотация (быстрый перевод, отдельная кнопка) — пользователь часто хочет «понять о чём статья за 10 секунд».
* Конкуренция LLM-вызовов: настройка `extraction_llm_references_max_concurrency` живёт **только** для одной фичи. Когда добавятся ещё ad-hoc LLM-операции (translate, idea-assist live, claims rerun, future TTS) — каждый раз будут вводить свой `*_max_concurrency` поле. **Нужен унифицированный кластер настроек** (см. §6 Track LX).

### 1.7 Таб Reader внутри Workspace и standalone расходятся

* `WorkspacePage/tabs/ReaderTab.jsx` рисует ту же `ReaderWorkBody`, **без** формы work_id, **с** двумя ссылками («Open standalone», «Jump to Graph»), **с** сжатым `liveLine`.
* `pages/ReaderPage.jsx` — обёртка с формой work_id, без тех же кнопок (есть отдельные `openReaderWs`, `openGraphWs`), но без `liveLine` и `ReaderClaimsPanel`.
* `ReaderClaimsPanel` (Wave O) включается **только** в табе, не в standalone — расхождение поведений неочевидное.

**Хочется:** унифицировать через общий `<ReaderShell>` (data + body + side rail), который отдаёт страница + таб с разными chrome.

### 1.8 Дополнительные мелочи

* `Alert severity="info"` для пустого markdown с PDF-fallback (`emptyMarkdownTryPdf`) — корректен, но без иконки и не закрывается.
* Лимит `getWorkChunks(... { limit: 200 })` (`ReaderWorkBody.jsx:74`) — для статьи с >200 чанками теряем хвост, но в UI ничего об этом не сказано (только короткая строка `chunksPartial`).
* PDF-режим `Suspense` падает back в текстовый загрузчик, но не показывает «PDF не доступен» как первичное сообщение, если `pdfAvailable=false` — текущий код прячет toggler. ОК, но не описано в i18n что произошло.

---

## 2. Цель серии RX

* Reader-страница превращается из **«дев-инспектора чанков»** в **«удобный документ-вьюер»** уровня Notion / Obsidian / Cursor docs view: красивый Markdown, формулы, переводимый интерфейс, человеко-читаемый заголовок и метаданные.
* Чанки и trace-параметры остаются полностью функциональными, но визуально уходят в «контекст ссылки» / «дев-режим».
* Перевод EN ↔ RU становится встроенной фичей бэкбона (LLM с пулом конкуренции), переиспользуемой будущими волнами (idea-assist explainer, summary regenerate и т. д.).
* Дисциплина настроек LLM-конкуренции: **один источник истины** в `config.py` (`llm_concurrency_*`), а не россыпь полей-сирот.

---

## 3. Серия волн RX (Reader eXperience)

### 3.1 Wave RX1 — Reader IA & layout (структура страницы)

**Что:**

* Удалить пермаментный TextField `work_id` со страницы. Когда `work_id` присутствует:
  * Header: `eyebrow="Чтение"`, `title=detail.title || "(без названия)"`, `subtitle=year + venue + DOI`.
  * Правый верхний угол — `CursorIconButton` с иконкой `ContentCopy` для копирования work_id; tooltip «Скопировать work_id».
* Когда `work_id` пуст:
  * Hero: «Открыть Workspace» (CTA, ведёт на `/workspaces`) + «Recent works» (берём из `persistWorkId` истории, если расширим до списка) или хотя бы one-shot ссылка на последний открытый work.
  * Под disclosure «Открыть по work_id» — спрятать туда исходный TextField (для разработчиков и Phoenix-трасс).
* Двухколоночный layout на `lg+`:
  * Левая `<ReaderSideRail>`: TOC (см. RX3), мета (year/venue/DOI/authors[0..3]+more), статус-чипы (`semantic`, `has_chunks`, `has_pdf`, `language=en|ru|…`), кнопки перевода (см. RX5), traceability buttons.
  * Правая колонка: Markdown body (см. RX2).
* Удалить дублирующий `PageHeader` description («Читайте извлечённый текст по `work_id`») — заменить на нейтральный subtitle.
* `mainShellContentSx` оставить, но Reader на `lg+` использует **полную** ширину до 1680 px (с 280-px sidebar и `maxWidth: 880px` у body); на `xl` — поднять кап до `1920px` именно для Reader (override через локальный `sx`).

**Файлы:** `ui/src/pages/ReaderPage.jsx`, `ui/src/components/work/ReaderWorkBody.jsx`,
новый `ui/src/components/work/ReaderShell.jsx`, новый `ui/src/components/work/ReaderSideRail.jsx`,
`ui/src/i18n/messages/{en,ru}/partReaderBody.js` + `partReaderShell.js` (новый ключ-неймспейс).
Settings: ничего.

**Acceptance:**

* На `/reader?work_id=…` нет TextField по умолчанию; заголовок страницы — название статьи, не «Чтение».
* На `lg+` body занимает «обычную колонку чтения» (640–880 px), слева компактный rail.
* На `md` и ниже — линейный поток (rail сворачивается в `Accordion` сверху).
* `npm run lint` / `npm run test` зелёные.

**Synergy:** разблокирует RX2/RX3/RX5 (даёт кадр для Markdown-вьювера и rail-кнопок); закрывает первый пункт жалобы пользователя про `work_id`.

**Сложность:** ~1 день.

### 3.2 Wave RX2 — красивый Markdown-рендер

**Что:**

* Зависимости в `ui/package.json`:
  * `react-markdown@^9.x`
  * `remark-gfm@^4.x` (таблицы, footnotes, task list)
  * `remark-math@^6.x`, `rehype-katex@^7.x`, `katex@^0.16.x` (формулы)
  * `rehype-highlight@^7.x` + `highlight.js@^11.x` (подсветка кода; subset languages)
  * `rehype-slug@^6.x` (auto-id для якорей TOC)
  * `rehype-external-links@^3.x` (`target="_blank" rel="noopener noreferrer"` авто).
* Новый компонент `ui/src/components/work/MarkdownView.jsx`:
  * Принимает `source: string`, `maxWidth: number = 880`, `onAnchor?: (id) => void`.
  * Регистрирует kit плагинов; mui-обёртка для `code`, `table`, `blockquote`, `a`.
  * Стили — соответствуют Cursor-канону (`#0a0a0a` фон body, `rgba(255,255,255,0.85)` текст, ссылки `rgba(129,140,248,0.95)`, тонкие границы у table/blockquote).
* В `ReaderWorkBody.jsx` `combinedExtractedText` рендерится через `MarkdownView` (на месте `<Typography pre-wrap>`); внешний `Box` без `maxHeight` (естественная высота).
* Лимит `120_000` символов снять; если длина > `400_000` — рендерить по секциям (split по `## `, mount только видимых через `IntersectionObserver`). Это можно вынести в Wave RX3 (TOC + lazy mount) — для RX2 хватит честного полного рендера.
* Загрузка KaTeX CSS — отдельный side-effect import (`import "katex/dist/katex.min.css"`); проверить, что не утекает в чужие страницы (импорт лежит внутри `MarkdownView`).
* Удалить ToggleButtonGroup `Markdown / PDF` сверху и заменить на иконочный `CursorButton` с `Article` / `PictureAsPdf` (продолжение RX1 в рамках RX2 PR).

**Файлы:** `ui/package.json`, `ui/package-lock.json`, новый `ui/src/components/work/MarkdownView.jsx`,
`ui/src/components/work/MarkdownView.test.jsx` (smoke рендер заголовков, таблицы, кода, формулы, ссылки),
`ui/src/components/work/ReaderWorkBody.jsx`, новый `ui/src/i18n/messages/{en,ru}/partMarkdownView.js` (если будут UI-метки типа «Copy code»).

**Acceptance:**

* `## Section` → визуальный H2; `**bold**` → жирный; таблица отрисовывается; формула KaTeX рендерится; внешние ссылки открываются с `target="_blank"`; код подсвечивается.
* Bundle size impact задокументирован в PR (KaTeX CSS ~25 KB gzip; highlight.js subset — ~30 KB; react-markdown+plugins ~40 KB) — **opt-in lazy-import** компонента (использовать `lazy()` как уже делается с `PdfViewer`).
* `npm run lint` / `npm run test` зелёные; smoke-тест проверяет, что для типичной статьи (2–5 разделов, 10–40 KB markdown) DOM содержит `<h2>`, `<table>`, `<code class="hljs ...">`, `.katex` (минимум один из).

**Synergy:** прямая закрытие пункта 1.3 жалобы; разблокирует RX3 (TOC берёт `<h*>` элементы).

**Сложность:** ~1.5 дня (с unit-тестами и проверкой bundle).

### 3.3 Wave RX3 — TOC sidebar + section anchors

**Что:**

* Из `chunks.items[].section_path` собираем дерево разделов (split по `/` если иерархия) и нумеруем якоря (`section-1`, `section-1-1`, …).
* `ReaderSideRail` (создан в RX1) рендерит `<TableOfContents>` с активным разделом (по `IntersectionObserver` за `<h2>` в Markdown body).
* Клик по разделу — `scrollIntoView({ behavior: "smooth", block: "start" })` с offset 16 px от sticky page-header.
* Переход из Ask/Evidence с `focusedSection=...` — авто-скролл на нужный раздел; кратковременная подсветка (`@keyframes flash` 1.5 с) — заменяет текущую `Chip "focused"` на чанке.
* Lazy-mount тяжёлых разделов (>50 KB markdown в одном разделе) с placeholder `Loading section…`.

**Файлы:** новый `ui/src/components/work/ReaderTableOfContents.jsx`, `ReaderSideRail.jsx`,
`ui/src/components/work/MarkdownView.jsx` (поддержка `onMountedSection` колбэка),
`ui/src/i18n/messages/{en,ru}/partReaderShell.js` (ключи `reader.toc.title`, `reader.toc.empty`).

**Acceptance:**

* TOC появляется при ≥ 2 разделах; при < 2 — скрыт (просто метаданные в rail).
* Активный раздел подсвечен; deep-link `?section=Methods` работает (после RX1 + RX3).
* `npm run lint` / `npm run test` зелёные.

**Synergy:** опора для traceability (вместо чанк-чипов навигация по разделам — куда пользователю ближе); готовит почву для RX4 (`scroll-to-translation` карточек).

**Сложность:** ~1 день.

### 3.4 Wave RX4 — chunks как dev-only / trace context

**Что:**

* В `ReaderWorkBody` секция «Чанки (дополнительно)» по умолчанию **не рендерится** (даже сворачиваемой).
* Условия рендера:
  1. `import.meta.env.VITE_READER_DEV_PANEL === "1"` — глобальный dev-флаг (для разработчиков).
  2. `searchParams.get("dev") === "1"` — per-request override.
  3. Активна traceability: `focusedFingerprint || focusedSection || citation` — тогда показываем **компактный** «Trace context» (1 чанк в фокусе + 0–2 соседних) с кнопкой «Show all chunks», которая раскрывает существующий полный список.
* Переименовать UI-копию: `Чанки (дополнительно) → Trace context (отрывки источника)` (RU) / `Trace context (source excerpts)` (EN); под dev-флагом добавить «Developer chunks (Qdrant raw)».
* `getWorkChunks(workId, { limit: 200 })` сохранить (всё равно нужен для `combinedExtractedText`); но в случае не-trace и не-dev режима — **сократить** до того лимита, что нужен для ToC и body (см. RX3 — потоково по секциям).

**Файлы:** `ui/src/components/work/ReaderWorkBody.jsx`, `ReaderShell.jsx`,
`ui/src/i18n/messages/{en,ru}/partReaderBody.js`,
доку — `docs/specs/frontend-ui-api-contracts-v1.md` (отметить `?dev=1` как client-only flag для Reader).

**Acceptance:**

* В обычном режиме `/reader?work_id=…` нет блока «Чанки» в DOM.
* `/reader?work_id=…&chunk_fp=abc` показывает Trace context с подсветкой нужного чанка (по якорю секции — RX3).
* `/reader?work_id=…&dev=1` — полный текущий блок чанков с фильтрами и счётчиком; визуально помечен бейджем `dev`.
* `npm run lint` / `npm run test` зелёные.

**Synergy:** закрывает пункт 1.4 жалобы; снижает когнитивную нагрузку Reader без потери трассируемости.

**Сложность:** ~0.5 дня.

### 3.5 Wave RX5 — UI перевода (translate panel)

**Зависит от:** Track LX (см. §6) — нужны backend-эндпоинты `POST /v1/works/{id}/translate/abstract` и `POST /v1/works/{id}/translate/body` плюс SSE-подписка прогресса. Если LX1/LX2 ещё не закрыт — UI делается с моком, который запускает LX2 при готовности.

**Что:**

* Detection языка статьи:
  * **Backend** (LX-сторона) добавляет в `Work` поле `language` (ISO 639-1, например `"en"`); если детекция не делалась при ingest — fallback на `null` и дать UI кнопку «Detect language» (LLM или быстрый эвристический detector — см. LX1).
  * **UI** показывает чип `EN` / `RU` / `…` рядом с заголовком; tooltip «Язык статьи».
* Когда `language !== uiLocale`:
  * В `ReaderSideRail` появляются **две** кнопки:
    1. «Перевести аннотацию» (`CursorPrimaryButton`, иконка `Translate`).
    2. «Перевести полный текст» (`CursorButton`, иконка `Translate` + lower-emphasis).
  * Под кнопками — статус-строка: `Готово 4 / 18 разделов` (live прогресс через SSE).
  * Tooltip объясняет: «Перевод выполняется LLM ({{model}}); на стороне сервера ограничено `{{maxConcurrency}}` параллельных запросов».
* Когда перевод готов — переключатель **Original / Translated** (ToggleButtonGroup из дизайн-канона); перевод хранится **на сервере** (см. LX2) и при повторном открытии работы загружается без повторного LLM-вызова. Кэш-ключ: `(work_id, target_lang, model_version)`.
* Показ перевода — внутри `MarkdownView` (RX2): абзацы / разделы с переведённым текстом + опция «показать оригинал inline» (подсветка двуколончно на `xl+`, или раскрывающийся блок «Оригинал» под каждым переведённым абзацем — выбор UX в Wave RX5 Phase B).
* Translate триггеры:
  * Per-chunk кнопки в режиме `dev` — для тестирования качества (вернуть конкретный chunk).
  * Глобальная кнопка «Re-translate» (если у пользователя есть права) с подтверждением «перезапишет существующий кэш».
* Метрика времени: показываем оценку «~30 секунд» (по `total_chunks * avg_chunk_ms / max_concurrency`) — расчёт из снимка настроек (LX-сторона).

**Файлы:** новый `ui/src/components/work/ReaderTranslatePanel.jsx`, `ui/src/services/research/translate.js`,
`ui/src/hooks/useTranslateStream.js` (по образцу `useJobStream`/`useAgentStream`),
`ui/src/i18n/messages/{en,ru}/partTranslate.js`,
расширение `ReaderShell.jsx` / `ReaderSideRail.jsx`.

**Acceptance:**

* На EN-статье в RU-локали видно две кнопки и чип `EN`.
* Перевод аннотации идёт ~5–10 секунд; полный текст потоково (видны секции по мере готовности).
* После перезагрузки страницы перевод подтянут без повторного LLM-вызова (если кэш на сервере).
* Toggle «Original / Translated» работает, без потери TOC-навигации (RX3).
* `npm run lint` / `npm run test` зелёные; smoke-тест на mock-сервере (фикстура fake SSE).

**Synergy:** прямая реализация пункта 1.6; будущая фича «summary EN→RU» / «idea-assist на родном языке» сразу пользуется backend-инфраструктурой LX.

**Сложность:** ~2 дня (UI), при готовом backend.

### 3.6 Wave RX6 — Reader visual polish (icons, chips, header)

**Что:**

* Все кнопки переключаются на `Cursor*` family (см. дизайн-канон в osint-gr `.cursorrules` и проект-канон в frontend-design skill).
* Иконки из `@mui/icons-material`:
  * `Article`, `PictureAsPdf` — переключатель режима.
  * `OpenInNew`, `AccountTree` — внешние ссылки.
  * `ContentCopy` — копировать work_id / DOI.
  * `Bookmark` / `BookmarkBorder` — закладка работы (опционально, без backend в RX6, только localStorage).
  * `Translate` — перевод (RX5).
  * `Code`, `BugReport` — dev-mode badges.
* Карточка деталей:
  * Чип DOI как `<Chip clickable onClick=copy>`.
  * Чип Year, чип Venue, цепочка авторов (первые 3 + `+5 more`).
  * Бейджи: `semantic` (зелёный пунктир), `has_chunks` (нейтральный), `claims=12` (`Chip color=primary`).
* Типографика:
  * Заголовок статьи — `H1` 22 px, `lineHeight: 1.2`, `letterSpacing: -0.01em`.
  * Body Markdown — 15 px `lineHeight: 1.65`, `fontFamily: ui-serif, Georgia, "Times New Roman", serif` (научный текст лучше читается серифом — обсудить дизайн-выбор перед merge).
* Borders / radius везде `6px`; убрать `4px` из inner Markdown box.
* `Alert` про PDF-fallback — иконка `InfoOutlined`, dismissible.

**Файлы:** `ReaderShell.jsx`, `ReaderSideRail.jsx`, `MarkdownView.jsx`,
`ReaderWorkBody.jsx`, `ui/src/components/work/ReaderHeader.jsx` (если выделится из shell).

**Acceptance:**

* Визуально страница соответствует canva из `frontend-design` skill (компактная, плотная типографика, тонкие границы, акценты `rgba(99,102,241,*)`).
* Минимум 8 иконок добавлено (см. список выше).
* `npm run lint` зелёный; ручной screenshot-review в PR (без regression-snapshot — у проекта нет visual snapshot pipeline).

**Synergy:** закрывает пункт 1.5; ставит дисциплину для RX7 (если случится — rich abstract layout, citations footer).

**Сложность:** ~1 день.

### 3.7 Wave RX7 — Unify ReaderTab and ReaderPage (composition shell)

**Что:**

* Вынести общий `<ReaderShell workId, mode={"standalone"|"workspace-tab"}>` (создан в RX1) и переиспользовать его и в `ReaderPage.jsx`, и в `WorkspacePage/tabs/ReaderTab.jsx`.
* Удалить дублирование «Open Reader (workspace)» / «Open Graph» — оставить общий `<ReaderTraceabilityFooter>` под body.
* `ReaderClaimsPanel` (Wave O) — включить в shell под флагом `VITE_CLAIMS_UI_ENABLED`; перестать держать его только в табе.
* В `WorkspacePage/tabs/ReaderTab.jsx` оставить только пред-render (workId) + chrome ссылок workspace; внутренности — `<ReaderShell>`.

**Файлы:** `ui/src/components/work/ReaderShell.jsx`, `ui/src/pages/ReaderPage.jsx`,
`ui/src/pages/WorkspacePage/tabs/ReaderTab.jsx`.

**Acceptance:**

* В обоих контекстах одинаковый header / sidebar / Markdown / claims-секция.
* Отличие двух точек входа — только chrome (mode-specific кнопки workspace-навигации).
* `ReaderWorkBody.jsx` → 280 строк или ниже (закрывает пункт `[OPEN] Split ReaderWorkBody.jsx (485)` из `refactor-frontend.md`).
* `npm run lint` / `npm run test` зелёные.

**Synergy:** закрывает пункт 1.7 + бэклог-пункт `H-ReaderWorkBodySplit`; готовит к Wave M (PDF page citations) — обоим контекстам сразу.

**Сложность:** ~0.5 дня.

---

## 4. Ожидаемые DON’T-зоны и потенциальные регрессии

* **Lazy-mount Markdown по секциям** (RX2/RX3) может ломать «найти на странице» (`Ctrl-F`) — секции не в DOM не находятся. Mitigation: в RX3 lazy-mount только для секций > 50 KB, или дать «Expand all sections» кнопку в TOC.
* **KaTeX** добавляет ~25 KB CSS, грузить только в Reader (lazy import `MarkdownView`).
* **highlight.js** subset (`python`, `bash`, `json`, `yaml`, `text`) — full bundle 200 KB+, нужен `core` + per-language imports.
* `react-markdown` несовместим с прямой вставкой `dangerouslySetInnerHTML` — это плюс (XSS-безопасность), но если в чанках есть HTML-вставки, они **не отрендерятся**. Проверить выборку: после `# научная статья из PDF/Markdown` HTML встречается редко; если встречается — добавить `rehype-raw` под флагом + sanitize (`rehype-sanitize`).
* Перевод (RX5) — стоимость токенов. Дать **оценку** до запуска (`{{n_chunks}} × {{avg_tokens}} → ~$X`) и кнопку «Cancel» по ходу прогресса (отмена SSE + abort актора на бекенде — это уже идёт в LX2).
* Удаление поля `work_id` (RX1): пользователь, который заходил «по адресу с пустым query» и копировал id руками, должен иметь disclosure «Open by work_id». **Критично:** в Phoenix трассах этот флоу — единственный способ открыть конкретный пример. Disclosure обязательно.

---

## 5. План UI-волн в Sprints

| Sprint | Wave RX | Зависимости |
|--------|---------|-------------|
| S6+ (после Round 5/6 master-roadmap) | RX1 + RX2 (один PR — IA + Markdown render) | независимо; запустить параллельно с любой backend-волной (по матрице — отдельная файловая зона `ui/src/{components/work,pages}/Reader*`) |
| S6+ | RX3 (TOC) + RX4 (chunks dev-only) | требует RX1 (shell) и RX2 (heading anchors) |
| S7 (см. master-roadmap S7) | RX6 (visual polish) | независимо; делается в параллели с любым backend |
| S8 (после LX1+LX2) | RX5 (translate UI) | требует Track LX (см. §6) |
| Sprint cleanup | RX7 (unify shell + закрыть `H-ReaderWorkBodySplit`) | после RX1..RX6 |

В master-roadmap §6 (матрица параллельности) — RX1..RX7 безопасно параллельны со всеми Backend (G/D/B/E) и любыми frontend, **кроме** одновременной правки `ReaderWorkBody.jsx` (например, бэклог-пункт `H-ReaderWorkBodySplit` объединяется с RX7, а не идёт отдельно).

---

## 6. Track LX — LLM concurrency cluster + translation backend (поддерживающий)

> **Цель:** установить единые правила, как любая новая LLM-операция (перевод, summary, idea-assist re-run, claims rerun, future agent calls) ограничивается по конкуренции и берёт credentials. Прекратить плодить `*_max_concurrency`-поля по фичам.

> **Статус 2026-04-27:** реализован **partial slice** — см. §11 и `docs/backlog/refactor-backend.md` (Completed + OPEN «LX1 integration…»). Полный acceptance §6.1–6.2 (приоритетный resolver двух legacy ключей, UI Settings, реальный перевод + Phoenix) — **не** закрыт.

### 6.1 Wave LX1 — settings cluster `llm_concurrency_*`

**Что:**

* В `science_graphrag/config.py` ввести группу полей под Pydantic-секцию (или просто префикс):
  * `llm_concurrency_default: int = Field(default=3, ge=1, le=32)` — общий cap на ad-hoc LLM-вызовы (translate, summary, idea-assist live).
  * `llm_concurrency_extraction_references: int = Field(default=1, ge=1, le=8)` — заменяет существующее `extraction_llm_references_max_concurrency` (с alias для обратной совместимости).
  * `llm_concurrency_translation: int = Field(default=4, ge=1, le=16)` — для RX5.
  * `llm_concurrency_claims: int = Field(default=2, ge=1, le=8)` — задел для будущей перерегенерации claims (Wave O follow-up).
  * `llm_concurrency_summary: int = Field(default=2, ge=1, le=8)` — для re-summarize кнопки workspace (Wave WX*).
* Переиспользуемый `science_graphrag/utils/llm_semaphore.py` — `asyncio.Semaphore`-фабрика по ключу + thread-pool обёртка для синхронных пайплайнов (как `extract_references_chunk` сейчас через `ThreadPoolExecutor`).
* В `.env.example` добавить блок:
  ```
  # LLM concurrency caps (Track LX)
  SCIENCE_GRAPHRAG_LLM_CONCURRENCY_DEFAULT=3
  SCIENCE_GRAPHRAG_LLM_CONCURRENCY_TRANSLATION=4
  # legacy alias (используется ingestion/llm/orchestrator.py):
  # SCIENCE_GRAPHRAG_EXTRACTION_LLM_REFERENCES_MAX_CONCURRENCY=1
  ```
* Settings UI: расширить `SettingsPage/IngestionSettingsPanel.jsx` (или вынести в новый `SettingsPage/LlmRuntimeSettingsPanel.jsx`) — поля чтения текущих значений и подсказки. Запись необязательна в LX1 (env-only достаточно для первой итерации).

**Файлы:** `science_graphrag/config.py`, новый `science_graphrag/utils/llm_semaphore.py`,
`science_graphrag/ingestion/llm/orchestrator.py` (миграция на новый ключ через alias),
`tests/config/test_llm_concurrency_alias.py` (новый),
`.env.example`.

**Acceptance:**

* `pytest` зелёный; `Settings(llm_concurrency_extraction_references=2, extraction_llm_references_max_concurrency=4)` корректно резолвится по приоритету (новое поле побеждает; алиас даёт WARNING в логе).
* Pylint / black / isort чисто.

**Synergy:** разблокирует LX2 + любые новые ad-hoc LLM-фичи; закрывает пункт 1.6 жалобы (ту его часть, что «нужно завести в .env, настройках»).

**Сложность:** ~0.5 дня.

### 6.2 Wave LX2 — translation backend (chunked, async, semaphore, persistence)

**Зависит от:** LX1 (settings + semaphore).

**Что:**

* Новый пакет `science_graphrag/translation/`:
  * `language_detector.py` — быстрый detector (heuristic + опциональный LLM fallback). Детектируем по первым ~2 KB `abstract` + `chunks[0..2].text`. Возвращаем ISO 639-1.
  * `translator.py` — `async def translate_chunks(chunks, source_lang, target_lang, *, settings, semaphore)`; разбивает на батчи (по `n` чанков или `n` токенов), использует тот же `ChatOpenAI` через OpenRouter, что и agent (`science_graphrag/agent/llm/chat.py`); шаблон промпта в `prompts/translate_v1.md` + `prompts.py`.
  * `cache.py` — Postgres-таблица `work_translations(work_id, target_lang, source_lang, model_version, abstract_md, body_md, status, started_at, finished_at, error)` или Neo4j-узел `:Translation` (предпочтительно Postgres — translations не граф-сущность, рядом с `BenchmarkTaskStore`).
  * `runner.py` — оркестратор: проверяет cache → запускает `translate_chunks` под `semaphore` → пишет результат → эмитит SSE.
* Новые эндпоинты:
  * `POST /v1/works/{work_id}/translate/abstract?target_lang=ru` — синхронный (быстрый), возвращает `{ "abstract_md": "...", "model": "...", "tokens_in": N, "tokens_out": M }`.
  * `POST /v1/works/{work_id}/translate/body?target_lang=ru` — kicks off async job, возвращает `job_id`.
  * `GET /v1/works/{work_id}/translate/body/events?target_lang=ru` — SSE: `progress` (`done_chunks/total_chunks`, `chunk_index`, `section_path`), `done` (полный markdown), `error`.
  * `GET /v1/works/{work_id}/translate?target_lang=ru` — выдаёт сохранённый перевод (для повторного открытия Reader).
* Phoenix span: `chain_span("translation.body", attributes={...})` + per-chunk `llm_span` — обязательно (правило 5 master-roadmap).
* Глубокая интеграция с языком работы:
  * `Work.language` — заполняется при ingest (новый шаг в `ingestion/pipeline.py` Stage X) — детект-и-сохранить; миграция Neo4j для уже загруженных работ — фоновый script `scripts/backfill_work_language.py`.
  * `GET /v1/works/{work_id}` (`detail.py:183`) — добавить поле `"language"` в ответ.

**Файлы:** новый `science_graphrag/translation/{__init__.py,language_detector.py,translator.py,cache.py,runner.py,prompts.py,prompts/translate_v1.md}`,
`science_graphrag/api/translation.py` (router) → монтировать в `api/main.py`,
`science_graphrag/ingestion/pipeline.py` (новый шаг language detect),
`science_graphrag/storage/neo4j/writes/works.py` (set `language`),
миграция Postgres `science_graphrag/storage/sql/migrations/00X_translations.sql`,
`tests/translation/test_translator.py`, `tests/api/test_translation_endpoints.py`,
`docs/specs/translation-v1.md` (новый), `docs/architecture/observability-phoenix.md` (добавить `translation.*` spans).

**Acceptance:**

* `pytest tests/translation tests/api/test_translation_endpoints.py` — зелёные с моком LLM.
* `POST /v1/works/{id}/translate/abstract?target_lang=ru` для EN-статьи возвращает RU-текст за ≤ 6 с (на dev LLM).
* SSE-стрим body перевода даёт `progress` каждые 1–5 с; завершается `done` с full markdown; повторный POST возвращает кэш без LLM-вызовов.
* В Phoenix UI виден `translation.body` chain span с детьми `llm.chat` (по числу батчей).
* Pylint / black / isort чисто.

**Synergy:** даёт backend для RX5; закрывает пункт 1.6 жалобы целиком; задел для будущих LLM-операций (любая новая фича подключается через `llm_semaphore.acquire(name="translation")`).

**Сложность:** ~3 дня (с тестами, миграцией и spec).

### 6.3 Wave LX3 — Settings UI для LLM cluster (опционально)

**Зависит от:** LX1.

**Что:**

* Расширить snapshot Settings (`api/settings.py`) полями `llm_concurrency_*`.
* В UI `SettingsPage/IngestionSettingsPanel.jsx` или новой панели `SettingsPage/LlmRuntimeSettingsPanel.jsx` отрендерить slider/number-input для каждого ключа.
* Сохранять через PUT (если уже есть write-path; иначе read-only с подсказкой `Set via .env / SCIENCE_GRAPHRAG_LLM_CONCURRENCY_*`).

**Acceptance:**

* В Settings видны текущие значения; при write-mode — изменение применяется без рестарта (через runtime overrides, как уже сделано для других секций).

**Synergy:** UX для админа — без редактирования `.env` подкручивает скорость перевода / extraction.

**Сложность:** ~0.5 дня.

---

## 7. Acceptance трека RX (общее)

* `/reader?work_id=…` для типичной EN-статьи (4–6 авторов, 8–12 разделов, 50–80 KB markdown, 32 чанка):
  * Видим название статьи как `H1`, метаданные с иконками, кнопку «Перевести аннотацию».
  * Body отрендерен как настоящий Markdown (заголовки, списки, таблицы, формулы, код, ссылки).
  * Слева TOC; клик прокручивает в раздел.
  * Нет блока «Чанки (дополнительно)» по умолчанию.
  * Полная ширина body 720–880 px, центрирована, читабельная мера.
* `/reader?work_id=…&chunk_fp=abc&section=Methods` — авто-скролл и подсветка раздела.
* `/reader?work_id=…&dev=1` — старый «Чанки (дополнительно)» виден с флагом `dev`.
* После RX5: чип `EN`, кнопки перевода — переводят аннотацию за ≤ 10 с, тело потоково; повторное открытие подтягивает кэш.
* `npm run lint`, `npm run test` зелёные на каждой Wave.
* После RX7: `ReaderWorkBody.jsx` ≤ 280 строк, ни один Reader-компонент не превышает 400.

## 8. Acceptance трека LX (общее)

* `Settings` снимок содержит `llm_concurrency_default`, `llm_concurrency_translation`, `llm_concurrency_extraction_references`, `llm_concurrency_claims`, `llm_concurrency_summary`.
* `extraction_llm_references_max_concurrency` сохраняется как alias и ловится тестом регрессии.
* В Phoenix UI видны spans `translation.body`, `translation.abstract`, дети — `llm.chat`.
* Cache: повторный `POST /translate/body` для уже переведённого `work_id × target_lang × model_version` не вызывает LLM (≤ 50 ms response).

---

## 9. Открытые вопросы

1. **Шрифт body в Reader (sans vs serif).** Решить до RX6: научный текст лучше читается серифом, но проект-канон — Inter sans 13 px. Возможен smart-toggle (`Settings → Reader font`).
2. **Lazy-mount markdown секций vs Ctrl-F.** Зафиксировать порог; альтернатива — рендерить всё, замерить производительность на 80 KB markdown.
3. **Где хранить переводы:** Postgres (предпочтительно — рядом с `task_store`) vs Neo4j-узлы `:Translation`. Postgres проще, не загрязняет граф.
4. **Цена перевода**. Нужна оценка стоимости + кнопка cancel (RX5 + LX2). Зафиксировать UX согласия пользователя на стоимость > $X.
5. **Detection language.** Heuristic vs LLM-based. Heuristic дешевле, но шумит на multilang-статьях. Возможен двухэтапный: heuristic → если confidence < 0.8 → LLM-classifier 1 чанк.
6. **Source-aware translation.** Для научных статей сохранять формулы/код/таблицы как есть, переводить только prose. Промпт `translate_v1.md` должен это учитывать (инструкция «do not translate inside fenced code or `$$...$$`»).
7. **`Work.language` для уже залитых статей.** Без backfill UI на старых данных не покажет чип EN/RU. Фоновый job с rate-limit или кнопка «Detect now» в Reader (RX5 phase B).
8. **Аутентификация перевода.** Cost guardrail: если в проекте появятся пользователи без прав, перевод должен требовать роль / WORKSPACE_OWNER. На текущей фазе single-user — не критично, но spec должен оговорить.

---

## 10. Что добавить в master-roadmap

В [`master-roadmap-and-refactor-plan-2026-04-25.md`](master-roadmap-and-refactor-plan-2026-04-25.md) — добавить:

1. **Track RX (Reader UX):** в §2 «Картина треков». Источник — этот документ. Текущая волна — RX1 + RX2 готовы к старту параллельно с любым backend в Sprint S6+.
2. **Track LX (LLM concurrency + translation):** в §2. Источник — этот документ §6. Текущая волна — LX1, далее LX2.
3. В §3 «Граф зависимостей» — блок:
   ```
   Wave RX1 (IA + layout) ── Wave RX2 (markdown render)
                      │              │
                      │              └── Wave RX3 (TOC + anchors) ── Wave RX4 (chunks dev-only)
                      │                                                       │
                      │                                                       └── Wave RX6 (visual polish)
                      │                                                                  │
                      │                                                                  └── Wave RX7 (unify shell)
                      │
                      └── Wave LX1 (settings cluster) ── Wave LX2 (translation backend) ── Wave RX5 (translate UI)
                                                                                          │
                                                                                          └── Wave LX3 (settings UI, opt)
   ```
4. В §4 — новый подраздел **4.7 Track RX (Reader UX)** и **4.8 Track LX (LLM concurrency + translation)** с кратким изложением целей и acceptance каждой волны (ссылается сюда).
5. В §6 (матрица параллельности) — новые строки/колонки:
   * `RX1+RX2` ↔ всё прочее: ✅ кроме ⚠️ с любой задачей, что одновременно правит `ReaderWorkBody.jsx`.
   * `RX5` ⛔ с `LX2` (если в одном раунде запускают оба и оба правят `api/translation.py` / SSE-контракт — последовательно).
   * `LX1` ↔ всё прочее: ✅ (только `config.py` + `utils/llm_semaphore.py`).
   * `LX2` ⚠️ с любой backend-волной, которая трогает `ingestion/pipeline.py` (LX2 добавляет stage language-detect).
6. В §7 «Запуск Cursor-агентов параллельно» — после Раунда 7 ввести Раунд 8 (RX1+RX2+LX1+H-ReaderWorkBodySplit), а перевод (RX5+LX2) — Раунд 9.
7. В §10 «Ссылки» — ссылка на этот документ (`docs/analysis/reader-ux-and-translation-roadmap-2026-04-25.md`).

---

## 11. Backlog-записи (что добавить в `refactor-{frontend,backend}.md`)

### Frontend (`docs/backlog/refactor-frontend.md`)

* **[OPEN] Reader Wave RX1** — IA & layout (см. §3.1 этого документа).
* **[OPEN] Reader Wave RX2** — Markdown viewer (`react-markdown` + math + code).
* **[OPEN] Reader Wave RX3** — TOC + section anchors.
* **[OPEN] Reader Wave RX4** — chunks dev-only / trace context.
* **[OPEN] Reader Wave RX5** — translate panel UI (depends on LX2).
* **[OPEN] Reader Wave RX6** — visual polish (icons, chips, header).
* **[OPEN] Reader Wave RX7** — unify ReaderTab + ReaderPage shell — **одновременно** закрывает существующий `[OPEN] Split ReaderWorkBody.jsx (485)`.

### Backend (`docs/backlog/refactor-backend.md`)

* **[PARTIAL 2026-04-27] LX1** — поля `llm_concurrency_*` + `utils/llm_semaphore.py` уже в репозитории; добавлены: синхронизация legacy `extraction_llm_references_max_concurrency` ↔ `llm_concurrency_extraction_references` в `Settings` + `tests/test_llm_concurrency_config.py`. **Остаётся OPEN:** подключить `build_llm_semaphore_map` к реальным LLM-путям (см. бэклог «LX1 integration…»); приоритет двух ключей при конфликте + Settings UI — по §6.1/6.3.
* **[PARTIAL 2026-04-27] LX2** — **есть:** `science_graphrag/api/translation.py` (SSE stub), router в `main.py`, Alembic `20260426_0007_work_translations`, ORM `WorkTranslationRecord`, `docs/specs/translation-v1.md`, заглушка-пакет `science_graphrag/translation/__init__.py`. **Остаётся OPEN:** `translation/{detector,translator,cache,runner}.py`, реальные ответы, Phoenix spans, language-detect ingest stage по §6.2.
* **[OPEN] LX3** — Settings UI snapshot extension (opt).
* **[OPEN] Stage in pipeline: language detection** — добавить шаг в `ingestion/pipeline.py` (Stage X) + backfill script (`scripts/backfill_work_language.py`).
