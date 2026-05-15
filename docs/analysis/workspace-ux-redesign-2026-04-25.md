# Workspace UX redesign — диагноз и план Wave WX1–WX6

**Doc status:** `reference`

**Read hint:** historical redesign diagnosis/plan for Workspace UX. For active product queue start from [`ACTIVE.md`](./ACTIVE.md), then use current backlog/runbooks.

**Дата:** 2026-04-25
**Статус:** living working doc; продолжение [`_archive/workspace-experience-gap-2026-04-24.md`](_archive/workspace-experience-gap-2026-04-24.md) [HISTORICAL]. Закрывает реальные пробелы между «панель работает» и «учёный понимает, в каком корпусе он находится и что происходит при загрузке» по треку **F (Workspace experience)** в [`master-roadmap-and-refactor-plan-2026-04-25.md`](master-roadmap-and-refactor-plan-2026-04-25.md).

**Триггер (2026-04-25, скриншоты `assets/image-7691ff3c-…`, `assets/image-2989e1ea-…`, `assets/image-2250fd94-…`):**
Пользователь открывает `/workspace?workspace_id=…` на 1920px-мониторе и видит:

1. **Контент ужат влево**, ~60% ширины экрана — пустой фон. Колонки `WorkspaceIngestPanel` (`maxWidth: 560`) и `WorkPaperCard` (`maxWidth: 720`) живут в одну левую полосу, при том что `mainShellContentSx` разрешает `min(1680px, 100%)`.
2. **Не понятно, какая рабочая область активна.** `WorkspaceContextChip` спрятан в правом верхнем углу `DashboardLayout`-хедера (28×220px), визуально неразличим. На самой странице есть только title `Research` и `paperCountMany`, но нет «куда я загружаю».
3. **Не понятно, как создать новую область.** Кнопка `Создать` есть только внутри `WorkspaceContextChip` `Popover` (надо догадаться кликнуть по чипу) и на отдельной странице `/workspaces`. На самой `/workspace` — никакой видимой CTA «новая область».
4. **При загрузке статьи показываются «Логи» в `<pre>`.** `IngestStageStepper` есть, но его перекрывает `Details / Logs` accordion, который сейчас и **раскрыт по умолчанию для нового job'а** (по факту — accordion свёрнут, но текст «Logs» доминирует визуально, а stage stepper лежит мелким `0.72rem`-списком). Нет общего progress-бара/процента, нет ETA, нет shimmer-эффекта на текущем шаге.
5. **Дубликаты — отдельная секция «Smart dedup»** внизу страницы, требует ручного запуска `Scan for near-duplicates` и говорит EN-only текстом. **При самом ingest** (когда LLM-pipeline уже встретил DOI/arXiv-совпадение или high-similarity vector) пользователь не получает confirmation card «Похоже, эта статья уже есть в области. Объединить или загрузить как отдельную?». Wave L1/L2 backend это уже умеет — UI-стороны нет.
6. **Иконок почти нет.** Кнопки `Чтение`/`Граф`/`Вопросы`/`Доказательства` на карточке статьи — голый текст; Drawer-пункты иконку имеют, но в основной зоне (header + ingest + dedup) визуального якоря нет.
7. **Хардкод-EN.** «Smart dedup (embeddings + LLM)», «Scan for near-duplicates», «Pending», «Review» — расходится с [`ui-i18n-guidelines.md`](../specs/ui-i18n-guidelines.md). Уже есть открытый бэклог-пункт `H-i18n-fixes` в [`refactor-frontend.md`](../backlog/refactor-frontend.md), но `WorkspaceDedupSection.jsx` туда не попал.

Этот документ:

- фиксирует диагноз с указанием конкретных файлов и строк;
- описывает целевой layout `WorkspacePage` («Active workspace hero» + двухколонная сетка + правильное использование пространства);
- расширяет план треком **F** на Wave **WX1** (layout + workspace hero), **WX2** (ingest progress redesign), **WX3** (ingest-time duplicate confirmation card), **WX4** (icons + visual hierarchy), **WX5** (workspace switcher + create CTA), **WX6** (i18n + cleanup smart dedup section);
- обновляет статус Track F в [`master-roadmap-and-refactor-plan-2026-04-25.md`](master-roadmap-and-refactor-plan-2026-04-25.md) и записывает open backlog-пункты в [`refactor-frontend.md`](../backlog/refactor-frontend.md).

**Связанные документы:**

| Документ | Что в нём |
|----------|-----------|
| [`_archive/workspace-experience-gap-2026-04-24.md`](_archive/workspace-experience-gap-2026-04-24.md) | [HISTORICAL] Исходный план Wave I/J/K/L (workspace-first, dedup, batch ingest) |
| [`master-roadmap-and-refactor-plan-2026-04-25.md`](master-roadmap-and-refactor-plan-2026-04-25.md) | Карта треков и параллельности; нуждается в правке статуса Track F |
| [`graph-readability-followup-2026-04-25.md`](graph-readability-followup-2026-04-25.md) | Параллельная серия Wave GR6–GR12 для графа; перекрытий по файлам нет |
| [`../specs/ui-ux-master-plan.md`](../specs/ui-ux-master-plan.md) | Целевая UI/UX-архитектура (workspace-first, work context) |
| [`../specs/frontend-ui-api-contracts-v1.md`](../specs/frontend-ui-api-contracts-v1.md) | UI ↔ API контракты, нуждается в обновлении после WX2/WX3 |
| [`../specs/ui-i18n-guidelines.md`](../specs/ui-i18n-guidelines.md) | i18n EN/RU дисциплина |
| [`../backlog/refactor-frontend.md`](../backlog/refactor-frontend.md) | Backlog для WX1..WX6 UI-частей |

---

## 1. Диагноз: что именно не работает

### 1.1 Layout: контент ужат влево, ширина не используется

[`ui/src/components/layout/mainShellContentSx.js`](../../ui/src/components/layout/mainShellContentSx.js) разрешает `width: 100%; max-width: min(1680px, 100%)`, но реальные дочерние блоки в [`WorkspacePage.jsx`](../../ui/src/pages/WorkspacePage/WorkspacePage.jsx) фиксированной ширины:

```92:103:ui/src/pages/WorkspacePage/WorkspaceIngestPanel.jsx
        sx={{
          mb: 2,
          p: 1.5,
          borderRadius: "6px",
          border: dragOver ? "1px dashed rgba(129,140,248,0.75)" : "1px solid rgba(99,102,241,0.22)",
          backgroundColor: dragOver ? "rgba(99,102,241,0.12)" : "rgba(99,102,241,0.06)",
          maxWidth: 560,
        }}
```

