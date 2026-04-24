/** @type {Record<string, string>} */
export default {
  "graphShell.loading": "Загрузка графа…",

  "graph.workspacePanel.emptyHint":
    "Выберите статью или откройте граф рабочей области (параметр workspace_id).",

  "graph.wsToolbar.title": "Граф рабочей области",
  "graph.wsToolbar.modeInner": "Внутренний",
  "graph.wsToolbar.modeUnion1hop": "Объединение +1",
  "graph.wsToolbar.modeSemantic": "Семантика",
  "graph.wsToolbar.modeFull": "Полный",
  "graph.wsToolbar.depth1": "глубина 1",
  "graph.wsToolbar.depth2": "глубина 2",
  "graph.wsToolbar.external": "Внешние",
  "graph.wsToolbar.statsWorks": "{{count}} стат.",
  "graph.wsToolbar.statsAuthors": "{{count}} авт.",
  "graph.wsToolbar.statsExtCites": "{{count}} внеш. цит.",
  "graph.wsToolbar.nodeType.Work": "Работа",
  "graph.wsToolbar.nodeType.Author": "Автор",
  "graph.wsToolbar.nodeType.Method": "Метод",
  "graph.wsToolbar.nodeType.Dataset": "Датасет",
  "graph.wsToolbar.nodeType.Venue": "Площадка",
  "graph.wsToolbar.nodeType.Institution": "Организация",

  "dedup.title": "Проверка дубликатов статей (в текущей области)",
  "dedup.intro":
    "Кластеры с одинаковым DOI, arXiv, OpenAlex или отпечатком. Выберите, какую работу оставить; слияние переназначает цитаты и синхронизирует Qdrant при удалении дубликата из Neo4j.",
  "dedup.loadingCandidates": "Загрузка кандидатов…",
  "dedup.noClusters": "В этой рабочей области нет кластеров дубликатов.",
  "dedup.candidateLine": "Кандидат {{current}} / {{total}} · {{kind}} · ключ {{key}}",
  "dedup.loadingTitle": "Загрузка заголовка…",
  "dedup.mergeActions": "Действия слияния",
  "dedup.keep1merge2": "Оставить 1, слить 2",
  "dedup.keep2merge1": "Оставить 2, слить 1",
  "dedup.keep1merge3": "Оставить 1 · слить 3",
  "dedup.skip": "Пропустить",
  "dedup.next": "Далее",
  "dedup.prev": "Назад",
  "dedup.refresh": "Обновить список",
};
