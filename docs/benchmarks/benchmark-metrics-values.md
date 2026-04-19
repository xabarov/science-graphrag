# Таблицы значений метрик (снимок артефактов)

Этот файл **генерируется** из JSON в `eval/results/`, перечисленных в `eval/results/benchmark-metrics-summary.json` → `authoritative_artifacts`. Не правьте таблицы вручную: при обновлении отчётов перегенерируйте файл.

```bash
.venv/bin/python scripts/generate_benchmark_metrics_tables.py
```

**Сгенерировано:** 2026-04-19 16:18:10 UTC

## Что означает `passed`

- **Layer-1:** `metrics.contract.passed` — все пороговые проверки эталона для кейса.
- **Graph:** `metrics.contract.passed` при наличии `graph_expectations`.
- **Layer-2 semantic:** `metrics.passed` — пороги recall/precision по методам и датасетам.
- **Retrieval / claims / references_resolution:** см. `eval/*/metrics.py` и поля `passed` в JSON.

Сводка gate без числовых колонок: [benchmark-metrics-summary.md](../../eval/results/benchmark-metrics-summary.md). Смысл метрик: [benchmark-metrics-catalog.md](benchmark-metrics-catalog.md).

## Сводные сигналы из `benchmark-metrics-summary.json`

| Поле | Значение |
| --- | --- |
| `decision` | GO |
| layer1 nightly `failed_count` | 0 |
| layer1 nightly `references_llm_failed_events` | 4 |
| layer2 nightly `failed_count` | 0 |


## Layer-1 reference (yolov1)

Артефакт: `eval/results/current-reference-layer1-yolov1.json`

| case_id | contract_passed | title_exact | title_rouge_L | title_token_F1 | abstract_rouge_L_vs_prefix | names_F1 | affiliations_F1 | sample_arxiv_F1 | sample_doi_F1 | ref_count_ok |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| yolov1 | true | true |  |  |  | 1 | 1 | 0.923077 | 1 | true |


## Graph reference (yolov1)

Артефакт: `eval/results/current-reference-graph-yolov1.json`

| case_id | has_expectations | contract_passed | cited_arxiv_P | cited_arxiv_R | cited_arxiv_F1 | cites_count |
| --- | --- | --- | --- | --- | --- | --- |
| yolov1 | true | true | 0.571429 | 1 | 0.727273 | 14 |


## Layer-2 reference (yolov1_semantic)

Артефакт: `eval/results/current-reference-layer2-yolov1-semantic.json`

| case_id | passed | precision_methods | recall_methods | precision_datasets | recall_datasets | notes |
| --- | --- | --- | --- | --- | --- | --- |
| yolov1_semantic | true | 1 | 1/2 | 0.666667 | 2/2 | method_tp=1/2; dataset_tp=2/2 |


## Layer-1 nightly (`nightly_heavy`)

Артефакт: `eval/results/current-llm-layer1-nightly-heavy-suite-after-prompt-fix.json`

### Общие цифры (верх suite-JSON)

| Поле | Значение |
| --- | --- |
| `summary.case_count` | 30 |
| `summary.all_passed` | true |

Пороговый gate и счётчики (`failed_count`, `references_llm_failed_events`) — в `eval/results/benchmark-metrics-summary.json` (секции `layer1_nightly`, `decision_gate`). Усреднённых F1/ROUGE по suite там **нет**: сводка только про прохождение контракта.

