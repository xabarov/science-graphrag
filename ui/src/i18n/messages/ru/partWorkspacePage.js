/** @type {Record<string, string>} */
export default {
  "workspace.paper.loading": "Загрузка статьи…",
  "workspace.paper.noTitle": "(без названия)",
  "workspace.paper.hint":
    "Откройте «Чтение» для извлечённого текста; слева — «Граф», «Вопросы» и «Доказательства» для того же",
  "workspace.paper.hintSuffix": "Клик по карточке (вне ссылок) фокусирует статью в URL.",
  "workspace.paper.reader": "Чтение",
  "workspace.paper.graph": "Граф",
  "workspace.paper.ask": "Вопросы",
  "workspace.paper.evidence": "Доказательства",
  "workspace.paper.yearChip": "Год {{year}}",
  "workspace.paper.doiChip": "DOI {{doi}}",

  "workspace.err.notFound": "Рабочая область не найдена.",
  "workspace.empty.alert":
    "Пока нет рабочей области. Создайте её в списке «Рабочие области», затем загрузите PDF или текст либо привяжите существующий идентификатор статьи (work_id).",
  "workspace.empty.workspaces": "Рабочие области",
  "workspace.empty.about": "О приложении",

  "workspace.header.eyebrow": "Рабочая область",
  "workspace.header.titleFallback": "Статьи",
  "workspace.header.loadingWs": "Загрузка рабочей области…",
  "workspace.header.paperCountOne": "В этой области {{count}} статья.",
  "workspace.header.paperCountMany": "В этой области статей: {{count}}.",
  "workspace.header.focusedPaper": "Фокус на статье:",
  "workspace.header.workspaceGraph": "Граф области",
  "workspace.header.graphStatsLine":
    "Граф: {{works}} работ · {{authors}} авторов · {{internal}} внутр. цит. · {{external}} внеш. цит.",

  "workspace.upload.title": "Загрузка статьи",
  "workspace.upload.desc":
    "PDF, Markdown или текст. Обработка на сервере; страница опрашивает статус и обновляет список.",
  "workspace.upload.starting": "Запуск…",
  "workspace.upload.processing": "Обработка…",
  "workspace.upload.chooseFile": "Выбрать файл",
  "workspace.upload.jobLine": "job {{id}} · {{status}}",
  "workspace.upload.newWorkId": "Новый work_id (id статьи):",
  "workspace.upload.dash": "—",

  "workspace.advanced.accordion": "Дополнительно: привязать статью по work_id",
  "workspace.advanced.workIdLabel": "work_id",
  "workspace.advanced.placeholder": "Существующий work_id из каталога",
  "workspace.advanced.add": "Добавить в область",

  "workspace.noPapers":
    "Пока нет статей. Загрузите файл выше или добавьте work_id из каталога на странице «Рабочие области».",
};
