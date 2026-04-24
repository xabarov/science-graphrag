/** @type {Record<string, string>} */
export default {
  "glossary.workspace.p1": "Откройте работу и переключайте вкладки, не теряя контекст.",
  "glossary.workspace.p2": "— это id проиндексированной статьи;",
  "glossary.workspace.p3": "связывает Reader, Graph, Ask и Evidence с этой статьёй.",
  "glossary.workspace.session": "сессия рабочей области",

  "glossary.corpus.p1": "Просмотр проиндексированных работ",
  "glossary.corpus.p2":
    "Каждая строка — work_id в корпусе; откройте работу в Workspace для полной сессии (reader, ask, evidence, graph).",

  "glossary.ask.p1":
    "ограничивает вопрос одной статьёй, если выбрать её из корпуса или вставить id. Оставьте пустым для поиска по всему корпусу.",

  "glossary.graph.p1": "Граф загружен для активного",
  "glossary.graph.p2": "Выбор узла синхронизируется с URL для deep links и трассируемости.",

  "home.header.eyebrow": "Исследовательская зона",
  "home.header.title": "Главная",
  "home.header.description":
    "Откройте рабочую область, перейдите в Workspaces, чтобы добавить статьи, или в админ-инструменты — без потери основного потока.",
  "home.header.workspaces": "Рабочие области",
  "home.header.admin": "Админ",

  "home.card.workspace.eyebrow": "Исследовательская зона",
  "home.card.workspace.titleOpenLast": "Открыть последнюю статью",
  "home.card.workspace.titleDefault": "Открыть Workspace",
  "home.card.workspace.descOpenLast":
    "Продолжить последнюю открытую статью в оболочке Workspace (список статей + инструменты слева).",
  "home.card.workspace.descDefault": "Создайте или выберите workspace в Workspaces, затем добавьте статьи по work_id.",
  "home.card.workspace.openWorkspace": "Открыть Workspace",
  "home.card.workspace.lastPaper": "Последняя статья",
  "home.card.workspace.browse": "Список Workspaces",

  "home.card.collections.eyebrow": "Коллекции",
  "home.card.collections.title": "Workspaces и индекс",
  "home.card.collections.description":
    "Управление workspace (наборы статей), слияние, экспорт JSON и поиск по индексу для добавления статей.",
  "home.card.collections.workspaces": "Workspaces",
  "home.card.collections.reader": "Reader",

  "home.card.admin.eyebrow": "Операционная зона",
  "home.card.admin.title": "Админ-инструменты",
  "home.card.admin.description":
    "Бенчмарки, настройки и диагностика доступны из отдельного входа и не перегружают основной UX.",
  "home.card.admin.openAdmin": "Открыть админ",
  "home.card.admin.benchmarks": "Бенчмарки",

  "home.recentWorks.title": "Недавние работы",
  "home.recentWorks.empty": "Пока нет недавних. Откройте Workspaces и добавьте статью.",
  "home.recentWorks.open": "Открыть",

  "home.session.title": "Готовность сессии",
  "home.session.lastContext": "Последний контекст workspace:",
  "home.session.recentHistory": "История недавних работ:",
  "home.session.continueFlow": "Продолжение:",
  "home.session.savedLocally": "сохранён локально",
  "home.session.notSaved": "ещё не сохранён",
  "home.session.available": "есть",
  "home.session.empty": "пусто",
  "home.session.readyResume": "можно продолжить",
  "home.session.startsWorkspaces": "начните с Workspaces",

  "notFound.header.eyebrow": "Восстановление",
  "notFound.header.title": "Страница не найдена",
  "notFound.header.description":
    "Маршрут не существует или недоступен. Выберите безопасный следующий шаг к исследованию или админ-зоне.",
  "notFound.actions.title": "Рекомендуемые действия",
  "notFound.actions.body":
    "Вернитесь на главные экраны, откройте Workspaces или продолжите последний сохранённый workspace.",
  "notFound.actions.goHome": "На главную",
  "notFound.actions.workspaces": "Workspaces",
  "notFound.actions.continueWorkspace": "Продолжить workspace",
  "notFound.actions.openAdmin": "Открыть админ",

  "adminGate.title": "Админ-зона недоступна",
  "adminGate.body":
    "Окружение в режиме только исследования. Вернитесь в Workspaces или продолжите workspace без операционных инструментов.",
  "adminGate.goHome": "На главную",
  "adminGate.workspaces": "Workspaces",
  "adminGate.workspace": "Workspace",

  "adminEntry.apiStatus": "Статус API",
  "adminEntry.card.benchmarks.title": "Бенчмарки",
  "adminEntry.card.benchmarks.description":
    "Запуск бенчмарков, workbench, сравнение прогонов и разбор кейсов.",
  "adminEntry.card.benchmarks.primary": "Открыть бенчмарки",
  "adminEntry.card.benchmarks.secondary": "Открыть workbench",
  "adminEntry.card.settings.title": "Настройки",
  "adminEntry.card.settings.description": "Runtime и LLM в отдельном layout настроек.",
  "adminEntry.card.settings.primary": "Открыть настройки",
  "adminEntry.card.diagnostics.title": "Диагностика",
  "adminEntry.card.diagnostics.description": "Проверки здоровья и каталога + JSON. Метрики — в следующих версиях.",
  "adminEntry.card.diagnostics.primary": "Открыть диагностику",

  "adminApi.loading": "Загрузка статуса API…",
  "adminApi.health": "GET /health",
  "adminApi.works": "GET /v1/works",
  "adminApi.unreachable": "недоступно",
  "adminApi.catalogTotal": "всего в каталоге {{total}}",
  "adminApi.reachable": "доступно",

  "diagnostics.title": "Диагностика",
  "diagnostics.intro":
    "Проверки к настроенному API: GET /health и минимальный GET /v1/works?limit=1. Глубокие метрики — позже.",
  "diagnostics.apiBase": "База API:",
  "diagnostics.runChecks": "Запустить проверки",
  "diagnostics.checking": "Проверка…",
  "diagnostics.backAdmin": "Назад в админ",
  "diagnostics.home": "Главная",
  "diagnostics.success": "Проверки завершены. Смотрите JSON ниже.",

  "reader.header.eyebrow": "Reader",
  "reader.header.title": "Статья",
  "reader.header.descBefore": "Читайте извлечённый текст для",
  "reader.header.descAfter": ". Обычно открывайте из Workspace.",
  "reader.workIdLabel": "work_id",
  "reader.load": "Загрузить",
  "reader.empty.title": "Работа не загружена",
  "reader.empty.body": "Введите `work_id` выше или начните с Workspaces.",
  "reader.openReaderWs": "Reader в workspace",
  "reader.openGraphWs": "Graph в workspace",

  "evidence.header.eyebrow": "Evidence",
  "evidence.header.title": "Трассируемость",
  "evidence.header.descBefore": "Цитаты на уровне чанков для",
  "evidence.header.descMid": ". Откройте статью из Workspace, затем левую панель или query в URL.",
  "evidence.empty.title": "Контекст evidence не загружен",
  "evidence.empty.body":
    "Укажите `work_id` или перейдите из цитаты в Ask workspace для просмотра evidence с нужным контекстом.",
  "evidence.openLastWorkspace": "Открыть последний workspace",

  "askPage.header.eyebrow": "Ask",
  "askPage.header.title": "Вопросы",
  "askPage.header.description":
    "Вопросы по статье или по всему корпусу. Выберите статью в Workspaces / Workspace, затем укажите work_id ниже или в URL.",
  "askPage.empty.openLastWorkspace": "Открыть последний workspace",

  "graph.toolbar.title": "Граф",
  "graph.toolbar.loadTooltip": "Загрузить по work_id (дополнительно)",
  "graph.toolbar.loadAria": "Загрузить граф по work_id",
  "graph.toolbar.aboutTooltip": "Об этой странице",
  "graph.toolbar.aboutAria": "Показать описание страницы",
  "graph.popover.hint":
    "Необязательно: вставьте UUID конкретной работы. Предпочтительнее открыть статью из Workspace или Workspaces.",
  "graph.popover.cancel": "Отмена",
  "graph.popover.apply": "Применить",
  "graph.about.eyebrow": "Graph",
  "graph.about.title": "Просмотр",
  "graph.about.description":
    "Левая панель: Workspaces, Ask, Evidence. Подсказки: ?lab=1 диагностика, ?compact=1 плотнее, ?focus=1 без боковых панелей.",
  "graph.missing.title": "Контекст графа ещё не задан",
  "graph.missing.description":
    "Откройте граф workspace (workspace_id) или одну статью (work_id) из Workspaces / Workspace или иконку ключа.",
  "graph.missing.footnote": "Подсказка: ?lab=1 расширяет диагностику; ?compact=1 или ?focus=1 ужимает layout.",
  "graph.openLastWorkspace": "Открыть последний workspace",

  "settings.snapshot.general.label": "Общие",
  "settings.snapshot.general.description": "Окружение, идентичность приложения и глобальные значения по умолчанию.",
  "settings.snapshot.llm.label": "LLM",
  "settings.snapshot.llm.description": "Эндпоинт провайдера, модель по умолчанию, учётные данные и тесты.",
  "settings.snapshot.ingestion.label": "Загрузка и обработка документов",
  "settings.snapshot.ingestion.description": "PDF, front-matter, ссылки и настройка пайплайна извлечения.",
  "settings.snapshot.storage.label": "Хранилище и интеграции",
  "settings.snapshot.storage.description": "Neo4j, Qdrant, Postgres, OpenAlex и внешние интеграции.",
  "settings.snapshot.benchmark.label": "Бенчмарк",
  "settings.snapshot.benchmark.description": "Настройки teacher/student и параметры запуска бенчмарков.",
  "settings.snapshot.security.label": "Безопасность и доступ",
  "settings.snapshot.security.description": "Права, модель доступа и управление секретами.",
  "settings.snapshot.diagnostics.label": "Диагностика",
  "settings.snapshot.diagnostics.description": "Статус подключений, недавние тесты и диагностика окружения.",
};