| case_id | contract_passed | title_exact | title_rouge_L | title_token_F1 | abstract_rouge_L_vs_prefix | names_F1 | aff_F1 | sample_arxiv_F1 | sample_doi_F1 | ref_count_ok |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| atss_realpdf | true | true |  |  |  | 0 | 0 | 1 | 1 | true |
| cascade_rcnn_realpdf | true | true |  |  |  | 0 | 0 | 1 | 1 | true |
| centernet_realpdf | true | true |  |  |  | 0 | 0 | 1 | 1 | true |
| cornernet_realpdf | true | true |  |  |  | 0 | 1 | 0.083333 | 1 | true |
| deformable_detr_realpdf | true | true |  |  |  | 0 | 0 | 0.5 | 1 | true |
| detr_realpdf | true | true |  |  |  | 0 | 0 | 1 | 1 | true |
| detrs_realpdf | true | true |  |  |  | 0 | 0 | 1 | 1 | true |
| dino_realpdf | true | true |  |  |  | 0 | 0 | 0.8 | 1 | true |
| dn_detr_realpdf | true | true |  |  |  | 0 | 0 | 1 | 1 | true |
| efficientdet_realpdf | true | true |  |  |  | 0 | 0 | 1 | 1 | true |
| fast_rcnn_realpdf | true | true |  |  |  | 0 | 0 | 1 | 1 | true |
| faster_rcnn_realpdf | true | true |  |  |  | 0 | 0 | 1 | 1 | true |
| fcos_realpdf | true | true |  |  |  | 0 | 0 | 1 | 1 | true |
| fpn_realpdf | true | true |  |  |  | 0 | 0 | 1 | 1 | true |
| gfl_realpdf | true | true |  |  |  | 0 | 0 | 1 | 1 | true |
| hog_human_detection_realpdf | true | true |  |  |  | 0 | 0 | 1 | 1 | true |
| libra_rcnn_realpdf | true | true |  |  |  | 0 | 0 | 1 | 1 | true |
| mask_rcnn_realpdf | true | true |  |  |  | 0 | 0 | 1 | 1 | true |
| overfeat_realpdf | true | true |  |  |  | 0 | 0 | 1 | 1 | true |
| part_based_models_realpdf | true | true |  |  |  | 0 | 0 | 1 | 1 | true |
| rcnn_realpdf | true | true |  |  |  | 0 | 0 | 1 | 1 | true |
| retinanet_focal_realpdf | true | true |  |  |  | 0 | 0 | 1 | 1 | true |
| rfcn_realpdf | true | true |  |  |  | 0 | 0 | 0.8 | 1 | true |
| selective_search_realpdf | true | true |  |  |  | 0 | 0 | 1 | 1 | true |
| sppnet_realpdf | true | true |  |  |  | 0 | 0 | 1 | 1 | true |
| ssd_realpdf | true | true |  |  |  | 0 | 0 | 1 | 1 | true |
| tood_realpdf | true | true |  |  |  | 0 | 0 | 1 | 1 | true |
| yolov2_realpdf | true | true |  |  |  | 0 | 0 | 1 | 1 | true |
| yolov3_realpdf | true | true |  |  |  | 0 | 0 | 1 | 1 | true |
| yolox_realpdf | true | true |  |  |  | 0 | 0 | 1 | 1 | true |

### Агрегаты по полям (nightly suite)

| Поле | N (с сигналом) | Среднее / доля | Комментарий |
| --- | --- | --- | --- |
| `contract.passed` | 30 | 100.0% | доля кейсов с passed |
| `title_exact_normalized` | 30 | 100.0% | доля exact title |
| `references.count_ok` | 30 | 100.0% | доля кейсов с count_ok |
| `names_f1` (mean) | 0 |  | нет эталона авторов в отчёте |
| `affiliations_f1` (mean) | 0 |  | нет эталона аффилиаций |
| `sample_arxiv_f1` (mean) | 30 | 0.939444 | по кейсам где значение есть в JSON |
| `sample_doi_f1` (mean) | 30 | 1 | по кейсам где значение есть в JSON |
| `title_rouge_l` (mean) | 0 |  | если ключ есть в metadata |
| `title_token_f1` (mean) | 0 |  | если ключ есть в metadata |
| `abstract_rouge_l_vs_prefix` (mean) | 0 |  | если ключ есть в metadata |