```47:56:ui/src/pages/WorkspacePage/WorkPaperCard.jsx
      sx={{
        p: 1.75,
        borderRadius: "6px",
        border: selected ? "1px solid rgba(129,140,248,0.55)" : "1px solid rgba(255,255,255,0.08)",
        backgroundColor: selected ? "rgba(99,102,241,0.12)" : "#1a1a1a",
        boxShadow: selected ? "0 0 0 2px rgba(129,140,248,0.35)" : "none",
        maxWidth: 720,
        cursor: onCardActivate ? "pointer" : "default",
        outline: "none",
      }}
```

В результате на 1920px viewport `WorkspacePage` рисует левую полосу 720px шириной и пустой правый блок ~1100px. На 1366px-ноутбуке проблема та же, только в меньшем масштабе.

### 1.2 «Активный workspace» спрятан в чип верхнего хедера

`Active workspace` сейчас — единственный визуальный якорь в `DashboardLayout` header (правый верхний угол):

```26:39:ui/src/components/layout/DashboardLayout/DashboardLayout.jsx
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "flex-end",
              gap: 1,
              px: { xs: 1.5, sm: 2 },
              py: 1,
              borderBottom: "1px solid rgba(255,255,255,0.06)",
              minHeight: 48,
            }}
          >
            <WorkspaceContextChip />
          </Box>
```

`WorkspaceContextChip` — Chip 28×220px с цветом `rgba(99,102,241,0.22)`. На общем тёмном фоне он не выделяется и пользователь читает его как «какой-то ярлык», а не как «вот мой текущий корпус, на этой странице любые действия применяются к нему». Создание новой области — за `Popover` внутри этого чипа (см. [`WorkspaceContextChip.jsx`](../../ui/src/components/layout/WorkspaceContextChip.jsx) lines 112–130). Это нарушает принцип «Workspace = единица работы» из [`_archive/workspace-experience-gap-2026-04-24.md`](_archive/workspace-experience-gap-2026-04-24.md) §1.1 [HISTORICAL].

`PageHeader` рисует сам title `workspaceMeta.name` и поясняющие строки про work_count / focused work / graph stats:

```397:461:ui/src/pages/WorkspacePage/WorkspacePage.jsx
      <PageHeader
        eyebrow={t("workspace.header.eyebrow")}
        title={workspaceMeta.name || t("workspace.header.titleFallback")}
        description={
          ...
          <span style={{ color: "rgba(255,255,255,0.55)", fontSize: "0.8125rem" }}>
            {effectiveWorkIds.length === 1
              ? t("workspace.header.paperCountOne", { count: String(effectiveWorkIds.length) })
              : t("workspace.header.paperCountMany", { count: String(effectiveWorkIds.length) })}
            {effectiveWorkIds.length > 1 && selectedWorkId ? (...) : null}
          </span>
          <br />
          <span style={{ color: "rgba(255,255,255,0.38)", fontFamily: "monospace", fontSize: "0.72rem" }}>
            {workspaceMeta.id}
          </span>
          ...
```

Но это plain title — не хватает: 1) визуального индикатора «active», 2) переключателя между областями inline (без открытия popover в шапке shell), 3) явной кнопки «новая область» рядом, 4) breadcrumb до общего списка областей.

### 1.3 Ingest progress: stage stepper «прячется» под Logs, нет общего %

Сейчас при заливке файла появляется блок job'а:

```148:241:ui/src/pages/WorkspacePage/WorkspaceIngestPanel.jsx
        {ingestJob ? (
          <Box sx={{ mt: 1.5 }}>
            <Typography sx={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.5)", fontFamily: "monospace" }}>
              {t("workspace.upload.jobLine", { id: String(ingestJob.job_id), status: String(ingestJob.status) })}
            </Typography>
            <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.65)", mt: 0.5 }}>
              {ingestJob.message || t("workspace.upload.dash")}
            </Typography>
            {Array.isArray(ingestJob.stages) && ingestJob.stages.length ? (
              <IngestStageStepper stages={ingestJob.stages} />
            ) : (
              <LinearProgress
                variant="determinate"
                value={Math.min(100, Math.max(0, Number(ingestJob.progress_current) || 0))}
                ...
              />
            )}
            ...
            {ingestJob.logs ? (
              <Accordion
                ...
                <AccordionSummary sx={{ fontSize: "0.72rem", minHeight: 32 }}>Details / Logs</AccordionSummary>
                ...
```

Проблемы:

- **Когда пришли `stages` — общего progress-бара нет.** Stepper рисует «✓/●/○» по каждой стадии, но единая полоса с «42% общий прогресс» отсутствует, поэтому пользователю не понятно «сколько ещё ждать».
- **Нет shimmer-индикатора активной стадии.** `statusSymbol("running")` — просто `●` цвета `rgba(255,255,255,0.9)`. Чтобы понять «эта стадия сейчас идёт», нужно сравнить иконку с другими — медленно для глаза.
- **Logs accordion доминирует визуально.** Заголовок «Details / Logs» захардкожен EN, дёргает внимание к технической информации. Раскрытие показывает `<pre>` высотой 140px с потоком `[17:02:36] Saved 2995202 bytes → ce3dea15-…`, что не нужно конечному пользователю.
- **Stage names не локализованы** — приходят с бэка как `"vl_extract"`, `"chunking"`, `"embed_chunks"`, `"neo4j_persist"` и т. д. Stepper показывает их as-is. На ru-локали это режет глаз.
- **Нет ETA.** Хотя backend в `IngestStageStepper` уже даёт `duration_ms` для завершённых стадий, оценка остатка не считается.

### 1.4 Куда грузится файл — не видно в зоне загрузки

Внутри `WorkspaceIngestPanel.jsx` показывается только title «Загрузка статьи» и описание «PDF, Markdown или текст. Обработка на сервере…», **но имени активной workspace там нет**. Пользователь, кликая «Выбрать файл», читает только этот блок и не видит, в какой корпус попадёт результат. Связь с `workspaceMeta.name` есть в `PageHeader`, но он ушёл вверх и оторван от ingest-зоны.

Также при отсутствии активной области (`workspaceMeta.id === ""`) `WorkspaceIngestPanel` просто `return null` (строка 85), а `WorkspacePage` показывает `emptyState` — info-alert «Создайте рабочую область в списке» + кнопка `/workspaces`. Это **не работает inline**: чтобы создать область, пользователь должен покинуть страницу.

### 1.5 Дубликаты при ingest не подтверждаются inline

Backend (Wave L1/L2) уже умеет возвращать `dedup_candidate` в payload `ingest job`'а — это видно по [`science_graphrag/ingestion/pipeline.py`](../../science_graphrag/ingestion/pipeline.py) (key-based DOI/arXiv/OpenAlex hit) и `science_graphrag/api/workspace_dedup/` (smart dedup runner). Однако UI-сторона **не показывает confirmation card «эта статья уже есть»** прямо в момент загрузки:

- если key-based hit обнаружен в pipeline — текущий ingest всё равно идёт до конца, создаёт дубль `:Work` в Neo4j, а пользователь должен потом руками открыть `WorkspaceDedupSection` → `Scan for near-duplicates` → ручной merge;
- smart dedup `Scan` запускается ad-hoc и работает на уже залитых документах, не на инжесте.

