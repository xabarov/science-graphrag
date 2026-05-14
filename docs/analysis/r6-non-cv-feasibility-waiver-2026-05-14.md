# R6 non-CV feasibility waiver (2026-05-14)

**Scope:** close the non-CV lane residual in R6 without inventing synthetic domain claims.

## Live contour check

- Base URL: `http://127.0.0.1:18787`
- API checks: `/health` and `/v1/workspaces` return `200`
- Inventory artifact: `eval/results/r6-non-cv-feasibility-waiver-2026-05-14.json`

## Observed workspace set

- Total workspaces: `8`
- Clearly CV-related by name/domain intent: `6`
  - `Object Detection (clean ingested + claims)`
  - `Full pilot object-detection corpus`
  - `Pilot: PDF corpus slice (YOLOv1)`
  - `Pilot: Object Detection (YOLOv1)`
  - `Two-stage detectors (R-CNN family)`
  - `YOLO family`
- Unknown/generic labels (not benchmark-qualified as non-CV): `2`
  - `LogSmoke ingest check`
  - `Research`

## Waiver decision

- **Decision:** non-CV lane is waived for this R6 cycle.
- **Reason:** no benchmark-qualified non-CV workspace in the live contour at check time.
- **Guardrail:** CV and non-CV remain not averaged; publication updates must continue to use the closed CV baseline artifacts only.

## Reopen condition

Reopen non-CV lane when a non-CV workspace with benchmark-ready fixture mapping is available; then run the same R6 matrix (claims, citation edge, retrieval BT2/BT4/BT5, dedup, paper profile snapshot) and add artifacts to manifest.
