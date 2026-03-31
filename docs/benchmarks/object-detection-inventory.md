# Инвентарь PDF: object-detection corpus

Локальная папка: `/home/roman/Documents/ML/CV/object-detection` (PDF не в git).

Соответствие **файл PDF → `case_id` → тир** (real-PDF кейсы в `nightly_heavy`, кроме отмеченных):

| PDF filename | `case_id` | Тир |
|--------------|-----------|-----|
| ATSS.pdf | `atss_realpdf` | nightly_heavy |
| Cascade R-CNN.pdf | `cascade_rcnn_realpdf` | nightly_heavy |
| CenterNet.pdf | `centernet_realpdf` | nightly_heavy |
| CornerNet.pdf | `cornernet_realpdf` | nightly_heavy |
| Deformable DETR.pdf | `deformable_detr_realpdf` | nightly_heavy |
| DETR.pdf | `detr_realpdf` | nightly_heavy |
| DETRs.pdf | `detrs_realpdf` | nightly_heavy |
| DINO.pdf | `dino_realpdf` | nightly_heavy |
| DN-DETR.pdf | `dn_detr_realpdf` | nightly_heavy |
| EfficientDet.pdf | `efficientdet_realpdf` | nightly_heavy |
| Faster R-CNN.pdf | `faster_rcnn_realpdf` | nightly_heavy |
| Fast R-CNN.pdf | `fast_rcnn_realpdf` | nightly_heavy |
| FCOS.pdf | `fcos_realpdf` | nightly_heavy |
| FPN.pdf | `fpn_realpdf` | nightly_heavy |
| GFL.pdf | `gfl_realpdf` | nightly_heavy |
| Histograms of Oriented Gradients for Human Detection.pdf | `hog_human_detection_realpdf` | nightly_heavy |
| Libra R-CNN.pdf | `libra_rcnn_realpdf` | nightly_heavy |
| Mask R-CNN.pdf | `mask_rcnn_realpdf` | nightly_heavy |
| Object Detection with Discriminatively Trained Part-Based Models.pdf | `part_based_models_realpdf` | nightly_heavy |
| OverFeat.pdf | `overfeat_realpdf` | nightly_heavy |
| R-CNN.pdf | `rcnn_realpdf` | nightly_heavy |
| RetinaNet.pdf | `retinanet_focal_realpdf` | nightly_heavy |
| R-FCN.pdf | `rfcn_realpdf` | nightly_heavy |
| Selective Search for Object Recognition.pdf | `selective_search_realpdf` | nightly_heavy |
| SPPNet.pdf | `sppnet_realpdf` | nightly_heavy |
| SSD.pdf | `ssd_realpdf` | nightly_heavy |
| TOOD.pdf | `tood_realpdf` | nightly_heavy |
| YOLOv1.pdf | `yolov1` | merge_safe |
| YOLOv2.pdf | `yolov2_realpdf` | nightly_heavy |
| YOLOv3.pdf | `yolov3_realpdf` | nightly_heavy |
| YOLOX.pdf | `yolox_realpdf` | nightly_heavy |

Генерация: `scripts/build_od_corpus_fixtures.py` (или по одному `scripts/build_real_pdf_layer1_fixture.py`).
