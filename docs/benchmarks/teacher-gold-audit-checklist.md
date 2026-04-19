# Teacher-Gold Audit Checklist

Дата запуска: `2026-04-07`

Цель:
- провести ручной QA для `eval/teacher_gold/layer1/`
- фиксировать, какие статьи уже проверены по оригиналу
- отделять статус `проверено` от статуса `исправлено`
- выполнять ревизию небольшими батчами по 5 кейсов за фазу

Источники проверки:
- локальный fixture статьи: `tests/fixtures/benchmarks/layer1/<case_id>/article.md`
- текущий teacher gold: `eval/teacher_gold/layer1/<case_id>/gold_teacher.json`
- curated gold для сравнения: `tests/fixtures/benchmarks/layer1/<case_id>/gold.json`
- при необходимости внешний источник: arXiv / publisher page / DBLP

## Правила ревизии

Проверять в таком порядке:
1. `title`
2. `authors`
3. `affiliations`
4. `arxiv_id`
5. `publication_year`
6. `abstract_prefix`
7. `work_type`
8. явные артефакты в references / sample ids

Минимально безопасные правки:
- добавление отсутствующего `arxiv_id`, если он явно виден в статье или на arXiv
- исправление усечённого author name
- исправление явного mojibake / Unicode artifact
- исправление `publication_year`, только если источник и политика года не вызывают сомнений

## Policy: `publication_year` (arXiv-heavy corpus)

1. **Primary source order:** prefer the year printed on the PDF title block / arXiv stamp that matches `article.md` for the fixture; if venue (CVPR/NeurIPS) is confirmed via DOI or publisher page and differs by ±1 from arXiv, **prefer venue year** and record the rationale in Notes.
2. **Ambiguous preprint vs camera-ready:** keep `needs_followup` until venue or arXiv page is checked; do not “guess” from ingestion heuristics alone.
3. **Benchmark scoring:** student runs must not fail solely on `publication_year` deltas that are still under `needs_followup` in this checklist — treat as **policy debt**, not extraction regression, until the row is closed.
4. **Teacher refresh:** when regenerating `gold_teacher.json`, carry forward the agreed year for the case; if the model changes the year vs a closed row, triage as **teacher drift** (regenerate with pinned profile or fix post-process).

Политика статусов:
- `reviewed`: статья вручную сверена по источнику
- `fixed`: `gold_teacher.json` обновлён
- `needs_followup`: нужен отдельный policy decision, например по `publication_year`

## Сводка по фазам

| Phase | Cases | Goal | Status |
|------|------:|------|--------|
| `Phase 1` | 5 | early CV detectors / first quality pass | `completed` |
| `Phase 2` | 5 | DETR family pass | `completed` |
| `Phase 3` | 5 | two-stage / FPN family pass | `triaged` — publication_year policy set; row backlog below |
| `Phase 4` | 5 | Mask/RCNN/classic pass | `triaged` |
| `Phase 5` | 5 | reference-count / anchor-era pass | `triaged` |
| `Phase 6` | 5 | YOLO / SSD / late cleanup | `triaged` — publication_year policy set; row backlog below |

## Prioritized suspect backlog (Phase 3-6)

Один исход на строку: `fixture_refresh` (локальный `article.md`/PDF), `teacher_refresh` (регенерация `gold_teacher.json`), `extractor_regression`, `acceptable_tolerance`, `pending_manual_review`.

| Priority | Case | Outcome | Next action |
|----------|------|---------|-------------|
| P1 | `cascade_rcnn_realpdf` | `fixture_refresh` | Расхождение авторов: сверить локальный `article.md` с arXiv; исправить fixture source до правок teacher. |
| P1 | `faster_rcnn_realpdf` | `pending_manual_review` | Закрыть `publication_year=2016` по policy § выше (venue vs arXiv). |
| P2 | `fast_rcnn_realpdf` | `pending_manual_review` | Ручная сверка Phase 3 batch. |
| P2 | `fcos_realpdf` | `pending_manual_review` | Ручная сверка Phase 3 batch. |
| P2 | `fpn_realpdf` | `pending_manual_review` | Ручная сверка Phase 3 batch. |
| P2 | `gfl_realpdf` | `pending_manual_review` | Ручная сверка Phase 3 batch. |
| P2 | `hog_human_detection_realpdf` | `pending_manual_review` | Phase 4 batch. |
| P2 | `libra_rcnn_realpdf` | `pending_manual_review` | Phase 4 batch. |
| P2 | `mask_rcnn_realpdf` | `pending_manual_review` | Phase 4 batch. |
| P2 | `overfeat_realpdf` | `pending_manual_review` | Phase 4 batch. |
| P2 | `part_based_models_realpdf` | `pending_manual_review` | Phase 4 batch. |
| P2 | `rcnn_realpdf` | `pending_manual_review` | Phase 5 batch. |
| P2 | `retinanet_focal_realpdf` | `pending_manual_review` | Phase 5 batch. |
| P2 | `rfcn_realpdf` | `pending_manual_review` | Phase 5 batch. |
| P2 | `selective_search_realpdf` | `pending_manual_review` | Phase 5 batch. |
| P2 | `sppnet_realpdf` | `pending_manual_review` | Phase 5 batch. |
| P2 | `ssd_realpdf` | `pending_manual_review` | Phase 6 batch. |
| P2 | `tood_realpdf` | `pending_manual_review` | Phase 6 batch. |
| P2 | `yolov3_realpdf` | `pending_manual_review` | Phase 6 batch. |
| P2 | `yolox_realpdf` | `pending_manual_review` | Phase 6 batch. |
| P3 | `yolov1_semantic` (layer2) | `pending_manual_review` | Diff `semantic_gold_teacher.json` vs последний UI run / curated `semantic_gold.json` для того же `case_id`. |

