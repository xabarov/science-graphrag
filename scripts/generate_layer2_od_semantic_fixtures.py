#!/usr/bin/env python3
"""
Create layer-2 semantic_gold.json fixtures for the object-detection corpus.

Each fixture references layer1/article.md via article_path and uses conservative
normalized method/dataset names for nightly_semantic runs (allow_empty_when_no_llm).

Usage (repo root):
  .venv/bin/python scripts/generate_layer2_od_semantic_fixtures.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAYER2 = ROOT / "tests" / "fixtures" / "benchmarks" / "layer2"

# layer1_case_id -> (semantic_case_id, methods[], datasets[])
OD_SEMANTIC: dict[str, tuple[str, list[str], list[str]]] = {
    "atss_realpdf": ("atss_semantic", ["atss", "adaptive training sample selection"], ["coco"]),
    "cascade_rcnn_realpdf": (
        "cascade_rcnn_semantic",
        ["cascade r-cnn", "cascade rcnn"],
        ["coco"],
    ),
    "centernet_realpdf": ("centernet_semantic", ["centernet", "keypoint triplets"], ["coco"]),
    "cornernet_realpdf": ("cornernet_semantic", ["cornernet", "corner pooling"], ["coco"]),
    "deformable_detr_realpdf": (
        "deformable_detr_semantic",
        ["deformable detr", "deformable transformer"],
        ["coco"],
    ),
    "detr_realpdf": ("detr_semantic", ["detr", "transformer", "object detection"], ["coco"]),
    "detrs_realpdf": ("detrs_semantic", ["detr", "real-time"], ["coco"]),
    "dino_realpdf": ("dino_semantic", ["dino", "denoising", "detr"], ["coco"]),
    "dn_detr_realpdf": ("dn_detr_semantic", ["dn-detr", "query denoising"], ["coco"]),
    "efficientdet_realpdf": ("efficientdet_semantic", ["efficientdet", "efficientdet-d"], ["coco"]),
    "fast_rcnn_realpdf": ("fast_rcnn_semantic", ["fast r-cnn", "fast rcnn"], ["voc", "coco"]),
    "faster_rcnn_realpdf": (
        "faster_rcnn_semantic",
        ["faster r-cnn", "faster rcnn", "rpn"],
        ["coco", "voc"],
    ),
    "fcos_realpdf": ("fcos_semantic", ["fcos", "fully convolutional"], ["coco"]),
    "fpn_realpdf": ("fpn_semantic", ["fpn", "feature pyramid"], ["coco"]),
    "gfl_realpdf": ("gfl_semantic", ["gfl", "generalized focal loss", "focal loss"], ["coco"]),
    "hog_human_detection_realpdf": (
        "hog_semantic",
        ["histogram of oriented gradients", "hog", "human detection"],
        ["inria"],
    ),
    "libra_rcnn_realpdf": (
        "libra_rcnn_semantic",
        ["libra r-cnn", "libra rcnn", "balanced learning"],
        ["coco"],
    ),
    "mask_rcnn_realpdf": (
        "mask_rcnn_semantic",
        ["mask r-cnn", "mask rcnn", "instance segmentation"],
        ["coco"],
    ),
    "overfeat_realpdf": ("overfeat_semantic", ["overfeat", "convnet"], ["imagenet"]),
    "part_based_models_realpdf": (
        "part_based_models_semantic",
        ["deformable part", "latent svm", "object detection"],
        ["pascal voc", "voc"],
    ),
    "rcnn_realpdf": ("rcnn_semantic", ["r-cnn", "rcnn", "selective search"], ["imagenet", "voc"]),
    "retinanet_focal_realpdf": (
        "retinanet_semantic",
        ["focal loss", "retinanet"],
        ["coco", "pascal"],
    ),
    "rfcn_realpdf": ("rfcn_semantic", ["r-fcn", "position-sensitive", "fcn"], ["coco"]),
    "selective_search_realpdf": (
        "selective_search_semantic",
        ["selective search", "object recognition"],
        ["voc"],
    ),
    "sppnet_realpdf": (
        "sppnet_semantic",
        ["spp-net", "spatial pyramid pooling", "sppnet"],
        ["imagenet", "voc"],
    ),
    "ssd_realpdf": ("ssd_semantic", ["ssd", "single shot", "multibox"], ["coco", "voc"]),
    "tood_realpdf": ("tood_semantic", ["tood", "task-aligned", "one-stage"], ["coco"]),
    "yolov1": ("yolov1_semantic", ["yolo", "you only look once"], ["pascal voc", "imagenet"]),
    "yolov2_realpdf": ("yolov2_semantic", ["yolo9000", "yolo", "darknet"], ["coco", "imagenet"]),
    "yolov3_realpdf": ("yolov3_semantic", ["yolov3", "yolo"], ["coco"]),
    "yolox_realpdf": ("yolox_semantic", ["yolox", "yolo"], ["coco"]),
}


def main() -> int:
    """Write semantic_gold.json for each object-detection layer1 case."""

    LAYER2.mkdir(parents=True, exist_ok=True)
    for layer1_id, (case_id, methods, datasets) in OD_SEMANTIC.items():
        l1 = ROOT / "tests" / "fixtures" / "benchmarks" / "layer1" / layer1_id
        if not (l1 / "article.md").is_file():
            print(f"skip missing layer1: {layer1_id}")
            continue
        out_dir = LAYER2 / case_id
        out_dir.mkdir(parents=True, exist_ok=True)
        rel = Path("../../layer1") / layer1_id / "article.md"
        desc = f"Object-detection corpus; layer1={layer1_id}. " "Nightly semantic when LLM enabled."
        spec = {
            "case_id": case_id,
            "schema_version": 1,
            "description": desc,
            "article_path": str(rel.as_posix()),
            "min_method_names": 1,
            "expected_method_names_normalized": methods,
            "expected_dataset_names_normalized": datasets,
            "allow_empty_when_no_llm": True,
        }
        # RetinaNet fixture keeps optional strict ratios in existing file — preserve if present
        existing = out_dir / "semantic_gold.json"
        if existing.is_file() and case_id == "retinanet_semantic":
            old = json.loads(existing.read_text(encoding="utf-8"))
            spec["min_method_recall_ratio"] = old.get("min_method_recall_ratio", 1.0)
            spec["min_dataset_recall_ratio"] = old.get("min_dataset_recall_ratio", 0.5)
        (out_dir / "semantic_gold.json").write_text(
            json.dumps(spec, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {case_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