Желаемое поведение по `_archive/workspace-experience-gap-2026-04-24.md` §1.3 [HISTORICAL]:
**detect → score → user-gated merge** на этапе ingest. Это значит, в `WorkspaceIngestPanel` должна появиться карточка-вопрос:

> **«В этой области уже есть похожая статья.»**
> Слева: новая (название, DOI, arXiv, год). Справа: канонический work из workspace.
> Score: 0.92 (DOI совпал) или 0.78 (vector similarity).
> Действия: `Объединить (рекомендуется)` / `Загрузить как отдельную` / `Отмена`.

Контракт payload расширяется в API — это backend-side в Wave WX3-backend (см. §3.3).

### 1.6 Иконок не хватает; визуальная иерархия слабая

- **Кнопки `Чтение / Граф / Вопросы / Доказательства`** на `WorkPaperCard` — plain text. Уже импортированы MUI-иконки в Drawer (`MenuBookOutlinedIcon`, `AccountTreeOutlinedIcon`, `QuestionAnswerOutlinedIcon`, `FactCheckOutlinedIcon`) — переиспользовать их.
- **Кнопки в `PageHeader`** (`Граф области`, `Суммировать`, `Сгенерировать гипотезы`) — тоже без иконок. Дать `AccountTreeOutlinedIcon`, `AutoStoriesOutlinedIcon`, `LightbulbOutlinedIcon`.
- **`Загрузка статьи`** — добавить `UploadFileOutlinedIcon` к заголовку и `CloudUploadOutlinedIcon` для drag-zone.
- **`Smart dedup`** — `MergeTypeIcon` (или `DifferenceOutlinedIcon`) к заголовку, `BoltOutlinedIcon` к кнопке `Scan`.
- **Stage stepper** — заменить ASCII-символы (`✓`, `●`, `○`, `×`) на `CheckCircleOutlineOutlinedIcon`, `RadioButtonUncheckedOutlinedIcon`, `ErrorOutlineOutlinedIcon`, `RotateRightIcon` (с `keyframes spin` для shimmer).

### 1.7 Hardcoded EN в WorkspaceDedupSection

```93:115:ui/src/pages/WorkspacePage/WorkspaceDedupSection.jsx
      <Typography sx={{ fontSize: "0.8125rem", fontWeight: 600, mb: 1, color: "rgba(129,140,248,0.95)" }}>
        Smart dedup (embeddings + LLM)
      </Typography>
      <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", mb: 1.5 }}>
        Scans work summary vectors in this workspace and opens a review queue. Requires ingested papers (work
        embeddings). Key-only duplicates remain under the classic panel below.
      </Typography>
      <CursorButton variant="outlined" size="small" onClick={() => void onScan()} disabled={scanBusy} sx={{ mb: 1 }}>
        {scanBusy ? "Scanning…" : "Scan for near-duplicates"}
      </CursorButton>
      ...
      <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mb: 2 }}>
        No pending smart-dedup conflicts.
      </Typography>
```

EN-only, нет `useI18n`. Должно жить в `partWorkspacePage.js` обоих локалей.

---

## 2. Целевой UX (что должно быть)

### 2.1 Layout (`WorkspacePage`) на широком экране

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ Drawer (280)  │  ▸ Хедер shell: Workspace switcher (полноценный)            [+ New] │
│               ├──────────────────────────────────────────────────────────────────────┤
│               │  ★ Active workspace HERO (полная ширина, ~90px)                      │
│               │     Иконка корпуса · Название (h1) · 12 статей · 3 автора · …       │
│               │     [Граф] [Сводка] [Гипотезы (admin)]    [⋯ Настройки области]    │
│               ├──────────────────────────────────────┬───────────────────────────────┤
│               │  ▼ Загрузка статей (полная ширина     │  ▶ Боковая колонка:          │
│               │    drop-zone, 2 шт. в ряд на md+)    │     • Smart-dedup queue      │
│               │     ┌──────────┐  ┌──────────┐       │       (badge с числом       │
│               │     │ + Загр.   │  │ Активный  │       │       pending конфликтов)   │
│               │     │ файл      │  │ job:      │       │     • Recent activity        │
│               │     │           │  │ shimmer   │       │       (ingest log compact)   │
│               │     │ drag      │  │ stepper   │       │     • Графовая статистика   │
│               │     └──────────┘  └──────────┘       │     • Связанные области      │
│               ├──────────────────────────────────────┴───────────────────────────────┤
│               │  Статьи в области (12)            [сортировка] [вид: cards|table]   │
│               │  ┌──────────┐  ┌──────────┐  ┌──────────┐                          │
│               │  │  card 1   │  │  card 2   │  │  card 3   │  …  (CSS grid auto-fit)│
│               │  └──────────┘  └──────────┘  └──────────┘                          │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

Главные принципы:

1. **Grid `repeat(auto-fit, minmax(320px, 1fr))` для карточек статей** — не `flex column` с `maxWidth: 720`. На 1920px viewport получим 4 колонки, на 1366px — 3, на планшете — 2, на мобиле — 1.
2. **Двухколонный body** на md+ (`grid-template-columns: minmax(0, 2fr) minmax(280px, 1fr)`): слева ingest + список статей, справа dedup + recent activity + graph stats + cross-links.
3. **Workspace hero** — отдельный 90px-блок над всем контентом с иконкой корпуса (`FolderOpenOutlinedIcon` 32px), названием (h1, 1.25rem), подписью (counts + age), и actions (Граф / Сводка / Гипотезы).
4. **Workspace switcher inline в shell-хедере** (расширить `WorkspaceContextChip` до полноценного `Select` с searchable списком и кнопкой `+ New workspace` рядом). Старый Popover-механизм убрать.

### 2.2 Ingest progress card

```
┌──────────────────────────────────────────────────────────────────────┐
│ ⬆ Загрузка → "Cross-lingual RAG.pdf"  ·  ~1.2 МБ                  │
│ Цель: Research (12 статей)              [↻ Cancel] [⌃ Hide]         │
│ ████████████░░░░░░░░░░░░░░░░░░░░░ 38%                              │
│                                                                      │
│ ✓ Сохранение файла          (2.3 с)                                 │
│ ✓ Извлечение текста         (15.4 с)                                │
│ ⟳ Извлечение метаданных…    [shimmer]                                │
│ ○ Чанки и эмбеддинги                                                 │
│ ○ Запись в граф знаний                                               │
│ ○ Семантический поиск                                                │
│                                                                      │
│ ⓘ ETA ~ 1 мин 20 с             ▸ Подробности (логи)                 │
└──────────────────────────────────────────────────────────────────────┘
```

Контракт UI:

