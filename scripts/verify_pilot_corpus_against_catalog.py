#!/usr/bin/env python3
"""Cross-check pilot PDF directory against corpus_v1.json (P0 roadmap slugs + coverage hints)."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_CATALOG_JSON = _REPO / "tests" / "fixtures" / "corpus" / "corpus_v1.json"

# Roadmap §10.1 step 3 — first-wave corpus_work_id slugs (see CATALOG.md).
P0_CORPUS_WORK_IDS: tuple[str, ...] = (
    "cornernet_realpdf",
    "fcos_realpdf",
    "fpn_realpdf",
    "mask_rcnn_realpdf",
    "retinanet_focal_realpdf",
    "ssd_realpdf",
    "faster_rcnn_realpdf",
    "fast_rcnn_realpdf",
)

# Longer keys first — first match wins (pilot folder uses human-readable PDF names).
_FILENAME_HINTS: tuple[tuple[str, str], ...] = (
    ("deformable detr", "deformable_detr_realpdf"),
    ("dn-detr", "dn_detr_realpdf"),
    ("dn detr", "dn_detr_realpdf"),
    ("dino", "dino_realpdf"),
    ("detrs", "detrs_realpdf"),
    ("dino", "dino_realpdf"),
    ("detr", "detr_realpdf"),
    ("efficientdet", "efficientdet_realpdf"),
    ("centernet", "centernet_realpdf"),
    ("cornernet", "cornernet_realpdf"),
    ("cascade r-cnn", "cascade_rcnn_realpdf"),
    ("libra r-cnn", "libra_rcnn_realpdf"),
    ("mask r-cnn", "mask_rcnn_realpdf"),
    ("faster r-cnn", "faster_rcnn_realpdf"),
    ("fast r-cnn", "fast_rcnn_realpdf"),
    ("r-fcn", "rfcn_realpdf"),
    ("retinanet", "retinanet_focal_realpdf"),
    ("histograms of oriented gradients", "hog_human_detection_realpdf"),
    ("part-based models", "part_based_models_realpdf"),
    ("selective search", "selective_search_realpdf"),
    ("overfeat", "overfeat_realpdf"),
    ("sppnet", "sppnet_realpdf"),
    ("yolov3", "yolov3_realpdf"),
    ("yolov2", "yolov2_realpdf"),
    ("yolov1", "yolov1"),
    ("yolox", "yolox_realpdf"),
    ("atss", "atss_realpdf"),
    ("fcos", "fcos_realpdf"),
    ("fpn", "fpn_realpdf"),
    ("ssd", "ssd_realpdf"),
    ("tood", "tood_realpdf"),
    ("gfl", "gfl_realpdf"),
    ("r-cnn.pdf", "rcnn_realpdf"),
    ("r-cnn", "rcnn_realpdf"),
)
_FILENAME_HINTS_SORTED = sorted(_FILENAME_HINTS, key=lambda x: -len(x[0]))


def _norm_stem(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", Path(name).stem.lower()).strip()


def _stem_tokens(stem_norm: str) -> set[str]:
    return {t for t in stem_norm.split() if len(t) >= 2}


def _score_work_row(row: dict, stem_norm: str) -> int:
    """Higher = better match for this PDF stem (disambiguate rcnn vs fast_rcnn vs mask_rcnn)."""
    cid = str(row.get("corpus_work_id") or "")
    title = str(row.get("title") or "").lower()
    arxiv = str(row.get("arxiv_id") or "").replace(".", "")
    stem_compact = stem_norm.replace(" ", "")
    toks = _stem_tokens(stem_norm)
    title_words = {w.strip(".,()") for w in title.split() if len(w.strip(".,()")) >= 3}
    score = 0
    if arxiv and arxiv in re.sub(r"\D", "", stem_norm):
        score += 50
    # Title word hits (weak)
    score += 3 * len(toks & title_words)
    # Slug tokens from corpus_work_id (e.g. faster, rcnn, mask)
    slug = cid.replace("_realpdf", "").replace("_", " ")
    for token in slug.split():
        if len(token) >= 3 and token in stem_compact:
            score += 8 + min(len(token), 12)
    return score


def _by_corpus_id(pilot_like: list[dict]) -> dict[str, dict]:
    return {str(w["corpus_work_id"]): w for w in pilot_like if w.get("corpus_work_id")}


def _hint_corpus_id(filename: str) -> str | None:
    low = filename.lower()
    for needle, cid in _FILENAME_HINTS_SORTED:
        if needle in low:
            return cid
    return None


def _best_work_for_stem(
    pilot_like: list[dict],
    *,
    filename: str,
    stem_norm: str,
) -> dict | None:
    cid = _hint_corpus_id(filename)
    by_c = _by_corpus_id(pilot_like)
    if cid and cid in by_c:
        return by_c[cid]
    scored = [(_score_work_row(w, stem_norm), w) for w in pilot_like]
    scored = [(s, w) for s, w in scored if s > 0]
    if not scored:
        return None
    scored.sort(key=lambda x: (-x[0], -len(str(x[1].get("corpus_work_id", "")))))
    return scored[0][1]


def _load_pilot_like_works() -> list[dict]:
    raw = json.loads(_CATALOG_JSON.read_text(encoding="utf-8"))
    merged: list[dict] = [w for w in raw.get("works", []) if isinstance(w, dict)]
    merged.extend(w for w in raw.get("stub_works_for_inventory_only", []) if isinstance(w, dict))
    non_synth = [
        w
        for w in merged
        if not str(w.get("corpus_work_id", "")).endswith("_heavy")
        and str(w.get("corpus_work_id", "")) not in ("noisy_layout_stub", "ws_graph_contract")
        and "synthetic" not in str(w.get("primary_stage", "")).lower()
    ]
    return [
        w
        for w in non_synth
        if "_realpdf" in str(w.get("corpus_work_id", ""))
        or str(w.get("primary_stage")) == "classical"
        or w.get("corpus_work_id") == "yolov1"
    ]


def main() -> int:
    """CLI entry: print PDF-to-catalog mapping and P0 checklist."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "corpus_dir",
        type=Path,
        help="Directory tree containing pilot PDFs (e.g. PILOT_CORPUS_DIR).",
    )
    args = parser.parse_args()
    root: Path = args.corpus_dir
    if not root.is_dir():
        print(f"Not a directory: {root}", flush=True)
        return 1

    pilot_like = _load_pilot_like_works()

    pdfs = sorted(set(root.rglob("*.pdf")) | set(root.rglob("*.PDF")))
    stems = [(p, _norm_stem(p.name)) for p in pdfs]

    print(f"catalog={_CATALOG_JSON}", flush=True)
    print(f"corpus_dir={root.resolve()} pdf_count={len(pdfs)}", flush=True)

    matched_work_ids: set[str] = set()
    for path, stem_norm in stems:
        best = _best_work_for_stem(pilot_like, filename=path.name, stem_norm=stem_norm)
        if best is None:
            print(f"  ? {path.name}", flush=True)
            continue
        cid = str(best.get("corpus_work_id"))
        matched_work_ids.add(cid)
        print(f"  ~ {path.name} -> {cid}", flush=True)

    by_id = _by_corpus_id(pilot_like)

    print("\nP0 roadmap coverage (corpus_work_id):", flush=True)
    missing_p0: list[str] = []
    for cid in P0_CORPUS_WORK_IDS:
        row = by_id.get(cid)
        ok = False
        if row is not None:
            ok = any(
                (bw := _best_work_for_stem(pilot_like, filename=path.name, stem_norm=stem_norm))
                is not None
                and str(bw.get("corpus_work_id")) == cid
                for path, stem_norm in stems
            )
        if ok:
            matched_work_ids.add(cid)
        else:
            missing_p0.append(cid)
        print(f"  [{'x' if ok else ' '}] {cid}", flush=True)
    if missing_p0:
        print(
            f"\nWARN: no PDF filename/title heuristic match for: {', '.join(missing_p0)}",
            flush=True,
        )
        print("(Filenames may still be correct; verify manually against arXiv PDFs.)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
