# Nightly Failures Analysis and Remediation Plan

Дата анализа: `2026-04-07`

Контекст:
- Layer-1: ученик `mistralai/mistral-small-3.2-24b-instruct` против `gold_teacher.json`, сгенерированного учителем `deepseek/deepseek-v3.2`
- Layer-2: `nightly_semantic` против текущего `semantic_gold.json`

Артефакты:
- `eval/results/layer1-nightly-heavy-student-vs-teacher.json`
- `eval/results/layer1-student-vs-teacher-aggregates.json`
- `eval/results/layer2-nightly-semantic-mistral.json`
- `eval/results/layer2-nightly-semantic-aggregates.json`

## Executive Summary

### Layer-1

- Всего кейсов: `30`
- Contract passed: `18 / 30`
- Провалов: `12`

Распределение причин по `checks`:

| Check | Count | Комментарий |
|------|------:|-------------|
| `min_abstract_rouge_l` | 11 | Главная системная причина. Почти наверняка проблема **метрики/threshold**, а не фактического качества извлечения. |
| `min_affiliations_f1` | 1 | Локальная проблема нормализации Unicode / mojibake в affiliation. |
| `min_authorship_names_recall` | 1 | Локальная проблема качества самого teacher-gold (`Joseph Red` вместо `Joseph Redmon`). |

### Layer-2

- Всего кейсов: `31`
- Passed: `30 / 31`
- Единственный провал: `efficientdet_semantic`

Причина: текущее `semantic_gold.json` ожидает имя paper-level метода (`efficientdet`, `efficientdet-d`), а модель стабильно извлекает contribution-level методы (`BiFPN`, `Compound Scaling`).

## Main Finding

Сейчас основная доля красноты не похожа на реальную деградацию извлечения.

Для layer-1 почти все красные кейсы возникают потому, что в контракт добавлен `min_abstract_rouge_l=0.22`, а сама метрика считается как `ROUGE-L` между:
- коротким `gold.work_metadata.abstract_prefix`
- полным предсказанным abstract

Это конструктивно нестабильная проверка:
- длинный корректный abstract получает заниженный `ROUGE-L` против короткого prefix;
- при этом в тех же кейсах часто `abstract_prefix_ok=True`, title/authors/references зелёные;
- следовательно, сигнал говорит не "abstract плохой", а "gate выбран неудачно".

## Detailed Failure Analysis

## Layer-1 Failures

### Group A. Contract noise from `min_abstract_rouge_l`

Затронутые кейсы:
- `atss_realpdf`
- `cascade_rcnn_realpdf`
- `detrs_realpdf`
- `dn_detr_realpdf`
- `faster_rcnn_realpdf`
- `fcos_realpdf`
- `gfl_realpdf`
- `sppnet_realpdf`
- `ssd_realpdf`
- `tood_realpdf`
- `yolov2_realpdf`

Общий паттерн:
- `title_rouge_l ~= 1.0`
- `title_token_f1 ~= 1.0`
- `sample_arxiv_f1 ~= 1.0`
- `sample_doi_f1 ~= 1.0`
- authors mostly green
- падает только `abstract_rouge_l_vs_prefix`

Representative examples:

| Case | `abstract_prefix_ok` | `abstract_rouge_l_vs_prefix` | Interpretation |
|------|----------------------|-----------------------------:|----------------|
| `atss_realpdf` | `True` | `0.205` | Содержательно abstract совпадает, но gate ниже порога `0.22`. |
| `cascade_rcnn_realpdf` | `True` | `0.178` | Prefix проходит, ROUGE-L нет. |
| `detrs_realpdf` | `True` | `0.180` | Та же проблема. |
| `fcos_realpdf` | `True` | `0.216` | Практически на пороге, провал неинформативный. |
| `gfl_realpdf` | `True` | `0.125` | Вероятно, модель переписала вводный кусок своими словами, но не сломала фактическое извлечение. |
| `tood_realpdf` | `True` | `0.189` | Тот же паттерн. |
| `yolov2_realpdf` | `True` | `0.176` | Падает по той же причине, плюс отдельная проблема authorship gold. |
| `sppnet_realpdf` | `False` | `0.156` | Здесь уже есть реальный edge case нормализации кавычек/Unicode, но основной красный сигнал всё равно идёт через ROUGE-L gate. |

#### Root cause

Текущий gate в `eval/layer1/metrics.py` и preset `student_mistral` из `eval/layer1/threshold_profiles.py` не согласованы с природой данных:
- teacher gold хранит только `abstract_prefix`, а не полный abstract;
- `ROUGE-L` по полному abstract против короткого prefix имеет плохую калибровку;
- одно и то же содержание может давать низкий score, особенно если модель:
  - возвращает более длинный abstract,
  - меняет пунктуацию,
  - нормализует line-break artifacts,
  - меняет начало на slightly paraphrased variant.

#### Proposed fix

`P0`

Убрать `min_abstract_rouge_l` из обязательного contract для student-vs-teacher и оставить его как diagnostic only.

