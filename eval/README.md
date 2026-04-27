# eval

Бенчмарки, эталонные кейсы, метрики извлечения и retrieval, регрессионные отчёты.

См. [docs/roadmap.md](../docs/roadmap.md) Phase 4, [docs/benchmarks/README.md](../docs/benchmarks/README.md), [docs/benchmarks/object-detection-corpus.md](../docs/benchmarks/object-detection-corpus.md).

Стабилизация benchmark + API: [docs/runbooks/benchmark-stabilization-baseline.md](../docs/runbooks/benchmark-stabilization-baseline.md), [docs/runbooks/benchmark-stabilization-triage.md](../docs/runbooks/benchmark-stabilization-triage.md), [docs/runbooks/benchmark-decision-gate.md](../docs/runbooks/benchmark-decision-gate.md).

**Docker dev (`make dev-up`):** после смены переменных окружения в `docker-compose.dev.yml` пересоберите только API: `make dev-recreate-api` (или `docker compose -f docker-compose.dev.yml up -d api --force-recreate`).

**Reference gate:** перед массовыми правками gold/метрик убедитесь, что эталон **YOLOv1** (три `baseline-reference-*-yolov1*.json`) зелёный; см. раздел 6.1 в runbook baseline.

**Сводка метрик по всем lane:** после прогонов выполните `.venv/bin/python scripts/aggregate_benchmark_metrics.py` или `./scripts/refresh_benchmark_metrics.sh` — см. `eval/results/benchmark-metrics-summary.md`.

**API (Phase 5/6 bridge):** `GET /v1/works`, `GET /v1/works/{work_id}`, `GET /v1/works/{work_id}/graph`, `GET /v1/works/{work_id}/chunks` — см. [`docs/specs/frontend-ui-api-contracts-v1.md`](../docs/specs/frontend-ui-api-contracts-v1.md); UI-прототип подгружает список works на `/`.

## Установка

Из корня репозитория:

```bash
.venv/bin/pip install -e ".[dev]"
```

## Переменные окружения (LLM)

| Режим | Переменные |
|-------|------------|
| **Без LLM** (детерминированные эвристики, подходит для CI без ключей) | `SCIENCE_GRAPHRAG_EXTRACTION_LLM_ENABLED=false` и пустые `SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY`, `MAIN_LLM_API_KEY`, `API_KEY`. |
| **С LLM** (извлечение layer-1 и semantic ближе к продакшену) | Задайте ключ: `SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY` или `MAIN_LLM_API_KEY`; при необходимости `SCIENCE_GRAPHRAG_EXTRACTION_LLM_BASE_URL` / `MAIN_LLM_BASE_URL`, модель — `SCIENCE_GRAPHRAG_EXTRACTION_LLM_MODEL`. |

**Эталонные прогоны (см. [roadmap Phase 4](../docs/roadmap.md)):** всегда включайте LLM для оценки качества и Neo4j после ingest.

1. В **`.env`** задайте `SCIENCE_GRAPHRAG_EXTRACTION_LLM_ENABLED=true`. Для `get_settings()` значения из **`.env` перекрывают** одноимённые переменные процесса (чтобы локальный `.env` не проигрывал устаревшему `export …=false` в shell).
2. Ключ: `MAIN_LLM_API_KEY` и при необходимости `MAIN_LLM_BASE_URL` / `MAIN_LLM_MODEL`, либо дублируйте как `SCIENCE_GRAPHRAG_EXTRACTION_LLM_*`.
3. Чтобы **выключить** LLM при том же `.env` с `true`, поменяйте флаг **в `.env`** или временно закомментируйте строку; одна только переменная в shell больше не перебивает `.env` (в CI секретного `.env` нет — там по-прежнему задаётся `SCIENCE_GRAPHRAG_EXTRACTION_LLM_ENABLED=false` в workflow).

Семантическая стадия (ontology v1) управляется `SCIENCE_GRAPHRAG_SEMANTIC_EXTRACTION_ENABLED` (по умолчанию включена, если LLM доступен).

## Retrieval / `POST /v1/query` (Wave F)

