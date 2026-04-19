"""Tests for scripts/enrich_gold_layer1.py (regex step A, no network)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_enrich_module():
    path = ROOT / "scripts" / "enrich_gold_layer1.py"
    spec = importlib.util.spec_from_file_location("enrich_gold_layer1", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module", name="enrich_layer1")
def enrich_layer1_fixture():
    """Load ``scripts/enrich_gold_layer1.py`` as a module (not on ``sys.path`` as a package)."""
    return _load_enrich_module()


def test_step_a_faster_rcnn_collects_arxiv_ids(enrich_layer1):
    """Regression: faster_rcnn fixture must expose multiple arXiv ids in step A."""
    gold_path = ROOT / "tests/fixtures/benchmarks/layer1/faster_rcnn_realpdf/gold.json"
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    step_a = enrich_layer1.step_a_from_gold(gold)
    assert step_a["count"] >= 8
    assert "1512.03385" in step_a["arxiv_ids_from_bibliography"]


def test_collect_arxiv_ids_from_text_finds_abs_form(enrich_layer1):
    """Regex must capture ``abs/`` and ``arXiv:...vN`` forms."""
    text = "See also abs/2005.12872 and arXiv:1904.07850v2 for details."
    ids = enrich_layer1.collect_arxiv_ids_from_text(text)
    assert "2005.12872" in ids
    assert "1904.07850" in ids


def test_normalize_header_llm_payload_strips_arxiv_version(enrich_layer1):
    """LLM payload normalizer must coerce year and strip arXiv version suffix."""
    raw = {
        "year": "2020",
        "arxiv_id": "2005.12872v3",
        "doi": None,
        "authors": [{"name": " A ", "affiliations": [" X "]}],
    }
    norm = enrich_layer1.normalize_header_llm_payload(raw)
    assert norm["year"] == 2020
    assert norm["arxiv_id"] == "2005.12872"
    assert norm["authors"][0]["name"] == "A"
    assert norm["authors"][0]["affiliations"] == ["X"]