- **header**: иконка `UploadFileOutlinedIcon` + filename + size; справа — `CursorIconButton` Cancel (если backend поддерживает) и Hide;
- **target row**: «Цель: {workspace_name} · {work_count} статей» — отвечает на вопрос пользователя «куда грузится»;
- **общий progress**: `LinearProgress determinate` высотой 6px, цвет `rgba(99,102,241,0.85)`, значение = `weighted average` стадий (вес стадии — `expected_duration_ms` из контракта `IngestJobView.stages[i].expected_duration_ms`, **новое поле backend**);
- **stage list**: каждая строка с MUI-иконкой (см. §1.6), локализованным именем (`t("ingest.stage.vl_extract")`), длительностью (если завершена) или `shimmer` для активной (`@keyframes sciGraphShimmer { 0% { background-position: -200px 0; } 100% { background-position: 200px 0; } }` на полупрозрачном `linear-gradient`);
- **ETA** — простая формула: `sum(remaining_stage_expected_duration_ms) - elapsed_in_current_stage`;
- **Подробности** — accordion свёрнут по умолчанию, внутри — `ingestJob.logs` `<pre>` (для разработчиков и admin-режима).

Backend-сторона: добавить `IngestJobView.stages[i].expected_duration_ms` (среднее по последним 30 успешным jobs из Postgres) и `IngestJobView.progress_pct` (0..1, weighted). Контракт обновляется в [`docs/specs/frontend-ui-api-contracts-v1.md`](../specs/frontend-ui-api-contracts-v1.md).

### 2.3 Ingest-time duplicate confirmation card

```
┌──────────────────────────────────────────────────────────────────────┐
│ ⚠  Возможный дубликат                                                │
│                                                                      │
│ Похоже, в этой области уже есть похожая статья:                     │
│                                                                      │
│ ┌── Новая ──────────────────────┐  ┌── Уже есть ──────────────────┐ │
│ │ XRAG: Cross-lingual…           │  │ XRAG: Cross-lingual…          │ │
│ │ DOI: 10.5555/… · 2024          │  │ DOI: 10.5555/… · 2024         │ │
│ │ arXiv 2404.14219               │  │ arXiv 2404.14219              │ │
│ └────────────────────────────────┘  └───────────────────────────────┘ │
│                                                                      │
│ Совпадение: DOI идентичен (score 1.00)                              │
│                                                                      │
│ [Объединить (рекомендуется)]  [Загрузить как отдельную]  [Отмена]    │
└──────────────────────────────────────────────────────────────────────┘
```

Поток:

1. backend на стадии «extract metadata» делает быстрый key-check (DOI/arXiv/OpenAlex) и vector lookup в Qdrant `work_embeddings` workspace-collection;
2. если есть hit с score ≥ `INGEST_DEDUP_AUTO_THRESHOLD` — pipeline **паузится** в новом стейте `awaiting_user_decision`, payload `IngestJobView.dedup_decision_required` содержит `{ candidate_work_id, score, match_keys, reason }`;
3. UI рисует confirmation card; ответ пользователя летит в `POST /v1/ingest/jobs/{id}/dedup-decision { action: "merge" | "keep_both" | "cancel" }`;
4. pipeline продолжает работу (merge → переиспользует existing work_id; keep_both → создаёт новый; cancel → завершает job со статусом `cancelled`).

Это **новый контракт**: обновляется [`docs/specs/frontend-ui-api-contracts-v1.md`](../specs/frontend-ui-api-contracts-v1.md) и `IngestJobView` в [`science_graphrag/ingestion/pipeline.py`](../../science_graphrag/ingestion/pipeline.py). Backend-сторона = Wave WX3-backend.

### 2.4 Workspace switcher (shell)

Переписать `WorkspaceContextChip` в полноценный `WorkspaceSwitcher`:

- триггер — кнопка вместо `Chip` (h: 36, ширина auto, с иконкой `FolderOpenOutlinedIcon` слева и `ExpandMoreOutlinedIcon` справа);
- внутри popover: searchable список (поле поиска сверху), пункты с цветным «аватаром» (генерация пастельного цвета из id), badge `{count} статей` справа;
- внизу popover: 3 пиктограммы — `+ Новая область`, `Управлять`, `Открыть текущую`;
- если активной нет — кнопка-триггер показывает `Выбрать область` с пунктирной обводкой и pulsing-эффектом для привлечения внимания.

Альтернатива: вынести switcher в саму `WorkspacePage` (workspace hero §2.1), а в shell-хедере оставить лишь breadcrumb-stub `Research › Cross-lingual RAG`. Решение — switcher живёт **обоих местах** (DRY через общий `WorkspaceSwitcher` компонент): и в хедере (повсюду), и в hero на самой `/workspace` (в hero визуально доминирует).

### 2.5 Empty state

Если активной области нет, **на самой** `/workspace` показывать:

```
┌──────────────────────────────────────────────────────────────────────┐
│              ★ Создайте свою первую рабочую область                  │
│                                                                      │
│    Рабочая область — это коллекция статей, в которой вы работаете:  │
│    читаете, спрашиваете, ищете противоречия, строите общий граф.    │
│                                                                      │
│    [+ Новая рабочая область]   [Открыть существующую]               │
│                                                                      │
│    ⓘ Уже есть статьи в каталоге? Их можно привязать к области       │
│      позже на странице «Управление областями».                       │
└──────────────────────────────────────────────────────────────────────┘
```

Поверх — кнопка `+ Новая` сразу создаёт workspace с дефолтным названием `Research N` и редиректит на её URL (без диалога).

---

## 3. План: Wave WX1–WX6

### 3.1 Wave WX1 — Layout + Workspace HERO (frontend-only)

**Цель:** убрать «контент влево, пустота справа»; ввести visible workspace hero; перейти к двухколонной сетке.

**Шаги:**

1. **Удалить `maxWidth: 560/720`** из `WorkspaceIngestPanel.jsx` и `WorkPaperCard.jsx`. Перейти на CSS `grid` в `WorkspacePaperList.jsx`:
   ```js
   sx={{
     display: "grid",
     gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
     gap: 1.5,
   }}
   ```
2. **Двухколонный body в `WorkspacePage.jsx`**: новый компонент `WorkspaceLayout.jsx` с `grid-template-columns: minmax(0, 2fr) minmax(280px, 1fr)` на `md+`, single column на `xs/sm`.
3. **`WorkspaceHero.jsx`** — новый компонент: `FolderOpenOutlinedIcon` 32px, h1 (workspace.name), описание (counts + age), actions (`Граф`, `Сводка`, `Гипотезы`). Заменяет текущий `PageHeader`-блок (PageHeader для других страниц остаётся).
4. **`WorkspaceSidePanel.jsx`** — правая колонка: `WorkspaceDedupSection` (compact-режим), `WorkspaceGraphStats`, `WorkspaceCrossLinks` (заглушка под Wave WX5 follow-up).
5. **Тесты:** добавить smoke `WorkspaceLayout.test.jsx` (рендер с empty/with-data состояниями).

