# Dedup pack: datasets_v1 (Layer 8 of Corpus Gold Pack v1)

**Дата:** 2026-04-25 · **Тип:** dedup gold (entity_type=dataset) для **BT11**.
**Статус:** `draft`. **Спека:** [`docs/specs/benchmark-gold-schemas-v1.md`](../../../../../docs/specs/benchmark-gold-schemas-v1.md) §9. **Шаблон:** [`../authors_v1/README.md`](../authors_v1/README.md).

## Содержание

21 records / 6 clusters / 5 negative_pairs.

### Кластеры (positive)
| cluster_id | Variants | Notes |
|---|---|---|
| `cluster_voc_2007` | PASCAL Visual Object Classes 2007 / PASCAL VOC 2007 / VOC2007 / VOC07 | 4 surface формы одной версии |
| `cluster_voc_2012` | PASCAL VOC 2012 / VOC2012 | |
| `cluster_mscoco_generic` | Microsoft COCO / MS COCO / COCO | Generic (без version); когда версия указана — distinct |
| `cluster_imagenet_full` | ImageNet / Imagenet | Capitalization |
| `cluster_ilsvrc_generic` | ImageNet Large Scale Visual Recognition Challenge / ILSVRC | Generic challenge name |
| `cluster_objects365` | Objects365 / Objects 365 | Whitespace |

### Negative pairs (must NOT merge — version-sensitive)
| pair_id | Pair | Why |
|---|---|---|
| `neg_voc_2007_vs_2012` | **VOC 2007 ↔ VOC 2012** | Разные splits/версии; numbers не сопоставимы |
| `neg_coco_2014_vs_2017` | **COCO 2014 ↔ COCO 2017** | Разные annotation revisions, train/val splits |
| `neg_imagenet_vs_ilsvrc_2013` | ImageNet ↔ ILSVRC 2013 | Generic ImageNet ≠ specific year ILSVRC 2013 (разный class set) |
| `neg_imagenet_classification_vs_lvis_segmentation` | ImageNet ↔ LVIS | Sanity-check на «entity_type=dataset» совпадение |
| `neg_kitti_vs_voc_2007` | KITTI ↔ VOC 2007 | Different domains |

### Главный design-принцип
**`version` в `context_attributes` — primary disambiguator.** Generic ↔ versioned различить можно через `version: "any"` vs `version: "2014"`; pipeline должен:
- Generic ↔ generic (например, "COCO" ↔ "MS COCO") — **merge**.
- Generic ↔ versioned ("COCO" ↔ "COCO 2017") — **soft link** (можно агрегировать в reporting, но не считать «той же сущностью» для citation accuracy).
- Versioned ↔ versioned разных лет — **never merge**.

## TODO
- Добавить subset-нотации (COCO val5k, COCO trainval35k, COCO test-dev) — это часть version namespace.
- ScanNet / S3DIS / nuScenes — для расширения broader-corpus pack v2.
