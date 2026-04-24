/** @type {Record<string, string>} */
export default {
  "wsTab.overview.pickWork": "Выберите работу из Corpus для обзора.",
  "wsTab.overview.loading": "Загрузка работы…",
  "wsTab.overview.noTitle": "(без названия)",
  "wsTab.overview.quickActions": "Быстрые действия",
  "wsTab.overview.readerTab": "Вкладка Reader",
  "wsTab.overview.graphTab": "Вкладка Graph",
  "wsTab.overview.askTab": "Вкладка Ask",
  "wsTab.overview.evidenceTab": "Вкладка Evidence",
  "wsTab.overview.openGraphFull": "Граф на отдельной странице",
  "wsTab.overview.graphNote":
    "Граф доступен внутри workspace и остаётся отдельным маршрутом для углублённого просмотра.",
  "wsTab.overview.ingestionLine":
    "document_id: {{docId}} · has_chunks: {{hasChunks}} · semantic: {{semantic}}",

  "wsTab.reader.pickWork": "Выберите работу из Corpus для reader.",
  "wsTab.reader.liveLine": "Живые данные: GET /v1/works/{work_id} + /chunks.",
  "wsTab.reader.openStandalone": "Reader отдельно",
  "wsTab.reader.jumpGraph": "К Graph",

  "wsTab.graph.pickWork": "Выберите работу из Corpus для контекста графа.",
  "wsTab.graph.openStandalone": "Graph отдельно",
  "wsTab.graph.jumpReader": "К Reader",
  "wsTab.graph.jumpEvidence": "К Evidence",
  "wsTab.graph.jumpAsk": "К Ask",
  "wsTab.graph.subtitle":
    "Граф привязан к активной работе; фокус узла в URL для глубоких ссылок.",

  "wsTab.ask.pickWork": "Выберите работу из Corpus, чтобы привязать вопросы к ней.",
  "wsTab.ask.researchContext": "Контекст исследования",
  "wsTab.ask.contextLine": "Продолжить текущий сценарий вопросов из {{summary}}.",

  "wsTab.evidence.pickWork": "Выберите работу из Corpus для отпечатков чанков.",
  "wsTab.evidence.liveLine":
    "Живые отпечатки чанков (GET /v1/works/{work_id}/chunks). Сверяйте с цитатами Ask.",
  "wsTab.evidence.jumpReader": "К Reader",
  "wsTab.evidence.jumpGraph": "К Graph",
  "wsTab.evidence.openStandalone": "Evidence отдельно",
};