**Файловый скоуп:**
- `ui/src/pages/WorkspacePage/WorkspacePage.jsx` (тонкий shell, ≤ 250 строк после распила — синергия с открытым backlog-пунктом «Slim WorkspacePage.jsx (530)»);
- новые: `ui/src/pages/WorkspacePage/WorkspaceLayout.jsx`, `WorkspaceHero.jsx`, `WorkspaceSidePanel.jsx`;
- правки: `WorkspaceIngestPanel.jsx` (убрать `maxWidth`), `WorkspacePaperList.jsx` (grid), `WorkPaperCard.jsx` (убрать `maxWidth`).

**Acceptance:**
- На 1920×1080 viewport контент `WorkspacePage` занимает ≥ 1280px ширины, карточки в 4 колонки;
- На 1366×768 viewport — 3 колонки, на 768×1024 — 2 колонки, на 375×667 — 1 колонка;
- `WorkspaceHero` всегда видим над контентом, в нём явно виден workspace.name и icon;
- `npm run lint` / `npm run test` зелёные.

**Synergy:**
- Закрывает первый пункт жалобы пользователя («контент ужат влево»).
- Параллельно с открытым backlog-пунктом `H-WorkspacePageSlim` (refactor-frontend) — этот wave **выполняет** распил, можно закрыть пункт `[DONE]`.

### 3.2 Wave WX2 — Ingest progress card redesign (frontend-only)

**Цель:** заменить «Logs»-доминанту на shimmer-stepper с общим прогрессом и ETA; локализовать stage names.

**Шаги:**

1. **Новый компонент `IngestProgressCard.jsx`** в `ui/src/components/ingestion/`:
   - header (filename, size, target workspace);
   - общий `LinearProgress determinate` (значение из `progress_pct`, fallback — равномерный вес по `stages.length`);
   - стадии через `IngestStageRow.jsx` (новый): MUI-иконка по статусу + локализованное имя + длительность/ETA + shimmer-полоса для `running`;
   - ETA-строка (`t("ingest.eta.about", { duration })`);
   - accordion «Подробности» (свёрнут, текст `t("ingest.details.toggle")`, внутри — старый `<pre>` с `ingestJob.logs`).
2. **Локализация stage names** — словари `t("ingest.stage.{stage_name}")` в `partWorkspacePage.js` (EN+RU). Список стадий брать из `science_graphrag/ingestion/pipeline_stages.py` (если такого файла нет — добавить как backend-side helper).
3. **Shimmer-эффект** — CSS `@keyframes` в новом `ui/src/components/ingestion/ingestProgressCard.css.js` (или sx с `keyframes`).
4. **Заменить старый блок `{ingestJob ? (...) : null}`** в `WorkspaceIngestPanel.jsx` на `<IngestProgressCard job={ingestJob} workspaceMeta={…} onCancel={…} onHide={…} />`.
5. **Обновить `IngestStageStepper.test.js`** + добавить `IngestProgressCard.test.jsx` (shimmer на `running`, ETA-расчёт, локализованные имена).

**Файловый скоуп:**
- `ui/src/components/ingestion/IngestProgressCard.jsx` (новый);
- `ui/src/components/ingestion/IngestStageRow.jsx` (новый);
- `ui/src/components/ingestion/IngestStageStepper.jsx` — оставить для backward-compat / batch parent jobs или удалить после миграции;
- `ui/src/i18n/messages/{en,ru}/partWorkspacePage.js` (новые ключи `workspace.upload.target`, `ingest.stage.*`, `ingest.eta.about`, `ingest.details.toggle`);
- `ui/src/pages/WorkspacePage/WorkspaceIngestPanel.jsx` (упрощение, делегирование).

**Backend-сторона (Wave WX2-backend, опциональная):**
- Добавить `IngestJobView.progress_pct: float | None` (weighted average по stages с весами `expected_duration_ms`);
- Добавить `IngestJobView.stages[i].expected_duration_ms: int | None` — статистика по последним 30 успешным jobs из Postgres (новый helper `ingestion/stage_stats.py`);
- Обновить [`docs/specs/frontend-ui-api-contracts-v1.md`](../specs/frontend-ui-api-contracts-v1.md), таблицу полей `IngestJobView`.

**Acceptance:**
- При активном job в UI виден только `IngestProgressCard`; «Logs» свёрнут под `Подробности`;
- Активная стадия имеет shimmer-полоску, завершённые — иконку `✓` (MUI), очередные — `○`;
- ETA-строка появляется при ≥ 1 завершённой стадии с `expected_duration_ms`;
- На ru-локали имена стадий — на русском (`Извлечение текста`, `Чанки и эмбеддинги` и т. д.);
- `npm run lint` / `npm run test` / новый `IngestProgressCard.test.jsx` зелёные.

**Synergy:**
- Закрывает четвёртый пункт жалобы пользователя.
- Не зависит от других wave'ов; полностью frontend на первом этапе. Backend-side `progress_pct` — отдельный backend-PR, можно сделать после wave-FE.

### 3.3 Wave WX3 — Ingest-time duplicate confirmation (backend + frontend)

**Цель:** прямо при загрузке статьи показывать confirmation card «уже есть похожая, объединить?». Ставит в производство то, что Wave L1/L2 backend и Wave I/J UI накопили, но не связали.

**Шаги (backend, отдельный PR):**

1. **`science_graphrag/ingestion/pipeline.py`**: после стадии `extract_metadata` запустить `dedup_check(work_meta, workspace_id)`:
   - key-based: точный DOI/arXiv/OpenAlex match через `Neo4jWorksRepository.find_by_external_id`;
   - vector-based: lookup в Qdrant `work_embeddings` workspace-scoped, threshold `INGEST_DEDUP_VECTOR_THRESHOLD` (default 0.88);
   - если match — pipeline переходит в стейт `awaiting_user_decision`, обновляет job в Postgres.
2. **`science_graphrag/api/ingest_jobs/`**: новый endpoint `POST /v1/ingest/jobs/{id}/dedup-decision`:
   - body: `{ "action": "merge" | "keep_both" | "cancel" }`;
   - merge: переиспользует `candidate_work_id` (запись `BlobStore` остаётся, но `:Work` — существующий), pipeline продолжает с `embed_chunks` для нового `work_revision`;
   - keep_both: pipeline продолжает с обычным `create_work`;
   - cancel: pipeline завершает job со статусом `cancelled`, BlobStore-файл удаляется (`opt-in`).
3. **`IngestJobView`**: новые поля `dedup_decision_required: dict | None` (содержит `candidate_work_id`, `score`, `match_keys: list[str]`, `reason: str`), `dedup_decision: str | None`.
4. Контракт обновляется в [`../specs/frontend-ui-api-contracts-v1.md`](../specs/frontend-ui-api-contracts-v1.md), ADR `0XX-ingest-dedup-decision.md` (нумерация: следующий свободный после `020-langgraph-supervisor-multiagent`).
5. Тесты: `tests/integration/test_ingest_dedup_decision.py` (key match → merge → продолжение pipeline; vector match → keep_both → продолжение).

