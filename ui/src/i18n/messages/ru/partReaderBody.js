/** @type {Record<string, string>} */
export default {
  "readerBody.loading": "Загрузка…",
  "readerBody.noTitle": "(без названия)",
  "readerBody.extractedTitle": "Извлечённый текст (чтение)",
  "readerBody.extractedHint":
    "Склеенные чанки по порядку документа (заголовки из section_path). Отпечатки чанков — в «Дополнительно» ниже.",
  "readerBody.chunksPartial": "Показаны первые {{shown}} из {{total}} чанков — при необходимости увеличьте лимит в UI.",
  "readerBody.focusedContext": "Контекст чтения",
  "readerBody.openedFrom": "Открыто из {{summary}}",
  "readerBody.returnAsk": "Вернуться ко «Вопросам»",
  "readerBody.openEvidence": "Открыть доказательства",
  "readerBody.chunksAdvanced": "Чанки (дополнительно) — {{count}}",
  "readerBody.chunksTraceHint": "Источники чанков для трассировки ответов агента (отпечатки и превью).",
  "readerBody.hide": "Скрыть",
  "readerBody.show": "Показать",
  "readerBody.ingestionLine":
    "document_id: {{docId}} · has_chunks: {{hasChunks}} · semantic: {{semantic}}",
  "readerBody.chunkMeta": "{{section}} · fp {{fp}}",
  "readerBody.focusedChip": "в фокусе",
  "readerBody.viewMarkdown": "Markdown",
  "readerBody.viewPdf": "PDF",
  "readerBody.pdfUnavailable":
    "Исходный PDF недоступен для этой работы (например, загрузка только в формате Markdown).",
  "readerBody.pdfLoadError": "Не удалось загрузить PDF: {{message}}",
  "readerBody.pdfLoading": "Загрузка PDF…",
  "readerBody.pdfPrev": "Предыдущая страница",
  "readerBody.pdfNext": "Следующая страница",
  "readerBody.pdfPageOf": "Страница {{page}} / {{total}}",
  "readerBody.pdfZoomIn": "Крупнее",
  "readerBody.pdfZoomOut": "Мельче",
  "readerBody.emptyMarkdownTryPdf":
    "В этом превью нет текста чанков — переключитесь на PDF для оригинальных страниц.",
  "readerBody.openPdf": "Открыть PDF",
  "readerBody.noExtractedTextOrPdf":
    "Нет извлечённого текста чанков и нет исходного PDF (например, только Markdown при загрузке).",
  "readerBody.showAbstract": "Аннотация",
  "readerBody.hideAbstract": "Скрыть аннотацию",
  "readerBody.claimsTitle": "Утверждения (claims)",
  "readerBody.claimsHint":
    "Извлечённые утверждения с цитатой-доказательством (загрузка по раскрытию). Включите VITE_CLAIMS_ENABLED=true.",
  "readerBody.claimsLoading": "Загрузка claims…",
  "readerBody.claimsEmpty":
    "Для этой работы пока нет claims (переингест с SCIENCE_GRAPHRAG_CLAIMS_EXTRACTION_ENABLED=true).",
  "readerBody.claimsEvidence": "Доказательства",
  "readerBody.claimFilterAllTypes": "Все типы",
  "readerBody.claimFilterAllPolarities": "Все полярности",
  "readerBody.claimsNoFilterMatch": "Нет claims под выбранные фильтры.",
};
