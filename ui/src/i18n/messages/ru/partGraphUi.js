/** @type {Record<string, string>} */
export default {
  "graphShell.loading": "Загрузка графа…",
  "dedup.title": "Проверка дубликатов статей (в workspace)",
  "dedup.intro":
    "Кластеры с одинаковым DOI, arXiv, OpenAlex или отпечатком. Выберите, какую работу оставить; слияние переназначает цитаты и синхронизирует Qdrant при удалении дубликата из Neo4j.",
  "dedup.loadingCandidates": "Загрузка кандидатов…",
  "dedup.noClusters": "В этом workspace нет кластеров дубликатов.",
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
