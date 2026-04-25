# Corpus Catalog v1 (Layer 0 of Corpus Gold Pack v1)

**Дата:** 2026-04-25
**Статус:** `draft` — таблица собрана из `gold_enrichment_*.json` файлов layer1 фикстур; колонки `key_claims_summary`, `methods_referenced`, `cites_corpus_work_ids` заполнены частично (топ-10 papers); требуется LLM-dual-pass + human spot-check (см. [§4 plan](../../docs/analysis/corpus-gold-pack-v1-2026-04-25.md#4-llm-validated-workflow-валидация-без-ручной-разметки-каждого-кейса)).
**Спека:** [`docs/specs/benchmark-gold-schemas-v1.md`](../../docs/specs/benchmark-gold-schemas-v1.md) §1.1.
**Машиночитаемая копия:** `corpus_v1.json` (тот же набор полей, для runner'ов).

---

## 1. Inventory (35 papers)

| corpus_work_id | Title (short) | Year | Stage | Primary methods | Key authors | arxiv_id |
|----------------|---------------|------|-------|-----------------|-------------|----------|
| `yolov1` | You Only Look Once: Unified, Real-Time Object Detection | 2016 | one_stage | yolov1, darknet | Redmon, Divvala, Girshick, Farhadi | 1506.02640 |
| `yolov2_realpdf` | YOLO9000: Better, Faster, Stronger | 2016 | one_stage | yolov2, darknet19 | Redmon, Farhadi | 1612.08242 |
| `yolov3_realpdf` | YOLOv3: An Incremental Improvement | 2018 | one_stage | yolov3, darknet53, multi_scale_prediction | Redmon, Farhadi | 1804.02767 |
| `yolox_realpdf` | YOLOX: Exceeding YOLO Series in 2021 | 2021 | one_stage | yolox, decoupled_head, simota | Ge, Liu, Wang, Li, Sun | 2107.08430 |
| `rcnn_realpdf` | Rich feature hierarchies for accurate object detection (R-CNN) | 2014 | two_stage | rcnn, selective_search, svm_classifier | Girshick, Donahue, Darrell, Malik | 1311.2524 |
| `fast_rcnn_realpdf` | Fast R-CNN | 2015 | two_stage | fast_rcnn, roi_pooling | Girshick | 1504.08083 |
| `faster_rcnn_realpdf` | Faster R-CNN: Towards Real-Time Object Detection with RPN | 2016 | two_stage | faster_rcnn, region_proposal_network, anchor_boxes | Ren, He, Girshick, Sun | 1506.01497 |
| `mask_rcnn_realpdf` | Mask R-CNN | 2018 | two_stage | mask_rcnn, roi_align, instance_segmentation_branch | He, Gkioxari, Dollár, Girshick | 1703.06870 |
| `cascade_rcnn_realpdf` | Cascade R-CNN: Delving into High Quality Object Detection | 2017 | two_stage | cascade_rcnn, multi_stage_iou_thresholds | Cai, Vasconcelos | 1712.00726 |
| `libra_rcnn_realpdf` | Libra R-CNN: Towards Balanced Learning for Object Detection | 2019 | two_stage | libra_rcnn, balanced_l1_loss, balanced_feature_pyramid | Pang, Chen, Shi, Feng, Ouyang, Lin | 1904.02701 |
| `rfcn_realpdf` | R-FCN: Object Detection via Region-based Fully Convolutional Networks | 2016 | two_stage | rfcn, position_sensitive_score_maps | Dai, Li, He, Sun | 1605.06409 |
| `sppnet_realpdf` | Spatial Pyramid Pooling in Deep CNN for Visual Recognition | 2015 | two_stage | sppnet, spatial_pyramid_pooling | He, Zhang, Ren, Sun | 1406.4729 |
| `ssd_realpdf` | SSD: Single Shot MultiBox Detector | 2016 | one_stage | ssd, multibox, multi_scale_feature_maps | Liu, Anguelov, Erhan, Szegedy, Reed, Fu | 1512.02325 |
| `retinanet_focal_realpdf` | Focal Loss for Dense Object Detection (RetinaNet) | 2018 | one_stage | retinanet, focal_loss | Lin, Goyal, Girshick, He, Dollár | 1708.02002 |
| `fcos_realpdf` | FCOS: Fully Convolutional One-Stage Object Detection | 2019 | one_stage | fcos, anchor_free, centerness | Tian, Shen, Chen, He | 1904.01355 |
| `atss_realpdf` | Bridging the Gap Between Anchor-based and Anchor-free Detection | 2020 | one_stage | atss, adaptive_training_sample_selection | Zhang, Chi, Yao, Lei, Li | 1912.02424 |
| `gfl_realpdf` | Generalized Focal Loss: Learning Qualified and Distributed Bounding Boxes | 2020 | one_stage | gfl, generalized_focal_loss, distribution_focal_loss | Li, Wang, Wu, Chen, Hu, Li, Yang | 2006.04388 |
| `tood_realpdf` | TOOD: Task-aligned One-stage Object Detection | 2021 | one_stage | tood, task_aligned_head | Feng, Zhong, Cheng, Li, Yu | 2108.07755 |
| `cornernet_realpdf` | CornerNet: Detecting Objects as Paired Keypoints | 2019 | keypoint_based | cornernet, corner_pooling, keypoint_heatmaps | Law, Deng | 1808.01244 |
| `centernet_realpdf` | CenterNet: Keypoint Triplets for Object Detection | 2019 | keypoint_based | centernet, center_pooling, cascade_corner_pooling | Duan, Bai, Xie, Qi, Huang, Tian | 1904.08189 |
| `fpn_realpdf` | Feature Pyramid Networks for Object Detection | 2017 | enabling_module | fpn, feature_pyramid_network, top_down_pathway | Lin, Dollár, Girshick, He, Hariharan, Belongie | 1612.03144 |
| `efficientdet_realpdf` | EfficientDet: Scalable and Efficient Object Detection | 2020 | one_stage | efficientdet, bifpn, compound_scaling | Tan, Pang, Le | 1911.09070 |
| `detr_realpdf` | End-to-End Object Detection with Transformers (DETR) | 2020 | transformer | detr, set_prediction, bipartite_matching, transformer_decoder | Carion, Massa, Synnaeve, Usunier, Kirillov, Zagoruyko | 2005.12872 |
| `deformable_detr_realpdf` | Deformable DETR: Deformable Transformers for End-to-End Object Detection | 2021 | transformer | deformable_detr, deformable_attention | Zhu, Su, Lu, Li, Wang, Dai | 2010.04159 |
| `dn_detr_realpdf` | DN-DETR: Accelerate DETR Training by Introducing Query DeNoising | 2022 | transformer | dn_detr, query_denoising | Li, Zhang, Liu, Guo, Ni, Zhang | 2203.01305 |
| `dino_realpdf` | DINO: DETR with Improved DeNoising Anchor Boxes | 2022 | transformer | dino, contrastive_denoising, mixed_query_selection | Zhang, Li, Liu, Zhang, Su, Zhu | 2203.03605 |
| `detrs_realpdf` | DETRs Beat YOLOs on Real-time Object Detection (RT-DETR) | 2023 | transformer | rt_detr, hybrid_encoder, iou_aware_query_selection | Zhao, Lv, Xu, Wei, Wang, Dang, Liu | 2304.08069 |
| `overfeat_realpdf` | OverFeat: Integrated Recognition, Localization and Detection using CNN | 2014 | one_stage | overfeat, sliding_window, multi_scale_features | Sermanet, Eigen, Zhang, Mathieu, Fergus, LeCun | 1312.6229 |
| `selective_search_realpdf` | Selective Search for Object Recognition | 2012 | classical | selective_search, hierarchical_grouping | Uijlings, van de Sande, Gevers, Smeulders | — |
| `hog_human_detection_realpdf` | Histograms of Oriented Gradients for Human Detection | 2005 | classical | hog, sliding_window_svm | Dalal, Triggs | — |
| `part_based_models_realpdf` | Object Detection with Discriminatively Trained Part-Based Models (DPM) | 2010 | classical | dpm, deformable_parts, latent_svm | Felzenszwalb, Girshick, McAllester, Ramanan | — |
| `arxiv_refs_heavy` | Synthetic refs-heavy article (arXiv-style) | n/a | synthetic | — | — | — |
| `doi_refs_heavy` | Synthetic refs-heavy article (DOI-style) | n/a | synthetic | — | — | — |
| `noisy_layout_stub` | Synthetic noisy-layout PDF stub | n/a | synthetic | — | — | — |
| `ws_graph_contract` | Workspace graph contract stub | n/a | synthetic | — | — | — |

**Pilot subset (used in BT prep):** все, кроме synthetic-стабов.

---

## 2. Datasets canonical (used across the corpus)

| dataset_id | Canonical name | Aliases | Years/versions | Used by (count) |
|------------|----------------|---------|----------------|-----------------|
| `pascal_voc_2007` | PASCAL VOC 2007 | VOC07, VOC2007 | 2007 | yolov1, ssd, faster_rcnn, ... (~20) |
| `pascal_voc_2012` | PASCAL VOC 2012 | VOC12 | 2012 | yolov1, faster_rcnn, ssd, ... (~15) |
| `mscoco` | MS COCO | COCO, Microsoft COCO, COCO 2017 | 2014, 2017 | retinanet, mask_rcnn, detr, ... (~25) |
| `imagenet` | ImageNet (ILSVRC) | ILSVRC2012 | 2012 | overfeat, sppnet, ... (~10) |
| `kitti` | KITTI | — | 2012 | rfcn, ssd (varianty) |
| `lvis` | LVIS | — | 2019 | mask_rcnn followups |
| `objects365` | Objects365 | — | 2019 | dino, detrs |

---

## 3. Methods canonical (cross-paper)

Только методы, которые встречаются в ≥ 2 статьях корпуса (или являются базовыми — введены одной статьёй и упоминаются другими как baseline):

| method_id | Canonical name | Aliases | Introduced in | Referenced by |
|-----------|----------------|---------|---------------|---------------|
| `selective_search` | Selective Search | SS | selective_search_realpdf | rcnn, fast_rcnn |
| `region_proposal_network` | Region Proposal Network | RPN | faster_rcnn_realpdf | mask_rcnn, cascade_rcnn, libra_rcnn |
| `roi_pooling` | RoI Pooling | — | fast_rcnn_realpdf | faster_rcnn |
| `roi_align` | RoI Align | — | mask_rcnn_realpdf | cascade_rcnn followups |
| `feature_pyramid_network` | Feature Pyramid Network | FPN | fpn_realpdf | retinanet, mask_rcnn (FPN backbone), libra, fcos |
| `focal_loss` | Focal Loss | — | retinanet_focal_realpdf | atss, gfl, tood |
| `anchor_boxes` | Anchor boxes | predefined anchors | faster_rcnn_realpdf | ssd, retinanet, yolov2/v3 |
| `bipartite_matching` | Bipartite matching (Hungarian) | set_prediction | detr_realpdf | deformable_detr, dn_detr, dino, rt_detr |
| `nms` | Non-Maximum Suppression | NMS | many (classical) | almost all CNN detectors; explicitly avoided by DETR family |
| `iou_loss` | IoU loss | GIoU, DIoU, CIoU | unitbox/giou (outside corpus) | gfl, atss, dino |

---

## 4. Authors with multi-paper presence (anchor for dedup authors_v1)

| canonical_name | Variants seen in corpus | Papers |
|----------------|-------------------------|--------|
| Joseph Redmon | Joseph Redmon, J. Redmon | yolov1, yolov2, yolov3 |
| Ross Girshick | Ross Girshick, R. Girshick, Ross B. Girshick | rcnn, fast_rcnn, faster_rcnn, mask_rcnn, fpn, retinanet, yolov1 (co-author), part_based_models |
| Kaiming He | Kaiming He, K. He | sppnet, faster_rcnn, mask_rcnn, fpn, retinanet, rfcn |
| Jian Sun | Jian Sun, J. Sun | sppnet, faster_rcnn, rfcn, yolox |
| Ali Farhadi | Ali Farhadi | yolov1, yolov2, yolov3 |
| Tsung-Yi Lin | Tsung-Yi Lin | fpn, retinanet |
| Piotr Dollár | Piotr Dollár | fpn, retinanet, mask_rcnn |
| Shaoqing Ren | Shaoqing Ren, S. Ren | sppnet, faster_rcnn |
| Jifeng Dai | Jifeng Dai | rfcn, deformable_detr |
| Hao Zhang | Hao Zhang | dn_detr, dino |
| Feng Li | Feng Li | dn_detr, dino |
| Shilong Liu | Shilong Liu | dn_detr, dino |
| Lei Zhang | Lei Zhang | dn_detr, dino |

---

## 5. Institutions canonical (anchor for dedup institutions_v1)

| canonical_name | Aliases in corpus | Notes |
|----------------|-------------------|-------|
| University of Washington | UW | Redmon, Divvala, Farhadi |
| Allen Institute for AI | AI2 | Divvala, Farhadi |
| Facebook AI Research | FAIR, Facebook AI | Girshick (later affiliation), DETR team |
| Microsoft Research | MSR, Visual Computing Group / Microsoft Research | Faster R-CNN, R-FCN, SPPNet authors |
| Microsoft Research Asia | MSRA | overlapping with MSR; **NOT same** (negative pair candidate) |
| Carnegie Mellon University | CMU | — |
| University of Adelaide | — | FCOS team |
| MEGVII Technology | Megvii | YOLOX, ATSS-related |

---

## 6. Known cross-paper relations (Layer 9 contradictions seed)

| pair | type |
|------|------|
| faster_rcnn_realpdf vs retinanet_focal_realpdf | era_shift (two-stage accuracy premise vs one-stage with focal loss matches) |
| faster_rcnn_realpdf vs fcos_realpdf | design_paradigm (anchor-based necessity vs anchor-free sufficient) |
| faster_rcnn_realpdf vs cornernet_realpdf | design_paradigm (region proposal vs keypoint detection) |
| {many CNN detectors} vs detr_realpdf | post_processing (NMS required vs set prediction) |
| rcnn_realpdf vs faster_rcnn_realpdf | architectural (external proposals vs RPN integrated) |
| hog_human_detection_realpdf vs rcnn_realpdf | classical_vs_deep (handcrafted features vs learned CNN features) |
| {ResNet-deep detectors} vs efficientdet_realpdf | scaling (depth vs compound scaling) |

---

## 7. Validation TODO (для следующей фазы)

- [ ] Заполнить `key_claims_summary[]` (3–5 на статью) для каждой из 31 не-synthetic работ — это вход для Layer 1 (Claims gold v2).
- [ ] Расширить `methods_referenced[]` (что цитируется как baseline) — вход для Layer 4 (multihop) и Layer 9 (contradictions).
- [ ] Проверить `datasets_canonical[]` для каждой работы (таблица §2 — кратко; нужна привязка work → dataset_ids).
- [ ] Двойной LLM-pass (extractor A + B) на §1, заполнить `consistency_report.json`.
- [ ] Spot-check disagreements.
- [ ] Зафиксировать `meta.validation_status: "human_spot_checked"`.