**Шаги (frontend, отдельный PR после backend merge):**

1. **`ui/src/components/ingestion/IngestDedupCard.jsx`** — новый компонент: 2 колонки (новый work / existing), match score, кнопки `merge | keep_both | cancel`;
2. **`useJobStream`** уже отдаёт `dedup_decision_required` (через payload job-update); в `WorkspaceIngestPanel` показать `IngestDedupCard` поверх `IngestProgressCard` при наличии этого поля;
3. сервис `services/research/ingest.js` (или `researchApi.js`) — функция `postIngestDedupDecision(jobId, action)`;
4. локализация в `partWorkspacePage.js` обоих локалей;
5. e2e: `tests/integration/test_ingest_dedup_card.test.jsx` (mock job stream, action клики).

**Acceptance:**
- При загрузке файла-дубля ingest job встаёт в стейт `awaiting_user_decision`, UI показывает `IngestDedupCard` с правильным score/reason;
- Кнопка `Объединить` → job продолжается с merge, вернувшись в `running`;
- Кнопка `Отмена` → job завершается со статусом `cancelled`, BlobStore сохраняет файл для аудита (если включено `INGEST_DEDUP_PRESERVE_CANCELLED_BLOBS=true`);
- backend: `pytest`/`pylint` зелёные; frontend: `npm run lint` / `npm run test` зелёные.

**Synergy:**
- Закрывает пятый пункт жалобы пользователя.
- Соприкасается с Track A (`Wave W` Dramatiq actor) — оба меняют `pipeline.py`. Делать **после** `Wave W done` (DONE 2026-04-25 ✅).
- Соприкасается с Track D (Wave T entity dedup, Wave L smart dedup) по vector similarity. Wave T переиспользует тот же `vector_dedup_check` helper.

### 3.4 Wave WX4 — Icons + visual hierarchy (frontend-only)

**Цель:** добавить MUI-иконки в action buttons, headers, stage stepper и dedup section; усилить визуальную иерархию.

**Шаги:**

1. **`WorkPaperCard.jsx`**: иконки рядом с label на `Чтение`/`Граф`/`Вопросы`/`Доказательства` (`MenuBookOutlinedIcon`, `AccountTreeOutlinedIcon`, `QuestionAnswerOutlinedIcon`, `FactCheckOutlinedIcon`). `startIcon` prop кастомных `Cursor*` кнопок.
2. **`WorkspaceHero.jsx`** (из WX1): иконки в action-кнопках (`AccountTreeOutlinedIcon` для «Граф области», `AutoStoriesOutlinedIcon` для «Сводка», `LightbulbOutlinedIcon` для «Гипотезы»).
3. **`WorkspaceIngestPanel.jsx`** / `IngestProgressCard.jsx`: `UploadFileOutlinedIcon` к заголовку, `CloudUploadOutlinedIcon` для drop-zone, `FolderOpenOutlinedIcon` для «Несколько файлов», `FolderZipOutlinedIcon` для «.zip».
4. **`IngestStageRow.jsx` (WX2)** — заменить ASCII-символы на MUI-иконки:
   - completed: `CheckCircleOutlineOutlinedIcon` (цвет `rgba(129,140,248,0.95)`);
   - failed: `ErrorOutlineOutlinedIcon` (`rgba(239,68,68,0.9)`);
   - running: `RotateRightIcon` с `keyframes spin` (`rgba(255,255,255,0.9)`);
   - pending: `RadioButtonUncheckedOutlinedIcon` (`rgba(255,255,255,0.5)`).
5. **`WorkspaceDedupSection.jsx`**: `MergeTypeIcon` к заголовку, `BoltOutlinedIcon` к кнопке `Scan`, `RuleFolderOutlinedIcon` к каждому conflict-row.
6. **Cursor button family** — добавить поддержку `startIcon`/`endIcon` если её нет. Проверить `ui/src/components/common/CursorButton.jsx` и сопутствующие; если иконки уже работают через MUI Button base — изменения не нужны.

**Файловый скоуп:**
- `ui/src/pages/WorkspacePage/WorkPaperCard.jsx`
- `ui/src/pages/WorkspacePage/WorkspaceHero.jsx` (новый из WX1)
- `ui/src/pages/WorkspacePage/WorkspaceIngestPanel.jsx`
- `ui/src/components/ingestion/IngestProgressCard.jsx` / `IngestStageRow.jsx` (новые из WX2)
- `ui/src/pages/WorkspacePage/WorkspaceDedupSection.jsx`
- `ui/src/components/common/Cursor*.jsx` (опционально — поддержка `startIcon`)

**Acceptance:**
- Все action-кнопки на `WorkspacePage` имеют осмысленную иконку слева;
- Stage stepper использует MUI-иконки, активная стадия вращается (`RotateRightIcon` + `keyframes spin`);
- `npm run lint` зелёный (никаких unused imports после правок).

**Synergy:**
- Закрывает шестой пункт жалобы.
- Зависит от WX1 (нужен `WorkspaceHero`) и WX2 (нужен `IngestStageRow`). Делать после них в одном спринте.

### 3.5 Wave WX5 — Workspace switcher + create CTA (frontend-only)

**Цель:** сделать «активный workspace» и «создать новый» очевидными в любой точке UI.

**Шаги:**

1. **`WorkspaceSwitcher.jsx`** (новый, в `ui/src/components/layout/`) — расширенный аналог `WorkspaceContextChip`:
   - триггер: `Button` высотой 36px, иконка `FolderOpenOutlinedIcon` слева, `ExpandMoreOutlinedIcon` справа, label = workspace.name;
   - popover: search-поле сверху, список workspaces с цветным «аватаром» (генерация пастельного цвета из id), badge `{count}` справа;
   - footer: 3 пиктограммы — `+ Новая`, `⚙ Управлять`, `↗ Открыть текущую`;
   - empty state триггера: `Выбрать область` с пунктирной обводкой и subtle pulse animation для привлечения внимания.
2. **Заменить `WorkspaceContextChip` на `WorkspaceSwitcher`** в `DashboardLayout.jsx` хедере.
3. **Использовать `WorkspaceSwitcher` внутри `WorkspaceHero`** (workspace name → раскрывает switcher; чтобы переключиться, не уходя со страницы).
4. **`workspace empty state`** в `WorkspacePage.jsx`: вместо `<Alert>` + ссылка `/workspaces` — большой блок с CTA `+ Новая рабочая область` (создаёт `Workspace N` через `createWorkspace`, редиректит на новый URL) и secondary `Открыть существующую` (открывает `WorkspaceSwitcher` popover).
5. **Drawer `+`-кнопка** (опционально): рядом с пунктом `Workspace` в Drawer добавить иконочную кнопку `AddOutlinedIcon` (висящая справа или появляющаяся при hover в expanded режиме), которая открывает switcher.

