# Корпус CV object-detection и фикстуры

PDF лежат локально у разработчика (не в git). В репозитории — закоммиченные `article.md` + `gold.json`; воспроизведение текста: [`scripts/build_real_pdf_layer1_fixture.py`](../../scripts/build_real_pdf_layer1_fixture.py). В каждом кейсе `*_realpdf` файл `SOURCE.txt` указывает исходный PDF.

**Полная таблица PDF → `case_id`:** [object-detection-inventory.md](object-detection-inventory.md).

**Массовая генерация layer-1 из локальной папки с PDF:**

```bash
.venv/bin/python scripts/build_od_corpus_fixtures.py \
  --pdf-dir /path/to/object-detection
```

**Layer-2 semantic для всего OD-корпуса:**

```bash
.venv/bin/python scripts/generate_layer2_od_semantic_fixtures.py
```

## Соответствие PDF ↔ `case_id` ↔ тир (кратко)

Все перечисленные в [object-detection-inventory.md](object-detection-inventory.md) real-PDF статьи — тир **`nightly_heavy`** в [`layer1/case_tiers.json`](../../tests/fixtures/benchmarks/layer1/case_tiers.json).

Эталонный кейс **YOLOv1** — [`layer1/yolov1/`](../../tests/fixtures/benchmarks/layer1/yolov1/) (текст из `YOLOv1.pdf` через тот же пайплайн), тир **`merge_safe`**.

## Layer-2 semantic

Для каждой статьи корпуса есть каталог `layer2/<name>_semantic/` с `semantic_gold.json` и `article_path` на соответствующий `layer1/.../article.md`. Тиры: [`layer2/case_tiers.json`](../../tests/fixtures/benchmarks/layer2/case_tiers.json) — все OD-кейсы в **`nightly_semantic`**, смоук без LLM — **`merge_safe`** (`no_llm_smoke`).

## Graph expectations

Блок `graph_expectations` в `gold.json` для OD real-PDF задан в **широких диапазонах** (устойчивость к OpenAlex / dedup). Для **`yolov1`** значения **зафиксированы** под graph-level eval и unit-тесты ([graph-level-eval-v1.md](graph-level-eval-v1.md)). После прогона ingest на живом Neo4j остальные кейсы можно сужать по фактическим snapshot-метрикам.
