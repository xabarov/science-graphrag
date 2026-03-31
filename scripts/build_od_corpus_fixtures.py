#!/usr/bin/env python3
"""
Batch-build layer-1 benchmark fixtures from PDFs in the local object-detection corpus.

Maps PDF filenames to stable case_id dirs under tests/fixtures/benchmarks/layer1/.
Writes article.md, gold.json (stub), SOURCE.txt per case.

Usage (from repo root):
  .venv/bin/python scripts/build_od_corpus_fixtures.py \\
    --pdf-dir /path/to/object-detection [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

# PDF basename -> case_id (must match docs/benchmarks/object-detection-inventory.md)
PDF_TO_CASE_ID: dict[str, str] = {
    "ATSS.pdf": "atss_realpdf",
    "Cascade R-CNN.pdf": "cascade_rcnn_realpdf",
    "CenterNet.pdf": "centernet_realpdf",
    "CornerNet.pdf": "cornernet_realpdf",
    "Deformable DETR.pdf": "deformable_detr_realpdf",
    "DETR.pdf": "detr_realpdf",
    "DETRs.pdf": "detrs_realpdf",
    "DINO.pdf": "dino_realpdf",
    "DN-DETR.pdf": "dn_detr_realpdf",
    "EfficientDet.pdf": "efficientdet_realpdf",
    "Faster R-CNN.pdf": "faster_rcnn_realpdf",
    "Fast R-CNN.pdf": "fast_rcnn_realpdf",
    "FCOS.pdf": "fcos_realpdf",
    "FPN.pdf": "fpn_realpdf",
    "GFL.pdf": "gfl_realpdf",
    "Histograms of Oriented Gradients for Human Detection.pdf": "hog_human_detection_realpdf",
    "Libra R-CNN.pdf": "libra_rcnn_realpdf",
    "Mask R-CNN.pdf": "mask_rcnn_realpdf",
    (
        "Object Detection with Discriminatively Trained Part-Based Models.pdf"
    ): "part_based_models_realpdf",
    "OverFeat.pdf": "overfeat_realpdf",
    "R-CNN.pdf": "rcnn_realpdf",
    "RetinaNet.pdf": "retinanet_focal_realpdf",
    "R-FCN.pdf": "rfcn_realpdf",
    "Selective Search for Object Recognition.pdf": "selective_search_realpdf",
    "SPPNet.pdf": "sppnet_realpdf",
    "SSD.pdf": "ssd_realpdf",
    "TOOD.pdf": "tood_realpdf",
    "YOLOv1.pdf": "yolov1",
    "YOLOv2.pdf": "yolov2_realpdf",
    "YOLOv3.pdf": "yolov3_realpdf",
    "YOLOX.pdf": "yolox_realpdf",
}


def _normalize_od_gold(case_id: str, gold_path: Path) -> None:
    """Align generated stub gold with nightly_heavy real-PDF benchmark style."""

    data = json.loads(gold_path.read_text(encoding="utf-8"))
    refs = data.get("references", {})
    n = refs.get("expected_count", 0)
    arxiv = refs.get("sample_arxiv_ids") or []
    tier_note = (
        " Tier: merge_safe (yolov1 only) — see case_tiers.json."
        if case_id == "yolov1"
        else " Tier: nightly_heavy (see case_tiers.json)."
    )
    data["description"] = (
        "Real CV paper: PDF→text (pypdf) → structured MD; noisy but realistic."
        + tier_note
        + " Authorships empty in gold when author line is not comma-separated."
    )
    data["authorships"] = []
    ge = data.get("graph_expectations") or {}
    ge["min_cites"] = 0
    ge["max_cites"] = min(n + 20, 120)
    ge["min_authorships"] = 0
    ge["max_authorships"] = 8
    ge["min_institutions"] = 0
    ge["max_institutions"] = 8
    ge["expected_cited_arxiv_ids"] = arxiv[:8] if arxiv else []
    ge["max_duplicate_work_fingerprints"] = 8
    ge["max_work_dedup_violations"] = 0
    data["graph_expectations"] = ge
    gold_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    """Run batch PDF→fixture build; exit 1 if any PDF fails."""

    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        default=Path("/home/roman/Documents/ML/CV/object-detection"),
        help="Directory containing PDF files",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print commands only")
    args = parser.parse_args()

    build_script = root / "scripts" / "build_real_pdf_layer1_fixture.py"
    if not build_script.is_file():
        print(f"Missing {build_script}", file=sys.stderr)
        return 1

    pdf_dir: Path = args.pdf_dir
    if not pdf_dir.is_dir():
        print(f"PDF dir not found: {pdf_dir}", file=sys.stderr)
        return 1

    failures: list[tuple[str, str]] = []
    for name, case_id in sorted(PDF_TO_CASE_ID.items(), key=lambda x: x[1]):
        pdf = pdf_dir / name
        if not pdf.is_file():
            failures.append((name, "file missing"))
            continue
        out = root / "tests" / "fixtures" / "benchmarks" / "layer1" / case_id
        cmd = [
            sys.executable,
            str(build_script),
            "--pdf",
            str(pdf),
            "--out",
            str(out),
            "--case-id",
            case_id,
        ]
        if args.dry_run:
            print(" ".join(cmd))
            continue
        r = subprocess.run(
            cmd,
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
        if r.returncode != 0:
            failures.append((name, r.stderr or r.stdout or "unknown error"))
            continue
        source = out / "SOURCE.txt"
        source.write_text(
            "Generated from local PDF (not shipped in repo):\n"
            f"  {pdf}\n\n"
            "Regenerate:\n"
            f"  .venv/bin/python scripts/build_real_pdf_layer1_fixture.py \\\n"
            f'    --pdf "{pdf}" \\\n'
            f"    --out tests/fixtures/benchmarks/layer1/{case_id} \\\n"
            f"    --case-id {case_id}\n\n"
            "Text extraction matches production pypdf path (no VL). "
            "Markdown structure is produced by scripts/build_real_pdf_layer1_fixture.py.\n",
            encoding="utf-8",
        )
        _normalize_od_gold(case_id, out / "gold.json")
        print(f"OK {case_id} <- {name}")

    if failures:
        print("\nFailures:", file=sys.stderr)
        for name, err in failures:
            print(f"  {name}: {err[:500]}", file=sys.stderr)
        return 1 if not args.dry_run else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