**Файловый скоуп:**
- `ui/src/components/layout/WorkspaceSwitcher.jsx` (новый);
- `ui/src/components/layout/DashboardLayout/DashboardLayout.jsx` (замена импорта);
- `ui/src/components/layout/WorkspaceContextChip.jsx` — удалить (или оставить как deprecated alias);
- `ui/src/pages/WorkspacePage/WorkspaceHero.jsx` (использует switcher);
- `ui/src/pages/WorkspacePage/WorkspacePage.jsx` (новый empty state).

**Acceptance:**
- На `/workspace` без активной области виден большой блок CTA «+ Новая»; клик создаёт workspace и редиректит;
- На `/workspace` с активной областью имя кликабельно, открывает popover со списком и `+ Новая`;
- На любой другой странице (`/graph`, `/ask`, `/evidence`) тот же switcher в shell-хедере;
- `npm run lint` / `npm run test` зелёные.

**Synergy:**
- Закрывает второй и третий пункты жалобы пользователя.
- WX5 зависит от WX1 (workspace hero). Делать после WX1.

### 3.6 Wave WX6 — i18n + cleanup smart dedup section (frontend-only)

**Цель:** убрать EN-only хардкод; согласовать `WorkspaceDedupSection` с дизайн-каноном; сделать smart-dedup compact.

**Шаги:**

1. **i18n ключи** в `partWorkspacePage.js` (EN+RU): `dedup.smart.title`, `dedup.smart.desc`, `dedup.smart.scan`, `dedup.smart.scanning`, `dedup.smart.empty`, `dedup.smart.pending`, `dedup.smart.review`, `dedup.smart.scanDone`, `dedup.smart.scanFailed`.
2. **`WorkspaceDedupSection.jsx`**: заменить хардкод на `t(...)`; убрать дублирующее `useI18n` если уже есть.
3. **`Cursor*` кнопки** в этом компоненте + в `WorkDedupReviewDialog.jsx` (закрывает open backlog-пункт `H-Cursor*-buttons in dedup dialogs`).
4. **Compact-режим** для side panel: при monтировании в `WorkspaceSidePanel` (WX1) рисовать только compact-card с числом pending конфликтов и кнопкой `Открыть очередь`, full-list — в отдельном диалоге `<DedupQueueDialog>`. На основной surface страницы `WorkspaceDedupSection` остаётся (для backward-compat при отсутствии side panel).
5. **`WorkDedupReviewDialog`**: проверить наличие иконок/изображений к карточкам сравнения (вписать `MergeTypeIcon`/`DifferenceOutlinedIcon` в title; цвета score `rgba(99,102,241,…)` для high, `rgba(255,193,7,…)` для medium, `rgba(239,68,68,…)` для low).

**Файловый скоуп:**
- `ui/src/i18n/messages/{en,ru}/partWorkspacePage.js`;
- `ui/src/pages/WorkspacePage/WorkspaceDedupSection.jsx`;
- `ui/src/components/graph/dedup/WorkDedupReviewDialog.jsx` (или `ui/src/components/graph/WorkDedupReviewDialog.jsx`);
- новый `ui/src/components/dedup/DedupQueueDialog.jsx` (для compact-режима).

**Acceptance:**
- Ни одного EN-литерала в `WorkspaceDedupSection.jsx` / `WorkDedupReviewDialog.jsx`;
- Smart dedup section согласован с дизайн-каноном (Cursor* кнопки, цвета score, иконки);
- В side panel (после WX1) видна compact-карточка `Smart dedup ▸ {N} конфликтов`;
- `npm run lint` / `npm run test` зелёные.

**Synergy:**
- Закрывает седьмой пункт жалобы пользователя.
- Закрывает 2 открытых backlog-пункта в `refactor-frontend.md` (`H-i18n-fixes` частично, `H-Cursor*-buttons in dedup`).

---

## 4. Контракт (что меняется в API/payload)

| Поле | Где | Wave | Тип | Описание |
|------|-----|------|-----|----------|
| `IngestJobView.progress_pct` | `science_graphrag/ingestion/pipeline.py` (Pydantic), `/v1/ingest/jobs/{id}` | WX2-backend | `float \| None` (0..1) | Weighted progress по `expected_duration_ms` стадий |
| `IngestJobView.stages[i].expected_duration_ms` | там же | WX2-backend | `int \| None` (ms) | Среднее по последним 30 успешным jobs данной стадии |
| `IngestJobView.dedup_decision_required` | там же | WX3-backend | `dict \| None` | `{ candidate_work_id: str, score: float, match_keys: list[str], reason: str }` |
| `IngestJobView.dedup_decision` | там же | WX3-backend | `str \| None` | `"merge" \| "keep_both" \| "cancel" \| None` (история ответа) |
| `POST /v1/ingest/jobs/{id}/dedup-decision` | `api/ingest_jobs/router.py` | WX3-backend | endpoint | Приём решения пользователя, продолжает pipeline |

Контракт обновляется в [`../specs/frontend-ui-api-contracts-v1.md`](../specs/frontend-ui-api-contracts-v1.md) и [`../architecture/observability-phoenix.md`](../architecture/observability-phoenix.md) (новые spans `ingest.dedup.check`, `ingest.dedup.decision_wait`).

---

## 5. Параллельность и связь с Track F

| Wave | Тип | Файловый скоуп | Параллельно с | Конфликт с |
|------|-----|----------------|---------------|------------|
| **WX1** | FE | `ui/src/pages/WorkspacePage/*`, `WorkspaceLayout.jsx`, `WorkspaceHero.jsx`, `WorkspaceSidePanel.jsx` | WX2-FE, GR6/GR7 (граф), любые backend-волны | `H-WorkspacePageSlim` (WX1 **выполняет** этот рефактор) |
| **WX2-FE** | FE | `ui/src/components/ingestion/*`, `WorkspaceIngestPanel.jsx`, i18n | WX1, WX3-BE, GR* | — |
| **WX2-BE** | BE | `science_graphrag/ingestion/pipeline.py`, `pipeline_stages.py`, `api/ingest_jobs/router.py` | WX1, WX3-BE, Track B/C/D без затронутых файлов | Track A `Wave W` (DONE) |
| **WX3-BE** | BE | `science_graphrag/ingestion/pipeline.py`, `api/ingest_jobs/`, новый ADR | Track D Wave T (общий vector helper) | WX2-BE (общий `pipeline.py`) |
| **WX3-FE** | FE | `ui/src/components/ingestion/IngestDedupCard.jsx`, `useJobStream.js`, `services/research/ingest.js` | WX1, WX2, GR* | WX2-FE (общий `WorkspaceIngestPanel.jsx`) |
| **WX4** | FE | разные файлы (icons вставка) | WX5, WX6 | WX1, WX2 (зависит от их компонентов) |
| **WX5** | FE | `WorkspaceSwitcher.jsx`, `DashboardLayout.jsx`, `WorkspaceHero.jsx` | WX4, WX6 | WX1 (общий `WorkspaceHero`) |
| **WX6** | FE | `WorkspaceDedupSection.jsx`, i18n, `WorkDedupReviewDialog.jsx`, `DedupQueueDialog.jsx` | WX4, WX5 | WX1 (компонент попадает в side panel) |