- Код: `eval/retrieval/` (`metrics`, `runner`).
- Фикстуры: `tests/fixtures/benchmarks/retrieval/<case_id>/`; тиры — [`case_tiers.json`](../tests/fixtures/benchmarks/retrieval/case_tiers.json).
- Документ: [docs/benchmarks/retrieval-eval-v1.md](../docs/benchmarks/retrieval-eval-v1.md).
- Сводка агрегатора (advisory lane): [docs/runbooks/benchmark-decision-gate.md](../docs/runbooks/benchmark-decision-gate.md) §8, `eval/results/benchmark-metrics-summary.md`.

```bash
science-graphrag-retrieval-benchmark tests/fixtures/benchmarks/retrieval/cv_corpus_methods_overview
# merge-safe contract smoke (default tier)
science-graphrag-retrieval-benchmark tests/fixtures/benchmarks/retrieval --suite --mock-answer \
  --json-out eval/results/current-retrieval-merge-safe-mock.json
# strict fingerprint gold (pilot placeholders until live capture)
science-graphrag-retrieval-benchmark tests/fixtures/benchmarks/retrieval --suite --tier strict_pilot --mock-answer \
  --json-out eval/results/current-retrieval-strict-pilot-mock.json
# all non-skipped cases
science-graphrag-retrieval-benchmark tests/fixtures/benchmarks/retrieval --suite --tier all --json-out eval/results/retrieval-suite.json
# live pilot mini-tier (requires ingested pilot corpus + Qdrant; no --mock-answer)
science-graphrag-retrieval-benchmark tests/fixtures/benchmarks/retrieval --suite --tier live_corpus_mini \
  --json-out eval/results/retrieval-live-corpus-mini.json
```

See [docs/benchmarks/retrieval-live-tier-v1.md](../docs/benchmarks/retrieval-live-tier-v1.md).

Полный чеклист advisory прогонов и `aggregate_benchmark_metrics.py`: [docs/runbooks/benchmark-pilot-advisory-runs.md](../docs/runbooks/benchmark-pilot-advisory-runs.md).

## Claims / epistemic ontology (Wave H1, advisory)

- Код: `eval/claims/` (`heuristic_extract`, `metrics`, `runner`).
- Фикстуры: `tests/fixtures/benchmarks/claims/`; тиры — [`case_tiers.json`](../tests/fixtures/benchmarks/claims/case_tiers.json).
- Спека: [docs/benchmarks/ontology-claims-benchmark-v1.md](../docs/benchmarks/ontology-claims-benchmark-v1.md).

```bash
# merge-safe contract (shape-only)
science-graphrag-claims-benchmark tests/fixtures/benchmarks/claims --suite --tier claims_merge_contract
# frozen mini-pack (deterministic anchor harness)
science-graphrag-claims-benchmark tests/fixtures/benchmarks/claims --suite --tier claims_mini \
  --json-out eval/results/claims-mini-suite.json
# corpus-derived v2 mini + pilot (see docs/benchmarks/ontology-claims-benchmark-v1.md)
science-graphrag-claims-benchmark tests/fixtures/benchmarks/claims --suite --tier claims_corpus_v2_mini \
  --json-out eval/results/current-claims-corpus-v2-mini.json
science-graphrag-claims-benchmark tests/fixtures/benchmarks/claims --suite --tier claims_pilot \
  --json-out eval/results/current-claims-pilot-suite.json
# Wave O: production LLM lane (requires MAIN_LLM_* / extraction LLM key); advisory artifact for aggregator
science-graphrag-claims-benchmark tests/fixtures/benchmarks/claims --suite --tier claims_pilot \
  --extractor production \
  --json-out eval/results/current-claims-production-pilot.json
```

## References resolution (v1 harness, advisory)

- Код: `eval/references_resolution/` (`metrics`, `runner`).
- Фикстуры: `tests/fixtures/benchmarks/references_resolution/`; тиры — [`case_tiers.json`](../tests/fixtures/benchmarks/references_resolution/case_tiers.json).
- Спека: [docs/specs/benchmark-family-references-resolution-v1.md](../docs/specs/benchmark-family-references-resolution-v1.md).

