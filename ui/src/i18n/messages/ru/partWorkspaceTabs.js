/** @type {Record<string, string>} */
export default {
  "wsTab.overview.pickWork": "Выберите статью из корпуса для обзора.",
  "wsTab.overview.loading": "Загрузка работы…",
  "wsTab.overview.noTitle": "(без названия)",
  "wsTab.overview.quickActions": "Быстрые действия",
  "wsTab.overview.readerTab": "Вкладка «Чтение»",
  "wsTab.overview.graphTab": "Вкладка «Граф»",
  "wsTab.overview.askTab": "Вкладка «Вопросы»",
  "wsTab.overview.evidenceTab": "Вкладка «Доказательства»",
  "wsTab.overview.openGraphFull": "Граф на отдельной странице",
  "wsTab.overview.graphNote":
    "Граф доступен внутри рабочей области и дублируется отдельным маршрутом для углублённого просмотра.",
  "wsTab.overview.ingestionLine":
    "document_id: {{docId}} · has_chunks: {{hasChunks}} · semantic: {{semantic}}",

  "wsTab.reader.pickWork": "Выберите статью из корпуса для чтения.",
  "wsTab.reader.liveLine": "Живые данные: GET /v1/works/{work_id} + /chunks.",
  "wsTab.reader.openStandalone": "Чтение отдельно",
  "wsTab.reader.jumpGraph": "К графу",
  "wsTab.reader.claimsTitle": "Утверждения (Claims, эксперимент)",
  "wsTab.reader.claimsLoading": "Загрузка claims…",
  "wsTab.reader.claimsEmpty": "Для этой работы пока нет извлечённых claims.",
  "wsTab.reader.claimConfidence": "уверенность: {{v}}",

  "wsTab.graph.pickWork": "Выберите статью из корпуса для контекста графа.",
  "wsTab.graph.openStandalone": "Граф отдельно",
  "wsTab.graph.jumpReader": "К чтению",
  "wsTab.graph.jumpEvidence": "К доказательствам",
  "wsTab.graph.jumpAsk": "К вопросам",
  "wsTab.graph.subtitle":
    "Граф привязан к активной работе; фокус узла в URL для глубоких ссылок.",

  "wsTab.ask.pickWork": "Выберите статью из корпуса, чтобы привязать вопросы к ней.",
  "wsTab.ask.researchContext": "Контекст работы со статьёй",
  "wsTab.ask.contextLine": "Продолжить текущий сценарий вопросов из {{summary}}.",

  "wsTab.evidence.pickWork": "Выберите статью из корпуса для отпечатков чанков.",
  "wsTab.evidence.liveLine":
    "Живые отпечатки чанков (GET /v1/works/{work_id}/chunks). Сверяйте с цитатами в «Вопросах».",
  "wsTab.evidence.jumpReader": "К чтению",
  "wsTab.evidence.jumpGraph": "К графу",
  "wsTab.evidence.openStandalone": "Доказательства отдельно",
};
