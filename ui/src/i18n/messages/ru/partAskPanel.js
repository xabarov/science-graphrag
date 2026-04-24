/** @type {Record<string, string>} */
export default {
  "askPanel.chromeTitle": "Ask",
  "askPanel.chromeBody":
    "POST /v1/query (живой запрос). Укажите VITE_API_BASE_URL, если API не same-origin.",
  "askPanel.chrome.p1": "POST /v1/query (живой запрос). Укажите ",
  "askPanel.chrome.p2": ", если API не same-origin.",
  "askPanel.banner.workspaceScoped": "Исследование в рамках workspace",
  "askPanel.banner.standalone": "Автономный режим",
  "askPanel.banner.descWorkspace":
    "Вопрос привязан к активной статье. По цитатам ниже — в evidence, reader и graph без потери `work_id`.",
  "askPanel.banner.descStandalone":
    "Вопрос по корпусу или к одной статье. Действия ответа ведут в evidence, reader или graph для углублённого просмотра.",
  "askPanel.banner.workspaceCorpusTitle": "Область: корпус workspace",
  "askPanel.banner.descWorkspaceCorpus":
    "Ответы ограничены статьями активного workspace (без одного work_id). Укажите work_id ниже, чтобы сузить область.",
  "askPanel.optionalContext.title": "Необязательный контекст статьи",
  "askPanel.session.title": "Сессия Ask",
  "askPanel.session.hintStandalone":
    "Хранится локально в браузере. В каждой сессии до 24 ходов.",
  "askPanel.session.hintWorkspace": "Отдельно для вкладки workspace. Переключайте сессии для разных веток.",
  "askPanel.session.serverSyncLine": "Синхронизация с сервером: /v1/ask-sessions (файлы на хосте API).",
  "askPanel.session.urlLine":
    "Активная сессия отражается в URL как ask_session (только локально; делитесь только по доверенным каналам).",
  "askPanel.serverSyncLabel": "Синхронизация сессий с сервером (пилот)",
  "askPanel.session.selectLabel": "Сессия",
  "askPanel.sessionTitle": "Название сессии",
  "askPanel.newSession": "Новая сессия",
  "askPanel.recent.standalone": "Недавние в этой сессии",
  "askPanel.recent.workspace": "Недавние в сессии workspace",
  "askPanel.recent.globalLine": "весь корпус · ",
  "askPanel.recent.topK": "top_k {{k}} · цитат: {{count}}",
  "askPanel.restore": "Восстановить",
  "askPanel.noTurns.title": "Пока нет ходов",
  "askPanel.noTurns.body":
    "Запустите запрос. Включите синхронизацию с сервером, чтобы хост API сохранял ходы для этой области.",
  "askPanel.workIdScopeLabel": "work_id (область workspace)",
  "askPanel.query": "Запрос",
  "askPanel.workIdAutocomplete": "work_id (необязательно, из корпуса)",
  "askPanel.topK": "top_k",
  "askPanel.runQueryLoading": "Запрос…",
  "askPanel.runQuery": "Выполнить запрос",
  "askPanel.openStandaloneAsk": "Открыть автономный Ask",
  "askPanel.answer.title": "Ответ",
  "askPanel.answer.why": "Почему такой ответ",
  "askPanel.answer.degraded":
    "Часть контекста была упрощена при retrieval. Изучите трассу ниже, прежде чем считать ответ окончательным.",
  "askPanel.citations.title": "Цитаты",
  "askPanel.citations.none": "Для этого ответа цитаты не вернулись.",
  "askPanel.citation.line": "Цитата #{{rank}} · score {{score}} · {{work}}",
  "askPanel.citation.noWork": "нет контекста статьи",
  "askPanel.chunkLabel": "чанк",
  "askPanel.openReader": "Открыть Reader",
  "askPanel.openEvidence": "Открыть Evidence",
  "askPanel.openGraph": "Открыть Graph",
  "askPanel.openInWorkspace": "Открыть в Workspace",
  "askPanel.standaloneReader": "Reader отдельно",
  "askPanel.standaloneEvidence": "Evidence отдельно",
  "askPanel.standaloneGraph": "Graph отдельно",
  "askPanel.graphContext.title": "Контекст графа",
  "askPanel.graphContext.body":
    "semantic_available={{semantic}} · context_work_id={{ctx}}{{err}}",
  "askPanel.retrieval.title": "Трассировка retrieval",
  "askPanel.retrieval.summary":
    "Кратко, как собирались доказательства. Разверните JSON для полей embedding и низкоуровневых деталей.",
  "askPanel.toggleJson.hide": "Скрыть расширенный JSON",
  "askPanel.toggleJson.show": "Показать расширенный JSON",
  "askPanel.flag.graphDegraded": "graph_context.degraded",
};
