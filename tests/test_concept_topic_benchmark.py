"""Smoke tests for concept / ResearchTopic benchmark (Wave N)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from eval.concept_topic.harness_extract import extract_concepts_topics_anchor_harness
from eval.concept_topic.metrics import score_concept_topic_extraction
from eval.concept_topic.runner import (
    discover_concept_topic_case_dirs,
    load_article_for_concept_topic_case,
    run_concept_topic_case,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "benchmarks" / "concept_topic"


def test_discover_contract_tier_includes_contract_shape() -> None:
    cases = discover_concept_topic_case_dirs(FIXTURE_ROOT, tier="concept_topic_merge_contract")
    names = {p.name for p in cases}
    assert "contract_shape" in names


def test_contract_shape_harness_and_metrics() -> None:
    case_dir = FIXTURE_ROOT / "contract_shape"
    gold = json.loads((case_dir / "gold.json").read_text(encoding="utf-8"))
    article = load_article_for_concept_topic_case(case_dir, gold)
    preds = extract_concepts_topics_anchor_harness(article, gold)
    m = score_concept_topic_extraction(preds, gold)
    assert m["contract_only"] is True
    assert m["passed"] is True


def test_yolov1_concepts_mini_case_passes_harness() -> None:
    case_dir = FIXTURE_ROOT / "yolov1_concepts"
    report = run_concept_topic_case(case_dir)
    assert report["case_id"] == "yolov1_concepts"
    assert report["metrics"]["passed"] is True


@pytest.mark.parametrize("case_id", list(discover_concept_topic_case_dirs(FIXTURE_ROOT, tier="concept_topic_mini")))
def test_concept_topic_mini_harness_passes(case_id: Path) -> None:
    report = run_concept_topic_case(case_id)
    assert report["metrics"]["passed"] is True, (case_id.name, report["metrics"])


def test_cli_contract_suite_smoke() -> None:
    cmd = [
        sys.executable,
        "-m",
        "eval.concept_topic",
        str(FIXTURE_ROOT),
        "--suite",
        "--tier",
        "concept_topic_merge_contract",
    ]
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), check=False, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr + proc.stdout
