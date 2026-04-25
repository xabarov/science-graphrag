# Claims gold v1 — holdout pack (Layer 1 of Corpus Gold Pack v1)

**Дата:** 2026-04-25 · **Тип:** claims gold holdout для **BT6** (weekly cron).
**Статус:** `draft`. **Спека:** [`docs/specs/benchmark-gold-schemas-v1.md`](../../../../docs/specs/benchmark-gold-schemas-v1.md) §2.2.

## Зачем holdout отдельно от pilot

`pilot_v2` используется для итеративной отладки runner'а BT6. **Чтобы не получить overfitting под pilot и phantom-зелёный judge**, holdout содержит **5 статей, которые не пересекаются с pilot**. Прогон tier `claims_holdout_v1` запускается weekly cron (см. acceptance Phase 2 в `docs/backlog/refactor-backend.md`).

## Состав

5 статей × 4–5 claims = **20 claims** в holdout.

| dir | corpus_work_id | claims | polarity (neg/pos) | примечание |
|---|---|---|---|---|
| `holdout_atss_v1` | atss_realpdf | 4 | 1 / 3 | label-assignment-finding, ATSS-method, retinanet-matches-fcos-perf, arch-no-advantage-neg |
| `holdout_yolov3_v1` | yolov3_realpdf | 4 | 1 / 3 | three-scale, logistic-classifier, vs-RetinaNet, strict-IoU-neg |
| `holdout_yolox_v1` | yolox_realpdf | 4 | 1 / 3 | decoupled-head, anchor-free-simota, 50AP-V100, coupled-conflict-neg |
| `holdout_dino_v1` | dino_realpdf | 5 | 2 / 3 | three-components, 63AP-Swin-L, scaling-finding, earlier-DETR-neg, classical-pipelines-neg |
| `holdout_deformable_detr_v1` | deformable_detr_realpdf | 4 | 1 / 3 | deformable-attention, 10x-faster-conv, multi-scale-finding, global-attn-neg |

## Изоляция от pilot

Pilot содержит: yolov1, faster_rcnn, retinanet_focal, ssd, mask_rcnn, fpn, centernet, cornernet, detr, cascade_rcnn, efficientdet, fast_rcnn, rcnn, yolov2, fcos.

Holdout содержит: atss, yolov3, yolox, dino, deformable_detr.

Пересечения: **0** (по `corpus_work_id`).

Дополнительно: `distractor_strategy.neighbor_corpus_work_ids` в holdout кейсах могут ссылаться на pilot работы — это **OK**, потому что pilot статьи к этому моменту уже проиндексированы как corpus, и distractors берут из них реальные paragraphs (не из их claim gold).

## Acceptance (см. backlog Phase 2)

5 holdout-кейсов прогоняются weekly cron — для этого нужен tier `claims_holdout_v1` в `case_tiers.json` и runner pass-through (без специального gating).

## Связи

- Pilot: [`README_v2_pilot.md`](README_v2_pilot.md).
- План: [`docs/analysis/corpus-gold-pack-v1-2026-04-25.md`](../../../../docs/analysis/corpus-gold-pack-v1-2026-04-25.md) §3.2.