```bash
science-graphrag-references-resolution-benchmark tests/fixtures/benchmarks/references_resolution --suite \
  --tier refs_merge_contract \
  --json-out eval/results/current-references-resolution-contract.json
science-graphrag-references-resolution-benchmark tests/fixtures/benchmarks/references_resolution --suite \
  --tier refs_mini \
  --json-out eval/results/current-references-resolution-mini.json
```

## Layer-1 (markdown → drafts)

- Код: `eval/layer1/` (`spec`, `metrics`, `runner`).
- Фикстуры: `tests/fixtures/benchmarks/layer1/<case_id>/`.
- Runner теперь возвращает non-zero exit, если `metrics.contract.passed=false` хотя бы в одном кейсе suite.

**Один кейс:**

```bash
science-graphrag-layer1-benchmark tests/fixtures/benchmarks/layer1/yolov1 --json-out eval/results/yolov1-latest.json
```

**Все кейсы** (включая `*_realpdf` из корпуса object-detection):

```bash
SCIENCE_GRAPHRAG_EXTRACTION_LLM_ENABLED=false \
  science-graphrag-layer1-benchmark tests/fixtures/benchmarks/layer1 --suite --json-out eval/results/layer1-suite.json
```

**Только быстрые кейсы** (`merge_safe`, без тяжёлых real-pdf):

```bash
SCIENCE_GRAPHRAG_EXTRACTION_LLM_ENABLED=false \
  science-graphrag-layer1-benchmark tests/fixtures/benchmarks/layer1 --suite --tier merge_safe
```

Тиры: `tests/fixtures/benchmarks/layer1/case_tiers.json`. Альтернатива: `python -m eval.layer1.runner …`.

**Authoritative nightly (`nightly_heavy`) + сводка gate** — после правок `gold.json` переснимите JSON и агрегатор (нужен LLM, см. `EXTRACTION_LLM_*` / `MAIN_LLM_*`):

```bash
science-graphrag-layer1-benchmark tests/fixtures/benchmarks/layer1 \
  --suite --tier nightly_heavy \
  --threshold-profile reporting_skip_f1_gates \
  --json-out eval/results/current-llm-layer1-nightly-heavy-suite.json
python scripts/aggregate_benchmark_metrics.py
python scripts/generate_benchmark_metrics_tables.py
```

Профиль `reporting_skip_f1_gates` описан в [docs/runbooks/benchmark-decision-gate.md](../docs/runbooks/benchmark-decision-gate.md).

**Обогащение gold (regex + опционально LLM):** [`scripts/enrich_gold_layer1.py`](../scripts/enrich_gold_layer1.py) пишет рядом с `gold.json` файл `gold_enrichment_<case_id>.json` (шаг A: все arXiv из `references_benchmark.raw_entries`; шаг B: год / arXiv работы / авторы из начала `article.md`, нужен `TESTGEN_LLM_*`). Сначала пилот на 1–3 кейсах с `--dry-run` (без LLM), затем с ключами без `--dry-run`, ревью, потом `--apply`.

**Корпус object-detection (много PDF):** инвентарь и скрипты — [docs/benchmarks/object-detection-inventory.md](../docs/benchmarks/object-detection-inventory.md), [docs/benchmarks/object-detection-corpus.md](../docs/benchmarks/object-detection-corpus.md). Регенерация layer-1 из локальной папки: `scripts/build_od_corpus_fixtures.py`; layer-2 semantic: `scripts/generate_layer2_od_semantic_fixtures.py`.

Отчёт baseline: [docs/benchmarks/yolov1-baseline.md](../docs/benchmarks/yolov1-baseline.md).

## Graph-level (ingest → Neo4j)

Нужны **живые** Neo4j, Qdrant и настройки в `.env` (см. `docker-compose.yml`).

- Код: `eval/graph_v1/`.
- Один кейс (эталон YOLOv1):

```bash
science-graphrag-graph-benchmark tests/fixtures/benchmarks/layer1/yolov1 --json-out eval/results/yolov1-graph-latest.json
```

- Suite с фильтром по тиру (как layer-1):

```bash
science-graphrag-graph-benchmark tests/fixtures/benchmarks/layer1 --suite --tier merge_safe
```