*Среднее `names_F1` по кейсам с непустым эталоном авторов: **n/a**. В текущем nightly JSON у всех кейсов `gold_count` = 0 в блоке authorships — колонка `names_F1` не используется как сигнал по корпусу.*

### Почему много нулей и пустых ячеек в таблице ниже

- **`names_F1` почти везде 0:** в `gold.json` многих `*_realpdf` кейсов список `authorships` **намеренно пустой** (см. `description` в gold: авторская строка не размечена как comma-separated). Тогда эталон имён — пустое множество, а предсказанные авторы считаются ложноположительными → precision/recall/F1 по именам = 0 (см. `eval/layer1/metrics.py`, `prf1_tp_fp_fn`). Это **не** значит, что модель «не извлекла авторов» в смысле продукта — значит, что **бенчмарк пока не ставит эталон по авторам** на этом корпусе.

- **`aff_F1` часто 0 по той же причине** (пустой эталон аффилиаций); единичные ненули — там, где в gold всё же заданы аффилиации / совпали множества.

- **Пустые `title_rouge_L` / `title_token_F1` / `abstract_rouge_L_vs_prefix`:** в закоммиченном JSON этих ключей в `metrics.metadata` часто **нет** (таблица показывает пусто). В актуальном коде `eval/layer1/metrics.py` поля считаются и при сериализации обычно были бы `null` или число; если нужны ROUGE-цифры в отчёте — **перепрогоните** suite и обновите артефакт, либо смотрите кейсы с непустым эталоном заголовка/абстракта (например merge_safe).

- **Что реально драйвит `contract_passed` на nightly:** в типичном `gold.json` для realpdf заданы `title` + `abstract_prefix` + ограничения по числу ссылок (`references.expected_count` / `min_count`), а `quality_thresholds` часто `null` — т.е. **нет** порогов по `min_title_rouge_l` / F1 авторам в контракте.


## Layer-2 nightly (`nightly_semantic`)

Артефакт: `eval/results/current-llm-layer2-nightly-semantic-suite.json`

### Общие цифры (верх suite-JSON)

| Поле | Значение |
| --- | --- |
| `summary.case_count` | 31 |
| `summary.all_passed` | true |


