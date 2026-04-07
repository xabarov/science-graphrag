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

Политика статусов:
- `reviewed`: статья вручную сверена по источнику
- `fixed`: `gold_teacher.json` обновлён
- `needs_followup`: нужен отдельный policy decision, например по `publication_year`

## Сводка по фазам

| Phase | Cases | Goal | Status |
|------|------:|------|--------|
| `Phase 1` | 5 | early CV detectors / first quality pass | `completed` |
| `Phase 2` | 5 | DETR family pass | `completed` |
| `Phase 3` | 5 | two-stage / FPN family pass | `in_progress` |
| `Phase 4` | 5 | Mask/RCNN/classic pass | `todo` |
| `Phase 5` | 5 | reference-count / anchor-era pass | `todo` |
| `Phase 6` | 5 | YOLO / SSD / late cleanup | `in_progress` |

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
| `fast_rcnn_realpdf` | [ ] | [ ] | [ ] |  |
| `faster_rcnn_realpdf` | [x] | [ ] | [x] | Проверено по `article.md` и arXiv. Teacher gold выглядит качественно; open question только по policy для `publication_year=2016`. |
| `fcos_realpdf` | [ ] | [ ] | [ ] |  |
| `fpn_realpdf` | [ ] | [ ] | [ ] |  |
| `gfl_realpdf` | [ ] | [ ] | [ ] |  |

## Phase 4

| Case | Reviewed | Fixed | Needs follow-up | Notes |
|------|----------|-------|-----------------|-------|
| `hog_human_detection_realpdf` | [ ] | [ ] | [ ] |  |
| `libra_rcnn_realpdf` | [ ] | [ ] | [ ] |  |
| `mask_rcnn_realpdf` | [ ] | [ ] | [ ] |  |
| `overfeat_realpdf` | [ ] | [ ] | [ ] |  |
| `part_based_models_realpdf` | [ ] | [ ] | [ ] |  |

## Phase 5

| Case | Reviewed | Fixed | Needs follow-up | Notes |
|------|----------|-------|-----------------|-------|
| `rcnn_realpdf` | [ ] | [ ] | [ ] |  |
| `retinanet_focal_realpdf` | [ ] | [ ] | [ ] |  |
| `rfcn_realpdf` | [ ] | [ ] | [ ] |  |
| `selective_search_realpdf` | [ ] | [ ] | [ ] |  |
| `sppnet_realpdf` | [ ] | [ ] | [ ] |  |

## Phase 6

| Case | Reviewed | Fixed | Needs follow-up | Notes |
|------|----------|-------|-----------------|-------|
| `ssd_realpdf` | [ ] | [ ] | [ ] |  |
| `tood_realpdf` | [ ] | [ ] | [ ] |  |
| `yolov2_realpdf` | [x] | [x] | [x] | Проверено по `article.md` и arXiv. Teacher gold корректен по авторам, добавлен `arxiv_id=1612.08242`; `publication_year` требует общей policy. |
| `yolov3_realpdf` | [ ] | [ ] | [ ] |  |
| `yolox_realpdf` | [ ] | [ ] | [ ] |  |

## Decision Log

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
