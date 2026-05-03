# Habr window — failure analysis (claims paraphrase, BT6)

Sources: `eval/results/habr-window-2026-05-iter-v2-*.json`, `scripts/report_claims_paraphrase_diagnostics.py` output `habr-window-2026-05-diagnostics.md`, gold under `tests/fixtures/benchmarks/claims/`.

Per-case F1 is computed as \(2PR/(P+R)\) from `claim_precision` and `claim_recall` in the suite JSON; **macro-F1** is the mean over cases (same convention as the Habr article table for this window).

## Case 1 — `holdout_dino_v1` (holdout): adjudicated gold vs numeric extractions

| | |
|---|---|
| **Gold (example)** | `dino_swinl_63ap`: Swin-L backbone, ~63 AP on COCO val — semantically matched via **rouge_l** / embedding vs normalized reference text in `gold.json`. |
| **Best-effort prediction** | Several claims quote **63.2AP / 63.3AP** and Objects365 pre-training (aligned with paper numbers). |
| **Why miss** | BT6 still scores **0 matched rows**: normalized adjudicated phrasing encodes **specific causal structure** (query denoising, hybrid query selection, scaling narrative). Predictions capture **performance facts** but do not align with the **exact gold dimensions** under embedding/ROUGE gates → **semantic drift vs gold schema**, not quote rejection. |

## Case 2 — `corpus_efficientdet_v2` (pilot): collapse to few predictions

| | |
|---|---|
| **Gold** | Five rows (BiFPN weighting, compound scaling, D7 AP, negative scaling rows). |
| **Observation** | Baseline run produced **4** predictions with **0** recall on EfficientDet gold rows (suite JSON). |
| **Why miss** | **Omission / coverage**: extractor under-filled the benchmark cap relative to dense abstract-style gold; distractors add little if plain lane already misses rows. |

## Case 3 — `corpus_detr_v2` (pilot): distractor precision collapse

| | |
|---|---|
| **Signal** | Plain lane recall **0.75** (3/4 rows) but suite **FAIL** — `precision_drop_with_distractors` exceeds **0.15** when distracted predictions diverge. |
| **Why miss** | **Noise under distraction**: neighboring-paper paragraphs inflate false positives or reorder emphasis so precision on distracted text drops beyond the allowed band — distinct from plain recall. |