## Phase 1

| Case | Reviewed | Fixed | Needs follow-up | Notes |
|------|----------|-------|-----------------|-------|
| `atss_realpdf` | [x] | [x] | [x] | Проверено по `article.md` и arXiv. Teacher gold был лучше curated gold по авторам, добавлен `arxiv_id=1912.02424`; `publication_year` оставлен до общей policy. |
| `cascade_rcnn_realpdf` | [x] | [ ] | [x] | Проверено по `article.md` и arXiv. Teacher gold согласован с локальным fixture, но внешний arXiv указывает второго автора `Nuno Vasconcelos`; нужен follow-up по source fixture vs benchmark truth. |
| `centernet_realpdf` | [x] | [x] | [x] | Проверено по `article.md` и внешнему источнику. Teacher gold по авторам выглядит корректно, добавлен `arxiv_id=1904.08189`; `publication_year` оставлен до общей policy. |
| `cornernet_realpdf` | [x] | [x] | [x] | Проверено по `article.md` и arXiv. Teacher gold сильнее curated gold, добавлен `arxiv_id=1808.01244`; `publication_year` требует общей policy. |
| `deformable_detr_realpdf` | [x] | [ ] | [ ] | Проверено по `article.md` и arXiv. Teacher gold выглядит качественно: `arxiv_id`, авторы, affiliations и venue уже согласованы с источником. |

## Phase 2

| Case | Reviewed | Fixed | Needs follow-up | Notes |
|------|----------|-------|-----------------|-------|
| `detr_realpdf` | [x] | [x] | [x] | Проверено по `article.md` и arXiv. Teacher gold корректен по авторам и abstract, добавлен `arxiv_id=2005.12872`; `publication_year` оставлен до общей policy. |
| `detrs_realpdf` | [x] | [x] | [x] | Проверено по teacher gold и внешнему arXiv/CVPR источнику. Добавлен `arxiv_id=2304.08069`; локальный `article.md` требует отдельной проверки, так как read вернул некорректный формат. |
| `dino_realpdf` | [x] | [x] | [x] | Проверено по `article.md` и arXiv. Teacher gold по авторам выглядит согласованным, добавлен `arxiv_id=2203.03605`; `publication_year` оставлен до общей policy. |
| `dn_detr_realpdf` | [x] | [ ] | [ ] | Проверено по `article.md` и arXiv. Teacher gold уже согласован по `arxiv_id`, авторам и venue; safe fixes не требуются. |
| `efficientdet_realpdf` | [x] | [x] | [x] | Проверено по `article.md` и arXiv. Teacher gold корректен по авторам, добавлен `arxiv_id=1911.09070`; `publication_year` и venue можно обсудить отдельно, если захотим нормализовать corpus-wide. |

## Phase 3

| Case | Reviewed | Fixed | Needs follow-up | Notes |
|------|----------|-------|-----------------|-------|
| `fast_rcnn_realpdf` | [ ] | [ ] | [ ] | См. приоритетный backlog (P2). |
| `faster_rcnn_realpdf` | [x] | [ ] | [x] | Проверено по `article.md` и arXiv. Teacher gold выглядит качественно; `publication_year` — policy § выше. |
| `fcos_realpdf` | [ ] | [ ] | [ ] | См. приоритетный backlog (P2). |
| `fpn_realpdf` | [ ] | [ ] | [ ] | См. приоритетный backlog (P2). |
| `gfl_realpdf` | [ ] | [ ] | [ ] | См. приоритетный backlog (P2). |

## Phase 4

| Case | Reviewed | Fixed | Needs follow-up | Notes |
|------|----------|-------|-----------------|-------|
| `hog_human_detection_realpdf` | [ ] | [ ] | [ ] | См. приоритетный backlog (P2). |
| `libra_rcnn_realpdf` | [ ] | [ ] | [ ] | См. приоритетный backlog (P2). |
| `mask_rcnn_realpdf` | [ ] | [ ] | [ ] | См. приоритетный backlog (P2). |
| `overfeat_realpdf` | [ ] | [ ] | [ ] | См. приоритетный backlog (P2). |
| `part_based_models_realpdf` | [ ] | [ ] | [ ] | См. приоритетный backlog (P2). |

## Phase 5