План и контракт `graph_expectations`: [docs/benchmarks/graph-level-eval-v1.md](../docs/benchmarks/graph-level-eval-v1.md).
Runner возвращает non-zero exit, если `metrics.contract.passed=false`.

**Сводка CITES для NLP-отчёта** (macro P/R/F1 по suite JSON):

```bash
.venv/bin/python scripts/report_graph_cites_metrics.py
```

## Relations (Neo4j semantic edges)

После полного ingest сравнивает эталон `semantic_gold.json` с фактическими рёбрами
`:USES_METHOD` / `:EVALUATED_ON` в Neo4j (тот же скорер, что у layer-2, предсказания
читаются из графа). Пилотный тир `relations_pilot` (3 кейса) в
`tests/fixtures/benchmarks/layer2/case_tiers.json`.

```bash
science-graphrag-relations-benchmark tests/fixtures/benchmarks/layer2 --suite --tier relations_pilot \
  --json-out eval/results/relations-neo4j-pilot-suite.json
.venv/bin/python scripts/report_relation_graph_metrics.py --relations-suite-json eval/results/relations-neo4j-pilot-suite.json
```

Без Neo4j-артефакта `report_relation_graph_metrics.py` усредняет те же поля из layer-2 nightly JSON
(числа совпадают с §4.0 при успешной проекции в граф).

## Report aggregation (extraction + claims diagnostics)

```bash
.venv/bin/python scripts/report_extraction_entity_metrics.py
.venv/bin/python scripts/report_claims_paraphrase_diagnostics.py
.venv/bin/python scripts/enrich_multimodel_summary_for_report.py
```

## Layer-2 semantic (Method / Dataset)

- Код: `eval/layer2/`.
- Без LLM (smoke, как в merge CI):

```bash
SCIENCE_GRAPHRAG_EXTRACTION_LLM_ENABLED=false \
  science-graphrag-layer2-benchmark tests/fixtures/benchmarks/layer2 --suite --tier merge_safe
```

- Кейсы с эталоном семантики (нужен LLM), тир `nightly_semantic`:

```bash
science-graphrag-layer2-benchmark tests/fixtures/benchmarks/layer2 --suite --tier nightly_semantic
```

В GitHub Actions (workflow **Integration**) шаг `Layer-2 nightly_semantic` выполняется **только если** в secrets репозитория задан `MAIN_LLM_API_KEY`; иначе шаг пропускается.

## Chat agent — roadmap use-case harness

- Код: `eval/chat_agent/roadmap_runner.py`, `roadmap_metrics.py`, `workspace_audit.py`.
- Фикстуры: `tests/fixtures/benchmarks/chat_agent_roadmap/` (`baseline_workspace_manifest.json`, `cases/*.json`).
- Эталонная область: **`ws-pilot-od`** (тот же pilot OD, что и retrieval `workspace_scoped` / agent-tools).

Pre-flight Neo4j + Qdrant audit (рекомендуется перед live suite):

```bash
.venv/bin/python scripts/chat_agent_workspace_readiness_audit.py \
  --manifest tests/fixtures/benchmarks/chat_agent_roadmap/baseline_workspace_manifest.json \
  --out-json eval/results/chat-agent-roadmap-workspace-audit.json \
  --out-md eval/results/chat-agent-roadmap-workspace-audit.md
```

Roadmap suite (детерминированный mock — подходит для CI без LLM):

```bash
science-graphrag-chat-agent-roadmap \
  --fixtures tests/fixtures/benchmarks/chat_agent_roadmap \
  --out eval/results/chat-agent-roadmap-mock-latest \
  --skip-audit --mock-runtime
```

Live прогон (ключи LLM + Neo4j + Qdrant; audit падает с кодом 3 при `blocked`):

```bash
science-graphrag-chat-agent-roadmap \
  --fixtures tests/fixtures/benchmarks/chat_agent_roadmap \
  --out eval/results/chat-agent-roadmap-live-latest
# опционально: снимок HTTP к Phoenix UI (best-effort)
science-graphrag-chat-agent-roadmap \
  --fixtures tests/fixtures/benchmarks/chat_agent_roadmap \
  --out eval/results/chat-agent-roadmap-live-latest \
  --fetch-phoenix
```