Более надёжные альтернативы:
- Вариант A: использовать только `abstract_prefix_ok` для gated-check.
- Вариант B: сравнивать `gold.abstract_prefix` не со всем abstract, а только с `pred_abstract[:len(prefix)+delta]`.
- Вариант C: в teacher-gold хранить полный `abstract`, а не только prefix; тогда ROUGE-L станет осмысленным.

Рекомендация:
- короткий срок: `min_abstract_rouge_l=None` в `STUDENT_MISTRAL_LAYER1_THRESHOLDS`
- средний срок: расширить `GoldWorkMetadata` полем `abstract_full` и мигрировать teacher-gold generation

### Group B. Unicode / mojibake in affiliations

Затронутый кейс:
- `hog_human_detection_realpdf`

Симптом:
- `names_f1=1.0`
- `names_recall=1.0`
- `affiliations_f1=0.0`

Сравнение gold vs pred:

- Gold: `INRIA Rhône-Alps, 655 avenue de l'Europe, Montbonnot 38334, France`
- Pred: `INRIA Rhone-Alps, 655 avenue de l'Europe, Montbonnot 38334, France`

#### Root cause

Это не ошибка извлечения affiliation как сущности. Это ошибка нормализации строки:
- teacher/prediction содержит mojibake (`Rhone`) вместо `Rhône`;
- `_norm_aff()` в `eval/layer1/metrics.py` сейчас делает только lowercase + whitespace normalization;
- акцент/encoding drift не компенсируется.

#### Proposed fix

`P0`

Расширить нормализацию affiliation:
- Unicode NFKD + accent stripping
- нормализация кавычек/апострофов
- optional mojibake cleanup для частых артефактов PDF/encoding

Минимальный практичный вариант:
- сделать canonical string для scoring без диакритики
- отдельно сохранять raw value в диагностике

Ожидаемый эффект:
- `hog_human_detection_realpdf` должен перейти в green без ослабления meaningful thresholds.

### Group C. Teacher-gold defect in author name

Затронутый кейс:
- `yolov2_realpdf`

Симптом:
- `min_authorship_names_recall=False`
- `names_f1=0.5`
- `names_recall=0.5`
- `names_difflib_macro=0.935`

Сравнение gold vs pred:
- Pred: `Joseph Redmon`, `Ali Farhadi`
- Gold: `Joseph Red`, `Ali Farhadi`

#### Root cause

Проблема в teacher-gold:
- gold зафиксировал усечённое имя `Joseph Red`;
- student вытащил более правдоподобное полное имя `Joseph Redmon`;
- текущий scoring по множествам считает это промахом.

Это классический false negative benchmark.

#### Proposed fix

`P0`

Исправить `gold_teacher.json` для `yolov2_realpdf` либо вручную, либо через post-processing teacher-gold pipeline.

Надёжное системное решение:
- добавить gold QA step после teacher generation:
  - искать подозрительные короткие author names;
  - flag patterns: last token truncated, suspicious prefix of another known full name, very short family name fragment;
  - optionally сравнивать gold author against student author with high `difflib` and low exact match.

Практическая эвристика:
- если gold name является строгим префиксом predicted name и `difflib > 0.9`, считать candidate for auto-repair/report.

### Group D. Additional normalization gap in abstract prefix match

Затронутый кейс:
- `sppnet_realpdf`

Симптом:
- `abstract_prefix_ok=False`
- gold prefix содержит `"artificial"` в straight quotes
- predicted abstract содержит `“artificial”` в curly quotes

#### Root cause

`_norm_abstract_match()` нормализует hyphen variants, но почти не нормализует:
- curly quotes vs straight quotes
- other Unicode punctuation variants

Это не основной источник красноты suite, но это реальный баг нормализации.

#### Proposed fix

`P1`

Расширить `_norm_abstract_match()`:
- `“ ”` -> `"`
- `‘ ’` -> `'`
- optional `×` -> `x`
- optional ligature / spacing normalization

## Layer-2 Failure

### `efficientdet_semantic`

Симптом:
- `precision_methods=0.0`
- `recall_methods=0/2`
- dataset part green (`COCO`)

Gold:
- `efficientdet`
- `efficientdet-d`

Predicted:
- `BiFPN`
- `Compound Scaling`

#### Root cause

Здесь есть несовпадение между тем, что benchmark считает "method", и тем, что извлекает модель:
- benchmark хочет верхнеуровневое название paper contribution (`EfficientDet`)
- модель извлекает ключевые нововведения внутри paper (`BiFPN`, `Compound Scaling`)

То есть это не "случайная ошибка", а ambiguity уровня ontology/prompt/gold design.

#### Proposed fix options

`P1`

Вариант A. Исправить gold:
- расширить `expected_method_names_normalized`:
  - добавить `bifpn`
  - добавить `compound scaling`

Плюс:
- быстрый стабилизирующий fix

Минус:
- benchmark начнёт считать subcomponents равноправными основному методу

Вариант B. Исправить prompt semantic extraction:
- явно требовать top-level method / paper contribution first
- subcomponents only as aliases or `description_short`

Плюс:
- онтология станет чище