| Case | Reviewed | Fixed | Needs follow-up | Notes |
|------|----------|-------|-----------------|-------|
| `rcnn_realpdf` | [ ] | [ ] | [ ] | См. приоритетный backlog (P2). |
| `retinanet_focal_realpdf` | [ ] | [ ] | [ ] | См. приоритетный backlog (P2). |
| `rfcn_realpdf` | [ ] | [ ] | [ ] | См. приоритетный backlog (P2). |
| `selective_search_realpdf` | [ ] | [ ] | [ ] | См. приоритетный backlog (P2). |
| `sppnet_realpdf` | [ ] | [ ] | [ ] | См. приоритетный backlog (P2). |

## Phase 6

| Case | Reviewed | Fixed | Needs follow-up | Notes |
|------|----------|-------|-----------------|-------|
| `ssd_realpdf` | [ ] | [ ] | [ ] | См. приоритетный backlog (P2). |
| `tood_realpdf` | [ ] | [ ] | [ ] | См. приоритетный backlog (P2). |
| `yolov2_realpdf` | [x] | [x] | [x] | Проверено по `article.md` и arXiv. Teacher gold корректен по авторам, добавлен `arxiv_id=1612.08242`; `publication_year` — policy § выше. |
| `yolov3_realpdf` | [ ] | [ ] | [ ] | См. приоритетный backlog (P2). |
| `yolox_realpdf` | [ ] | [ ] | [ ] | См. приоритетный backlog (P2). |

## Layer 2 (`eval/teacher_gold/layer2/`)

| Case / suite | Reviewed | Fixed | Needs follow-up | Notes |
|--------------|----------|-------|-----------------|-------|
| `no_llm_smoke` | [x] | [ ] | [ ] | Merge-safe semantic stub; teacher slot optional — diff vs curated `semantic_gold.json` when triaging UI runs. |
| `yolov1_semantic` | [ ] | [ ] | [ ] | Compare `semantic_gold_teacher.json` to latest `data/benchmark_runs/*.json` (or `/v1/benchmark/runs/{id}` export) for same `case_id`; см. backlog P3. |
| **Policy** | — | — | — | Regenerate teacher fixtures via `scripts/generate_semantic_teacher_fixtures.py` after prompt/model profile change; record model id in commit message. |

## Audit exit (Wave E1)

| Criterion | Status |
|-----------|--------|
| Inventory + diff procedure documented | **CLOSED** — this file + [teacher-gold-audit-v1.md](teacher-gold-audit-v1.md) |
| Prioritized suspect list | **CLOSED** — единая очередь: [Prioritized suspect backlog](#prioritized-suspect-backlog-phase-3-6) |
| Remediation path agreed | **CLOSED** — safe fixes = confirmed `arxiv_id` / hygiene; policy items = `needs_followup` |
| `publication_year` policy | **CLOSED** — см. раздел *Policy: `publication_year`* выше |

## Decision Log

### 2026-04-19

- Закрыт **Audit exit** для Wave E1: приоритетный backlog вынесен в единую таблицу; политика `publication_year` зафиксирована в этом файле; layer-2 triage остаётся в очереди (P3).
- Remediation / provenance для teacher refresh синхронизированы с `eval/README.md` и docstring’ами скриптов генерации.

### 2026-04-07
- Создан фазовый чеклист аудита `teacher_gold`.
- Первично вручную сверены `cornernet_realpdf`, `faster_rcnn_realpdf`, `yolov2_realpdf`.
- Повторяющийся паттерн: teacher gold часто лучше curated gold по authors / abstract, но остаются пропуски в `arxiv_id`.
- Отдельный policy вопрос: как именно фиксируем `publication_year` для arXiv-heavy корпуса.
- `Phase 1` завершена: вручную проверены `atss_realpdf`, `cascade_rcnn_realpdf`, `centernet_realpdf`, `cornernet_realpdf`, `deformable_detr_realpdf`.
- Safe fixes применены в `teacher_gold` для `atss_realpdf`, `centernet_realpdf`, `cornernet_realpdf` и ранее проверенного `yolov2_realpdf`: добавлены подтверждённые `arxiv_id`.
- Выявлен источник follow-up для `cascade_rcnn_realpdf`: расхождение между локальным `article.md` и внешним arXiv по составу авторов.
- `Phase 2` завершена: вручную проверены `detr_realpdf`, `detrs_realpdf`, `dino_realpdf`, `dn_detr_realpdf`, `efficientdet_realpdf`.
- Safe fixes применены в `teacher_gold` для `detr_realpdf`, `detrs_realpdf`, `dino_realpdf`, `efficientdet_realpdf`: добавлены подтверждённые `arxiv_id`.
- `dn_detr_realpdf` подтверждён без изменений: текущий teacher gold уже выглядит консистентным.
- По `cascade_rcnn_realpdf` внешний источник подтвердил, что paper действительно имеет двух авторов: `Zhaowei Cai` и `Nuno Vasconcelos`; это похоже на дефект локального fixture/article source, а не только teacher-gold extraction.
