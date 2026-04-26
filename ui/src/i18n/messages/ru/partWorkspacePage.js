/** @type {Record<string, string>} */
export default {
  "workspace.paper.loading": "Загрузка статьи…",
  "workspace.paper.noTitle": "(без названия)",
  "workspace.paper.hint":
    "Откройте «Чтение» для извлечённого текста. Граф, вопросы и сводка по всей области — в шапке страницы.",
  "workspace.paper.hintSuffix": "Клик по карточке (вне ссылок) фокусирует статью в URL.",
  "workspace.paper.reader": "Чтение",
  "workspace.paper.workGraph": "Граф статьи",
  "workspace.actions.askWorkspace": "Вопросы по области",
  "workspace.paper.yearChip": "Год {{year}}",
  "workspace.paper.doiChip": "DOI {{doi}}",

  "workspace.err.notFound": "Рабочая область не найдена.",
  "workspace.err.serverHintInline":
    "(Ошибка сервера — возможно, недоступен API или бэкенд; проверьте логи и состояние сервисов.)",
  "workspace.err.loadTitle": "Не удалось загрузить данные рабочей области",
  "workspace.err.serverHint":
    "Коды HTTP 5xx обычно означают, что research API недоступен, упал или отвалился по таймауту за reverse proxy. Убедитесь, что стек запущен (например docker compose), и повторите попытку.",
  "workspace.err.retry": "Повторить",
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
  "workspace.header.summarizing": "Сводка...",
  "workspace.header.summarizeAction": "Суммировать рабочую область",
  "workspace.header.generatingHypotheses": "Генерация...",
  "workspace.header.generateHypotheses": "Сгенерировать гипотезы",
  "workspace.header.graphStatsLine":
    "Граф: {{works}} работ · {{authors}} авторов · {{internal}} внутр. цит. · {{external}} внеш. цит.",
  "workspace.summary.dialogTitle": "Сводка по рабочей области",
  "workspace.summary.empty": "Сводки пока нет.",
  "workspace.idea.dialogTitle": "Помощник гипотез и противоречий",
  "workspace.dialog.close": "Закрыть",

  "workspace.upload.title": "Загрузка статьи",
  "workspace.upload.desc":
    "PDF, Markdown или текст. Обработка на сервере; страница опрашивает статус и обновляет список.",
  "workspace.upload.starting": "Запуск…",
  "workspace.upload.processing": "Обработка…",
  "workspace.upload.chooseFile": "Выбрать файл",
  "workspace.upload.chooseMultiple": "Несколько файлов",
  "workspace.upload.chooseZip": "Загрузить .zip",
  "workspace.upload.dropHint":
    "Или перетащите сюда файлы или папку (PDF / Markdown / текст).",
  "workspace.upload.jobLine": "job {{id}} · {{status}}",
  "workspace.upload.newWorkId": "Новый work_id (id статьи):",
  "workspace.upload.dash": "—",
  "workspace.ingest.progressLabel": "Общий прогресс: {{pct}}%",
  "workspace.ingest.detailsLogs": "Подробности / логи",

  "workspace.advanced.accordion": "Дополнительно: привязать статью по work_id",
  "workspace.advanced.workIdLabel": "work_id",
  "workspace.advanced.placeholder": "Существующий work_id из каталога",
  "workspace.advanced.add": "Добавить в область",

  "workspace.noPapers":
    "Пока нет статей. Загрузите файл выше или добавьте work_id из каталога на странице «Рабочие области».",

  "workspace.side.graphTitle": "Снимок графа",
  "workspace.side.graphStatsLine":
    "{{works}} работ · {{authors}} авторов · {{internal}} внутр. цит. · {{external}} внеш. цит.",
  "workspace.side.dedupTitle": "Умное дедуплицирование",
  "workspace.side.dedupPendingLine": "Ожидают проверки почти-дубликаты: {{count}}",
  "workspace.side.dedupPendingUnknown": "Запустите сканирование в блоке ниже, чтобы обновить очередь.",
  "workspace.side.dedupJump": "Перейти к дедупу",
};