| case_id | passed | P_methods | R_methods | P_datasets | R_datasets | notes |
| --- | --- | --- | --- | --- | --- | --- |
| atss_semantic | true | 1 | 2/2 | 1 | 1/1 | method_tp=2/2; dataset_tp=1/1 |
| cascade_rcnn_semantic | true | 1 | 1/2 | 1 | 1/1 | method_tp=1/2; dataset_tp=1/1 |
| centernet_semantic | true | 0.25 | 1/2 | 1 | 1/1 | method_tp=1/2; dataset_tp=1/1 |
| cornernet_semantic | true | 0.666667 | 2/2 | 1 | 1/1 | method_tp=2/2; dataset_tp=1/1 |
| deformable_detr_semantic | true | 1 | 1/2 | 1 | 1/1 | method_tp=1/2; dataset_tp=1/1 |
| detr_semantic | true | 1 | 2/3 | 1 | 1/1 | method_tp=2/3; dataset_tp=1/1 |
| detrs_semantic | true | 1 | 1/2 | 0.5 | 1/1 | method_tp=1/2; dataset_tp=1/1 |
| dino_semantic | true | 1 | 3/3 | 0.5 | 1/1 | method_tp=3/3; dataset_tp=1/1 |
| dn_detr_semantic | true | 0.2 | 1/2 | 1 | 1/1 | method_tp=1/2; dataset_tp=1/1 |
| efficientdet_semantic | true | 0.5 | 2/2 | 0.5 | 1/1 | method_tp=2/2; dataset_tp=1/1 |
| fast_rcnn_semantic | true | 0.25 | 1/2 | 0.5 | 1/2 | method_tp=1/2; dataset_tp=1/2 |
| faster_rcnn_semantic | true | 1 | 1/3 | 1 | 2/2 | method_tp=1/3; dataset_tp=2/2 |
| fcos_semantic | true | 0.25 | 1/2 | 0.5 | 1/1 | method_tp=1/2; dataset_tp=1/1 |
| fpn_semantic | true | 1 | 2/2 | 0.333333 | 1/1 | method_tp=2/2; dataset_tp=1/1 |
| gfl_semantic | true | 0.75 | 3/3 | 1 | 1/1 | method_tp=3/3; dataset_tp=1/1 |
| hog_semantic | true | 1 | 2/3 | 0.5 | 1/1 | method_tp=2/3; dataset_tp=1/1 |
| libra_rcnn_semantic | true | 1 | 1/3 | 1 | 1/1 | method_tp=1/3; dataset_tp=1/1 |
| mask_rcnn_semantic | true | 0.5 | 1/3 | 1 | 1/1 | method_tp=1/3; dataset_tp=1/1 |
| overfeat_semantic | true | 1 | 1/2 | 1 | 1/1 | method_tp=1/2; dataset_tp=1/1 |
| part_based_models_semantic | true | 0.5 | 2/3 | 0.5 | 2/2 | method_tp=2/3; dataset_tp=2/2 |
| rcnn_semantic | true | 0.5 | 2/3 | 0.666667 | 2/2 | method_tp=2/3; dataset_tp=2/2 |
| retinanet_semantic | true | 1 | 2/2 | 1 | 1/2 | method_tp=2/2; dataset_tp=1/2 |
| rfcn_semantic | true | 0.428571 | 3/3 | 0 | 0/1 | method_tp=3/3; dataset_tp=0/1 |
| selective_search_semantic | true | 1 | 1/2 | 1 | 1/1 | method_tp=1/2; dataset_tp=1/1 |
| sppnet_semantic | true | 1 | 2/3 | 0.666667 | 2/2 | method_tp=2/3; dataset_tp=2/2 |
| ssd_semantic | true | 1 | 3/3 | 0.666667 | 2/2 | method_tp=3/3; dataset_tp=2/2 |
| tood_semantic | true | 0.75 | 3/3 | 1 | 1/1 | method_tp=3/3; dataset_tp=1/1 |
| yolov1_semantic | true | 1 | 2/2 | 1 | 2/2 | method_tp=2/2; dataset_tp=2/2 |
| yolov2_semantic | true | 0.5 | 2/3 | 0.666667 | 2/2 | method_tp=2/3; dataset_tp=2/2 |
| yolov3_semantic | true | 0.666667 | 2/2 | 0.333333 | 1/1 | method_tp=2/2; dataset_tp=1/1 |
| yolox_semantic | true | 1 | 2/2 | 1 | 1/1 | method_tp=2/2; dataset_tp=1/1 |


## Retrieval merge_safe_contract (mock)

Артефакт: `eval/results/current-retrieval-merge-safe-mock.json`

| case_id | passed | contract_only | hit_count | hit_ok | min_hit_count | work_id_ok |
| --- | --- | --- | --- | --- | --- | --- |
| cv_corpus_methods_overview | true | true | 0 |  |  |  |
| single_stage_detectors | true | true | 0 |  |  |  |
| yolo_family_keywords | true | true | 0 |  |  |  |


## Retrieval strict_pilot (mock)

Артефакт: `eval/results/current-retrieval-strict-pilot-mock.json`

| case_id | passed | contract_only | hit_count | hit_ok | min_hit_count | work_id_ok |
| --- | --- | --- | --- | --- | --- | --- |
| strict_pilot_corpus_wide | true | false | 1 | true | 1 | true |
| strict_pilot_methods | true | false | 1 | true | 1 | true |
| strict_pilot_work_scoped | true | false | 1 | true | 1 | true |


## Retrieval live_corpus_mini

Артефакт: `eval/results/current-retrieval-live-corpus-mini.json`