Артефакты: `summary.json` / `summary.md`, `workspace_audit.json`, per-case `cases/<case_id>/case_result.json` + `trace_audit.json`.

## Compare baseline vs current

Для benchmark-driven цикла используйте comparator (падает при regressions):

```bash
science-graphrag-benchmark-compare \
  eval/results/baseline-layer1.json \
  eval/results/current-layer1.json \
  --json-out eval/results/compare-layer1.json
```

Поддерживаются both formats: single-case (`{run_metadata, case}`) и suite (`{run_metadata, cases}`).

## Рекомендуемый developer loop

1. Выберите затронутый кейс/слой (например, `yolov1`, `retinanet_semantic`).
2. Запустите узкий benchmark локально (single-case).
3. Сравните с baseline через `science-graphrag-benchmark-compare`.
4. Повторите правку до отсутствия regressions.
5. Запустите suite по нужному tier (`merge_safe` / `nightly_*`).

## Teacher gold (DeepSeek) vs student (Mistral) — автоматический эталон

Переменные (опционально, в `.env`): `SCIENCE_GRAPHRAG_BENCHMARK_TEACHER_LLM_API_KEY`, `SCIENCE_GRAPHRAG_BENCHMARK_TEACHER_LLM_BASE_URL`, `SCIENCE_GRAPHRAG_BENCHMARK_TEACHER_LLM_MODEL` (иначе берутся `--api-key` / `--model` или `EXTRACTION_LLM_*` / `MAIN_LLM_*`).

1. Сгенерировать `gold_teacher.json` по корпусу (нужен ключ учителя):

```bash
.venv/bin/python scripts/generate_teacher_layer1_gold.py \
  --fixtures-root tests/fixtures/benchmarks/layer1 \
  --out-root eval/teacher_gold/layer1 \
  --tier nightly_heavy
```

2. Оценить **ученика** (в `.env` — модель/ключ Mistral и `SCIENCE_GRAPHRAG_EXTRACTION_LLM_ENABLED=true`) против teacher-gold:

```bash
science-graphrag-layer1-benchmark tests/fixtures/benchmarks/layer1 \
  --suite --tier nightly_heavy \
  --external-gold-root eval/teacher_gold/layer1 \
  --gold-filename gold_teacher.json \
  --json-out eval/results/layer1-suite-vs-teacher-gold.json
```

Опционально смягчить пороги поверх эталона в файле: `--threshold-profile student_mistral`.

3. Семантический слой от учителя (layer-2): `scripts/generate_semantic_teacher_fixtures.py` пишет `eval/teacher_gold/layer2/<case>/semantic_gold_teacher.json`.

### Teacher-gold remediation (когда регенерировать, provenance)

**Регенерация допустима**, когда осознанно меняется профиль учителя (промпт / модель / tier) и нужен новый эталон для сравнения со студентом: зафиксируйте в **сообщении коммита** скрипт, аргументы (`--tier`, пути `--fixtures-root` / `--out-root`), и идентификатор модели (без секретов). Для layer-1: `scripts/generate_teacher_layer1_gold.py`; для layer-2: `scripts/generate_semantic_teacher_fixtures.py` — одинаковое правило provenance.

**Не используйте регенерацию** как способ скрыть регрессию экстрактора или битый `article.md`: сначала triage по [teacher-gold-audit-checklist.md](../docs/benchmarks/teacher-gold-audit-checklist.md) и [benchmark-stabilization-triage.md](../docs/runbooks/benchmark-stabilization-triage.md) (код или fixture, затем при необходимости teacher refresh).

## Регенерация `article.md` из локального PDF

```bash
.venv/bin/python scripts/build_real_pdf_layer1_fixture.py \
  --pdf /path/to/RetinaNet.pdf \
  --out tests/fixtures/benchmarks/layer1/retinanet_focal_realpdf
```

После правок пересмотрите `gold.json` и при необходимости обновите [docs/benchmarks/object-detection-corpus.md](../docs/benchmarks/object-detection-corpus.md).
