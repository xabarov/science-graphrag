---
name: run-long-ingest
description: Безопасный запуск долгого ingest или corpus-wide бенчмарка с pre-flight, heartbeat-мониторингом и recovery. Используй при любом `ingest-corpus`, `pilot_ingest_cv_corpus.sh`, `science-graphrag-*-benchmark` на 5+ кейсах, или batch `dual_validate` на 10+ packs. Выводит чёткий чек-лист «что проверить ДО запуска», «как мониторить», «что делать при hang». Срабатывает на упоминания «ingest корпус», «прогон бенчмарка на корпусе», «dual validate batch», «расширить корпус».
---

# Run long ingest / corpus-wide benchmark safely

## Контекст

Источник скилла — постмортем Wave 4 (2026-04-26): `ingest-corpus` повис на 16-м файле `Libra R-CNN.pdf` ≈ 3 часа из-за **четырёх** независимых причин:

1. `SCIENCE_GRAPHRAG_SKIP_HOST_DOTENV=1` перекрыл `MAIN_LLM_API_KEY` из `.env` — LLM-запросы шли «без ключа», ловили upstream 401, retry с экспонентой не помогал.
2. У `httpx` клиента не было выставленного `connect_timeout` для кейса CLOSE-WAIT — socket остался в полузакрытом состоянии без recovery.
3. У ingest-pipeline нет per-file timeout — один зависший файл блокирует весь прогон.
4. Нет JSONL-checkpoint — после kill пришлось вручную определять, какие файлы успели обработаться.

Backlog item на структурное решение: `docs/backlog/refactor-backend.md` → `[OPEN] Robust ingest orchestration`. **До его закрытия** этот скилл обязателен.

## Когда использовать

- `science-graphrag ingest-corpus` (любое `--corpus-dir` с > 5 файлов).
- `scripts/pilot_ingest_cv_corpus.sh` или аналоги.
- Любой `science-graphrag-*-benchmark` на > 5 кейсов с `--extractor production` (live LLM).
- `scripts/dual_extract_validate.py` на > 10 packs.
- `scripts/aggregate_benchmark_metrics.py --write-trust-baseline` после большой серии прогонов.
- Backfill / seed скрипты, которые ходят в Neo4j по `(:Work)` множественно.

## Phase 1 — Pre-flight (3 проверки, 30 секунд)

### 1.1 API keys видимы внутри окружения процесса

```bash
.venv/bin/python -c "from science_graphrag.config import Settings; s=Settings(); print('main_llm:', bool(s.main_llm_api_key), 'embeddings:', bool(s.embeddings_api_key), 'judge:', bool(s.judge_llm_api_key))"
```

Должно напечатать `True` для нужных каналов. Если хоть один `False`:

- Проверить `.env` (`grep -E "MAIN_LLM_API_KEY|EMBEDDINGS_API_KEY|OPENROUTER_API_KEY" .env`).
- Если в env присутствует `SCIENCE_GRAPHRAG_SKIP_HOST_DOTENV=1` — **снять или явно прокинуть ключи** при запуске:

  ```bash
  MAIN_LLM_API_KEY=<key> .venv/bin/science-graphrag ingest-corpus ...
  ```

- НИКОГДА не запускай долгий CLI пока этот smoke-check не зелёный.

### 1.2 Инфраструктура поднята

```bash
docker compose ps --format 'table {{.Service}}\t{{.Status}}'
```

Все сервисы должны быть `running (healthy)`. Если что-то `unhealthy`:

```bash
docker compose logs --tail=50 <service>
docker compose up -d <service>  # restart specific
```

### 1.3 Console-script зарегистрирован (если запускаешь новый или изменённый)

```bash
command -v science-graphrag-<имя>
# должен вернуть путь в .venv/bin/
```

Если не находит:

```bash
.venv/bin/pip install -e . --quiet
```

После любой правки `[project.scripts]` в `pyproject.toml` это **обязательно**.

## Phase 2 — Запуск (правильный шаблон)

### 2.1 Только в фоне

Долгий CLI запускается через `Shell` с `block_until_ms: 0`:

```text
Shell command: source .venv/bin/activate && science-graphrag ingest-corpus --corpus-dir tests/fixtures/corpus/cv_pdfs/ --workspace-id pilot 2>&1 | tee eval/results/ingest-pilot-$(date +%Y%m%d-%H%M%S).log
working_directory: /home/roman/pyprojects/ML/Prod/science-graphrag
block_until_ms: 0
description: Pilot CV corpus ingest in background
```

Заметь `2>&1 | tee` — без него stderr теряется, и hang отлавливать сложнее.

### 2.2 One-shot smoke check через 30-60s

Через 30-60 секунд после старта прочитать tail terminal-файла:

```text
Read terminals/<id>.txt последние 30 строк
```

Что искать (positive):

- Сообщение про инициализацию pipeline (Neo4j connected, Qdrant collection ready).
- Первый файл начат (`processing: <slug>.pdf`).
- Прогресс по стадиям (extract chunks → embed → write Neo4j → write Qdrant).