| case_id | passed | contract_only | hit_count | hit_ok | min_hit_count | work_id_ok |
| --- | --- | --- | --- | --- | --- | --- |
| live_corpus_methods_wide | true | false | 10 | true | 1 | true |
| live_yolov1_architecture | true | false | 8 | true | 1 | true |
| live_yolov1_intro | true | false | 8 | true | 1 | true |
| live_yolov1_methods_combo | true | false | 8 | true | 1 | true |
| live_yolov1_training | true | false | 6 | true | 1 | true |


## Claims merge_contract

Артефакт: `eval/results/current-claims-merge-contract.json`

| case_id | passed | claim_recall | claim_precision | expected_n | predicted_n |
| --- | --- | --- | --- | --- | --- |
| claims_contract_shape | true | 1 | 1 | 0 | 0 |


## Claims mini

Артефакт: `eval/results/current-claims-mini-suite.json`

| case_id | passed | claim_recall | claim_precision | expected_n | predicted_n |
| --- | --- | --- | --- | --- | --- |
| yolov1_fast_yolo_speed_claim | true | 1 | 1 | 1 | 1 |
| yolov1_framing_claim | true | 1 | 1 | 1 | 1 |
| yolov1_localization_tradeoff_claim | true | 1 | 1 | 1 | 1 |
| yolov1_speed_claim | true | 1 | 1 | 1 | 1 |
| yolov1_unified_pipeline_claim | true | 1 | 1 | 1 | 1 |


## Claims corpus_v2_mini

Артефакт: `eval/results/current-claims-corpus-v2-mini.json`

| case_id | passed | claim_recall | claim_precision | expected_n | predicted_n |
| --- | --- | --- | --- | --- | --- |
| corpus_faster_rcnn_rpn_shared | true | 1 | 1 | 1 | 1 |
| corpus_fpn_multiscale | true | 1 | 1 | 1 | 1 |
| corpus_mask_rcnn_mask_branch | true | 1 | 1 | 1 | 1 |
| corpus_retinanet_focal_imbalance | true | 1 | 1 | 1 | 1 |
| corpus_ssd_single_network | true | 1 | 1 | 1 | 1 |


## Claims pilot

Артефакт: `eval/results/current-claims-pilot-suite.json`

| case_id | passed | claim_recall | claim_precision | expected_n | predicted_n |
| --- | --- | --- | --- | --- | --- |
| corpus_cascade_rcnn_stages | true | 1 | 1 | 1 | 1 |
| corpus_centernet_triplet | true | 1 | 1 | 1 | 1 |
| corpus_cornernet_keypoints | true | 1 | 1 | 1 | 1 |
| corpus_detr_set_prediction | true | 1 | 1 | 1 | 1 |
| corpus_efficientdet_compound | true | 1 | 1 | 1 | 1 |
| corpus_faster_rcnn_rpn_shared | true | 1 | 1 | 1 | 1 |
| corpus_fpn_multiscale | true | 1 | 1 | 1 | 1 |
| corpus_mask_rcnn_mask_branch | true | 1 | 1 | 1 | 1 |
| corpus_retinanet_focal_imbalance | true | 1 | 1 | 1 | 1 |
| corpus_ssd_single_network | true | 1 | 1 | 1 | 1 |


## References resolution contract

Артефакт: `eval/results/current-references-resolution-contract.json`

| case_id | passed | resolution_R | resolution_P | expected_n | predicted_n |
| --- | --- | --- | --- | --- | --- |
| refs_contract_shape | true | 1 | 1 | 0 | 1 |


## References resolution mini

Артефакт: `eval/results/current-references-resolution-mini.json`

| case_id | passed | resolution_R | resolution_P | expected_n | predicted_n |
| --- | --- | --- | --- | --- | --- |
| refs_mini_arxiv_id | true | 1 | 1 | 1 | 1 |
| refs_mini_doi_pair | true | 1 | 1 | 2 | 2 |
| refs_mini_work_id | true | 1 | 1 | 1 | 1 |