Минус:
- потребует ретеста всего `nightly_semantic`

Вариант C. Добавить post-processing rule:
- если paper title / evidence указывает на `EfficientDet`, а extracted methods = `BiFPN` + `Compound Scaling`, добавлять canonical method `EfficientDet`

Плюс:
- минимальный локальный fix

Минус:
- rule-based special case

Рекомендация:
- краткий срок: Вариант A или C
- средний срок: Вариант B и пересмотр semantic ontology contract

## Prioritized Remediation Plan

### Phase 1. Fix benchmark validity first

Цель: убрать false negatives до любых изменений prompt/model.

1. Убрать `min_abstract_rouge_l` из gating profile `student_mistral`.
2. Починить normalization для affiliations и abstract punctuation.
3. Исправить `yolov2_realpdf` teacher gold (`Joseph Red` -> `Joseph Redmon`).
4. Перезапустить:
   - `science-graphrag-layer1-benchmark ... --tier nightly_heavy --external-gold-root eval/teacher_gold/layer1 ...`

Expected result:
- большинство из текущих 12 провалов исчезнет без изменений extraction prompt.

### Phase 2. Harden teacher-gold pipeline

Цель: сделать auto-generated gold менее хрупким.

1. Добавить post-generation QA для `gold_teacher.json`.
2. Ввести warning report по кейсам:
   - truncated author names
   - empty / obviously damaged affiliations
   - suspicious Unicode corruption
3. Решить, хранить ли полный abstract в teacher-gold.

Suggested outputs:
- `eval/results/teacher-gold-quality-report.json`
- `eval/results/teacher-gold-quality-report.md`

### Phase 3. Resolve semantic ontology ambiguity

Цель: сделать `layer2` устойчивым и семантически последовательным.

1. Зафиксировать policy:
   - benchmark measures paper-level methods
   - или benchmark measures both paper-level methods and core submethods
2. Под эту policy:
   - обновить `tests/fixtures/benchmarks/layer2/efficientdet_semantic/semantic_gold.json`
   - или скорректировать prompt в `science_graphrag/ingestion/llm/semantic_extraction.py`
3. Перезапустить `nightly_semantic`.

### Phase 4. Recalibrate thresholds after validity fixes

Цель: только после устранения false negatives оценить, где действительно слаб ученик.

1. Собрать новый suite report.
2. Посмотреть остаточные провалы.
3. Решить, какие thresholds:
   - отражают product minimum,
   - а какие лишь наказывают style drift.

## Concrete Code Changes to Propose

### `eval/layer1/threshold_profiles.py`

- Убрать или занизить `min_abstract_rouge_l`

Preferred:
- `min_abstract_rouge_l=None`

### `eval/layer1/metrics.py`

- Усилить `_norm_aff()`
- Усилить `_norm_abstract_match()`
- Возможный split:
  - diagnostic metric `abstract_rouge_l_vs_prefix`
  - contract metric `abstract_prefix_window_ok`

### `scripts/generate_teacher_layer1_gold.py` and `eval/layer1/teacher_gold.py`

- Добавить QA/report stage
- Возможный repair pass для obviously truncated author names

### `tests/fixtures/benchmarks/layer2/efficientdet_semantic/semantic_gold.json`

- Или расширить expected methods
- Или оставить как есть и менять semantic extraction prompt/normalizer

### `science_graphrag/ingestion/llm/semantic_extraction.py`

- Если идём через prompt fix:
  - stronger instruction: prefer umbrella method introduced by the paper
  - subcomponents should not replace canonical method name

## Suggested Verification Sequence

После исправлений:

1. Узкие regression checks:
   - `hog_human_detection_realpdf`
   - `yolov2_realpdf`
   - `sppnet_realpdf`
   - `efficientdet_semantic`

2. Затем:
   - layer-1 `nightly_heavy` vs teacher gold
   - layer-2 `nightly_semantic`

3. Затем:
   - `scripts/aggregate_benchmark_metrics.py`

## Recommended Implementation Order

### P0

- убрать `min_abstract_rouge_l` из contract
- нормализовать affiliation mojibake / diacritics
- исправить дефект `yolov2_realpdf` gold

### P1

- улучшить abstract punctuation normalization
- решить `efficientdet_semantic`
- добавить teacher-gold QA report

### P2

- пересмотреть representation полного abstract в gold
- при необходимости ужесточить semantic ontology and prompts

## Expected Outcome After P0

Ожидаемо:
- layer-1 pass rate вырастет примерно с `60%` до `~96%+`
- останутся только genuinely interesting failures, а не benchmark noise
- layer-2 останется с одним содержательным кейсом (`efficientdet_semantic`) или станет полностью зелёным после policy fix

## Final Recommendation

Не начинать с "подкрутки prompt у Mistral".

Первый приоритет здесь не model quality, а benchmark validity:
- один дефект в gold,
- одна проблема нормализации,
- одна системная ошибка дизайна gating metric,
- один semantic ontology mismatch.

Пока это не исправлено, любые дальнейшие метрики будут частично шумными и плохо интерпретируемыми.