Что искать (negative — **немедленно kill**):

- `Traceback` в первых 50 строках.
- Stuck на одной строке `Connecting to OpenRouter...` без последующего вывода.
- `401 Unauthorized` или `403 Forbidden` от OpenRouter — значит API key не подхватился, см. Phase 1.1.
- Пустой stdout > 60 секунд после старта.

### 2.3 Что НЕ делать

- НЕ использовать `block_until_ms: 600000` чтобы «дождаться» — заблокирует turn без возможности реагировать.
- НЕ опрашивать `AwaitShell` каждые 5 секунд — пустая трата cache. Sized polling: 60-270s слайсы для коротких; 1200s+ для длинных.
- НЕ запускать второй `ingest-corpus` параллельно с первым (могут оба попасть в Qdrant и побить дедуп).

## Phase 3 — Мониторинг во время прогона

### 3.1 Признаки нормального прогресса

- terminal-файл обновляется не реже 1 раз/минуту.
- Прогресс по файлам (`processed: N/M`).
- Логи embeddings/extraction не висят на одной строке > 3 минут.

### 3.2 Признаки зависания (любой = действовать)

- terminal-файл не обновлялся > 5 минут на команде, которая ожидаемо логирует.
- `lsof -i -nP -p <PID>` показывает много CLOSE-WAIT соединений к OpenRouter / Neo4j / Qdrant.
- `ps -o etime= -p <PID>` показывает время > expected_runtime × 2 без вывода.

### 3.3 Команды для inspection

```bash
# найти PID процесса (если знаешь имя)
pgrep -af "science-graphrag ingest"

# CLOSE-WAIT соединения процесса
lsof -i -nP -p <PID> 2>/dev/null | rg -i "close.wait"

# системное время процесса
ps -o pid,etime,stat,cmd -p <PID>

# tail последнего лога (без cat)
Read /home/roman/.cursor/projects/.../terminals/<id>.txt offset=-50
```

## Phase 4 — Recovery после hang

1. **НЕ ждать дальше.** При уверенном hang — `kill -9 <PID>` (SIGTERM не помогает с зависшим httpx).
2. **Проанализировать tail terminal-файла**: на каком этапе встал, последний обработанный файл/case.
3. **Проверить `lsof` для PID** на CLOSE-WAIT — это классика OpenRouter timeout без recovery.
4. **Записать в backlog** (`docs/backlog/refactor-backend.md` или текущий план в `docs/analysis/`):
   - Какая команда повисла (полный CLI).
   - На каком файле/case (последняя строка лога).
   - Симптомы (CLOSE-WAIT count, время idle).
   - Текущий обходной путь, если есть.
5. **Точечный resume**: если первый прогон обработал N файлов из M — запусти `science-graphrag ingest <single-file> --force-new-document` для пропущенных по одному, пока не закроется `[OPEN] Robust ingest orchestration`.

## Phase 5 — Post-success

После успешного завершения долгой операции:

1. **Re-seed workspace membership** (если ingest добавил новые `:Work`):

   ```bash
   .venv/bin/python scripts/seed_benchmark_workspaces.py
   ```

2. **Re-backfill workspace_id payloads в Qdrant**:

   ```bash
   .venv/bin/python scripts/backfill_workspace_payloads.py
   ```

   (помни про `ws_full_corpus="*"` backlog item — для unbounded workspaces скрипт сейчас silent skip).

3. **Re-aggregate trust baseline**, если затронули bench-related коллекции:

   ```bash
   .venv/bin/python scripts/aggregate_benchmark_metrics.py --write-trust-baseline
   ```

4. **Зафиксировать diff в `eval/results/benchmark-trust-baseline.json`** через `git diff` — это снимок «как сейчас», и любое изменение `advisory_phantom_count` должно быть осознанным.

5. **Quality gates** на затронутых модулях (см. `.cursor/rules/backend-quality.mdc`): `isort`, `black`, `pylint --fail-under=7.0`, `pytest`.

## Quick reference (одной таблицей)

| Phase | Что делать | Сколько занимает |
|-------|------------|------------------|
| 1. Pre-flight | API key smoke + `docker compose ps` + console-script registered | 30 сек |
| 2. Запуск | `block_until_ms: 0` + smoke check через 30-60s | 1 мин |
| 3. Мониторинг | terminal tail + `lsof` при подозрении на hang | passive |
| 4. Recovery | kill -9 + analysis + backlog entry + точечный resume | 5-15 мин при hang |
| 5. Post-success | re-seed + backfill + aggregate + git diff trust baseline | 2-5 мин |

## Связанные правила

- `.cursor/rules/long-running-ops.mdc` (always applied) — общее правило для long-running CLI.
- `.cursor/rules/benchmarks-trust.mdc` — что проверять при добавлении нового runner'а.
- `.cursor/rules/venv.mdc` — всегда из `.venv/bin/`.
- `docs/backlog/refactor-backend.md` → `[OPEN] Robust ingest orchestration` — структурное решение, после его merge большая часть этого скилла станет ненужной (CLI сам будет делать checkpoint + resume + per-file timeout).