**Рекомендованный порядок (1 спринт):**
WX1 → (WX2-FE ‖ WX2-BE) → WX4 → WX5 → WX6 → (WX3-BE → WX3-FE).

**Безопасный шаблон одного раунда (4 агента):**
- Agent 1: WX1 (layout + hero + side panel skeleton);
- Agent 2: WX2-FE (IngestProgressCard + i18n stage names) **после** WX1 merge;
- Agent 3: WX2-BE (`progress_pct` + `expected_duration_ms`) — независимо;
- Agent 4: WX5 (workspace switcher + create CTA) **после** WX1 merge.

Затем отдельным следующим раундом:
- Agent 1: WX4 (icons sweep);
- Agent 2: WX6 (i18n + cleanup smart dedup);
- Agent 3: WX3-BE;
- Agent 4: WX3-FE (после WX3-BE merge).

---

## 6. Backlog-пункты для `refactor-frontend.md`

Добавляются 6 пунктов (по одному на wave) в формате:

```markdown
### [OPEN] Workspace UX — Wave WX1 layout & hero
- **Area:** `ui/src/pages/WorkspacePage/*`
- **Issue:** контент ужат влево (`maxWidth: 560/720`), активный workspace неявен
- **Proposal:** см. `docs/analysis/workspace-ux-redesign-2026-04-25.md` §3.1
- **Acceptance:** на 1920px viewport карточки в 4 колонки, `WorkspaceHero` всегда виден
- **Raised:** 2026-04-25
```

Аналогично для WX2/WX3-BE/WX3-FE/WX4/WX5/WX6 (см. §3.2–3.6).

Закрываемые пункты (с `[DONE]` после соответствующего PR):
- `[OPEN] Slim WorkspacePage.jsx (530)` — закроется WX1;
- `[OPEN] Switch dedup dialogs to Cursor* button family` — закроется WX6;
- `[OPEN] i18n hardcoded copy: HypothesisPanel, IngestionSettings, Workspace dialogs` — частично закроется WX6 (часть про `WorkspaceDedupSection`).

---

## 7. Привязка к [`master-roadmap-and-refactor-plan-2026-04-25.md`](master-roadmap-and-refactor-plan-2026-04-25.md)

### 7.1 Track F — Workspace experience: расширение

В §4.6 Track F (текущий статус «Wave I/J/K/L done, gated stub») добавляются новые волны **WX1–WX6**:

```
Wave I/J/K/L (done) ── Wave WX1 (layout + hero) ── Wave WX2 (ingest progress)
                              │                          │
                              │                          ├── Wave WX2-BE (progress_pct, expected_duration_ms)
                              │                          │
                              │                          └── Wave WX4 (icons sweep) ── Wave WX5 (switcher + CTA)
                              │                                                               │
                              │                                                               └── Wave WX6 (i18n + dedup compact)
                              │
                              └── Wave WX3-BE (dedup decision API) ── Wave WX3-FE (IngestDedupCard)
```

### 7.2 Новый раунд агентов

Добавляется **Раунд 8 (Workspace UX redesign: WX1 + WX2-FE + WX2-BE + WX5)** — параллельный шаблон для §7 «Запуск Cursor-агентов параллельно». Файловые скоупы не пересекаются с активными раундами 6/7 (Benchmark Trust BT1–BT12) и не пересекаются с GR6/GR7 (граф).

### 7.3 §10 Ссылки

В блоке «Активные роадмапы» добавляется строка:

```
- `docs/analysis/workspace-ux-redesign-2026-04-25.md` — Workspace UX redesign и план Wave WX1–WX6
```

---

## 8. Открытые вопросы / риски

1. **`progress_pct` для batch parent jobs.** Текущий `IngestJobView.kind == "batch_parent"` имеет `child_jobs[]`. WX2-BE должен агрегировать `progress_pct` как weighted avg по children, с весом = `progress_total` ребёнка. Зафиксировать в spec.
2. **Cancel pipeline.** `WX2-FE` имеет кнопку `Cancel`, но backend сейчас не умеет аккуратно отменить running pipeline. Wave A `Wave W` (Dramatiq actor) даёт hook для cancel через message broker. WX2-FE кнопку добавить с `disabled={true}` и tooltip «in progress», полное включение — отдельным backend-PR (X1.5? — обсудить).
3. **`INGEST_DEDUP_AUTO_THRESHOLD`** для key-based vs vector-based. Дефолты: key=1.00 (точное совпадение DOI/arXiv/OpenAlex), vector=0.88 (по экспериментам Wave T). Конфигурируемо через [`Settings`](../../science_graphrag/config.py).
4. **Workspace switcher шорткат.** Cmd+K (или Ctrl+K) — открывать switcher. Отдельный PR (Wave WX5.1?) после base WX5.
5. **Side panel collapse.** `WorkspaceSidePanel` должен сворачиваться (как Drawer) — иначе на 1366px viewport занимает 280px, что съедает основной контент. Решение: collapsed по умолчанию на `< 1280px`, expanded на `≥ 1280px`. Зафиксировать в WX1 spec.
6. **Onboarding для empty state.** Большой CTA «Создайте первую область» (см. §2.5) появляется только если у пользователя **нет ни одной** области. Если есть, но не выбрана — другой текст «У вас уже есть {N} областей. Откройте одну из списка или создайте новую». Учесть оба state'а в WX5.

---

## 9. Definition of Done (общий)

- Все wave-пункты Wave WX1–WX6 закрыты `[DONE]` в `refactor-frontend.md`;
- На 1920×1080 viewport `/workspace` использует ≥ 1280px ширины (4 колонки карточек);
- При загрузке файла видны: target workspace name, общий progress %, локализованные имена стадий, shimmer на активной стадии, ETA;
- При загрузке дубликата (DOI/arXiv hit или vector ≥ 0.88) видна `IngestDedupCard` с действиями `Объединить / Загрузить как отдельную / Отмена`;
- Workspace switcher доступен в shell-хедере и в `WorkspaceHero`; кнопка `+ Новая` создаёт workspace без перехода на `/workspaces`;
- Все action-кнопки на `WorkspacePage` имеют MUI-иконки;
- `WorkspaceDedupSection` локализован EN+RU; `WorkDedupReviewDialog` использует `Cursor*` кнопки;
- `npm run lint` / `npm run test` / `pytest` / `pylint` зелёные;
- [`../specs/frontend-ui-api-contracts-v1.md`](../specs/frontend-ui-api-contracts-v1.md) обновлён по WX2-BE и WX3-BE.

