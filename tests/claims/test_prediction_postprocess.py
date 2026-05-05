"""Tests for BT6 prediction post-processing."""

from __future__ import annotations

from eval.claims.prediction_postprocess import dedupe_near_duplicate_predictions


def test_dedupe_drops_duplicate_identical_text() -> None:
    text = "Model A beats B on COCO with a novel loss."
    rows = [
        {"claim_text": text, "claim_text_normalized": ""},
        {"claim_text": text, "claim_text_normalized": ""},
        {
            "claim_text": "Training uses bipartite matching for assignment.",
            "claim_text_normalized": "",
        },
    ]
    out = dedupe_near_duplicate_predictions(rows, jaccard_min=0.92)
    assert len(out) == 2
    assert "bipartite" in out[1]["claim_text"]


def test_dedupe_keeps_distinct_claims() -> None:
    rows = [
        {"claim_text": "Model A beats B on COCO.", "claim_text_normalized": ""},
        {"claim_text": "Training uses bipartite matching.", "claim_text_normalized": ""},
    ]
    assert dedupe_near_duplicate_predictions(rows, jaccard_min=0.92) == rows
