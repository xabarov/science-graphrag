# Runbook: обогащение layer-1 gold (`enrich_gold_layer1.py`)

## Цель

Заполнить в `gold.json` для корпуса `*_realpdf`:

- полный список arXiv id из `references_benchmark.raw_entries` (regex, бесплатно);
- при необходимости — авторов, год, arXiv/DOI работы из начала `article.md` (LLM, платно).

Скрипт: [`scripts/enrich_gold_layer1.py`](../../scripts/enrich_gold_layer1.py).

## Переменные (LLM)

- `TESTGEN_LLM_API_KEY`
- `TESTGEN_LLM_BASE_URL` (например `https://openrouter.ai/api/v1`)
- `TESTGEN_LLM_MODEL` (например `anthropic/claude-sonnet-4.6`)

Опционально: `--env-file /path/.env` (ключи не логируются).

## Рекомендуемый порядок

1. **Пилот без LLM** (regex только):

   ```bash
   .venv/bin/python scripts/enrich_gold_layer1.py \
     --cases faster_rcnn_realpdf detr_realpdf yolov1 --dry-run
   ```

   Проверить `gold_enrichment_<case_id>.json` → `step_a_arxiv_from_bibliography`.

2. **Пилот с LLM** (1–3 кейса, контроль бюджета):

   ```bash
   .venv/bin/python scripts/enrich_gold_layer1.py --cases faster_rcnn_realpdf detr_realpdf yolov1
   ```

   Сверить `step_b_header_metadata` с PDF/статьёй; при плохом качестве — править промпт в скрипте и повторить.

3. **Все nightly** (после стабилизации промпта):

   ```bash
   .venv/bin/python scripts/enrich_gold_layer1.py --all-nightly
   ```

4. **Применение в gold** (после ревью enrichment-файлов):

   ```bash
   .venv/bin/python scripts/enrich_gold_layer1.py --cases faster_rcnn_realpdf --apply
   ```

   По умолчанию добавляются `quality_thresholds` (`min_authorship_names_f1`, `min_sample_arxiv_f1`). Отключить: `--no-quality-thresholds`.

5. Прогнать layer-1 suite и обновить `eval/results/*` + `scripts/generate_benchmark_metrics_tables.py`.

## Тир `smoke`

Контрактные кейсы перечислены в `smoke` внутри `tests/fixtures/benchmarks/*/case_tiers.json` — см. [benchmark-dataset-inventory.md](../benchmarks/benchmark-dataset-inventory.md).
