# Dedup pack: methods_v1 (Layer 8 of Corpus Gold Pack v1)

**Дата:** 2026-04-25 · **Тип:** dedup gold (entity_type=method) для **BT11**.
**Статус:** `draft`. **Спека:** [`docs/specs/benchmark-gold-schemas-v1.md`](../../../../../docs/specs/benchmark-gold-schemas-v1.md) §9. **Шаблон:** [`../authors_v1/README.md`](../authors_v1/README.md).

## Содержание

25 records / 7 clusters / 6 negative_pairs.

### Кластеры (positive — same method, different surface)
| cluster_id | Variants | Notes |
|---|---|---|
| `cluster_rcnn` | R-CNN / Region-based CNN / RCNN | Hyphenation + expansion |
| `cluster_faster_rcnn` | Faster R-CNN / Faster RCNN | Hyphenation |
| `cluster_fpn` | FPN / Feature Pyramid Network / Feature Pyramid Networks | Acronym + singular/plural |
| `cluster_ssd` | SSD / Single Shot MultiBox Detector / Single Shot Detector | Acronym + 2 expansion forms |
| `cluster_detr` | DETR / DEtection TRansformer / Detection Transformer | Mixed-case original + normalized |
| `cluster_yolov1` | YOLOv1 / YOLO / You Only Look Once | Bare 'YOLO' (2016-era) → v1 |
| `cluster_focal_loss` | Focal Loss / focal loss | Case-only |

### Negative pairs (must NOT merge — самая важная категория для methods)
| pair_id | Pair | Why |
|---|---|---|
| `neg_rcnn_vs_fast_rcnn` | R-CNN ↔ Fast R-CNN | Разные методы/статьи (2014 vs 2015), substring совпадает |
| `neg_fast_rcnn_vs_faster_rcnn` | Fast R-CNN ↔ Faster R-CNN | Differ by single word ("Faster") |
| `neg_faster_rcnn_vs_mask_rcnn` | Faster R-CNN ↔ Mask R-CNN | Both end in "R-CNN" family но разные методы |
| `neg_yolov1_vs_yolov2` | YOLOv1 ↔ YOLOv2 | Version number — разные методы |
| `neg_yolov2_vs_yolo9000` | YOLOv2 ↔ YOLO9000 | Same paper, distinct variants (base vs joint-9000-class training) |
| `neg_focal_loss_vs_generalized_focal_loss` | Focal Loss ↔ Generalized Focal Loss | Different formulations (GFL adds continuous quality + distribution) |

### Главный design-принцип
**Substring overlap не достаточен** для merge. Pipeline должен использовать `introduced_in_corpus_work_id` как strong signal: разные `corpus_work_id` ⇒ почти всегда не merge (исключение — multi-paper extensions, e.g. R-CNN family chain не формирует cluster, формирует `extends` edges в `relations_v1.json`).

## TODO
- Добавить method-aliases для DETR family (Deformable DETR / Def-DETR / Deformable Transformer) — будет в Phase 3 (concept_v2).
- Добавить кейс TINY/NANO/Lite suffixes (YOLOv5-nano vs YOLOv5).
