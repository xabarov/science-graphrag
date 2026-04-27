"""Smoke tests for scripts/report_extraction_entity_metrics.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def tiny_layer1_path(tmp_path: Path) -> Path:
    suite = {
        "run_metadata": {"extraction_llm_model": "test/model"},
        "cases": [
            {
                "case_id": "c1",
                "metrics": {
                    "metadata": {"title_token_f1": 1.0, "title_rouge_l": 0.9},
                    "authorships": {
                        "names_precision": 1.0,
                        "names_recall": 1.0,
                        "names_f1": 1.0,
                        "affiliations_precision": 1.0,
                        "affiliations_recall": 0.5,
                        "affiliations_f1": 0.666,
                    },
                    "references": {
                        "sample_arxiv_precision": 1.0,
                        "sample_arxiv_recall": 0.0,
                        "sample_arxiv_f1": 0.0,
                        "sample_doi_precision": None,
                        "sample_doi_recall": None,
                        "sample_doi_f1": None,
                    },
                },
                "gold": {
                    "graph_expectations": {"expected_cited_arxiv_ids": ["1234.5678"]},
                },
            }
        ],
    }
    p = tmp_path / "layer1.json"
    p.write_text(json.dumps(suite), encoding="utf-8")
    return p


def test_report_script_writes_outputs(tmp_path: Path, tiny_layer1_path: Path) -> None:
    out_json = tmp_path / "out.json"
    out_md = tmp_path / "out.md"
    missing = tmp_path / "no_such_layer2.json"
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "report_extraction_entity_metrics.py"),
        "--repo-root",
        str(REPO_ROOT),
        "--layer1-json",
        str(tiny_layer1_path),
        "--layer2-json",
        str(missing),
        "--claims-pilot-json",
        str(missing),
        "--claims-holdout-json",
        str(missing),
        "--out-json",
        str(out_json),
        "--out-md",
        str(out_md),
    ]
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["run_metadata"]["extraction_llm_model"] == "test/model"
    assert any(s["slot_id"] == "author_names" for s in payload["slots"])
    assert (
        "Macro mean" in out_md.read_text(encoding="utf-8")
        or "macro mean" in out_md.read_text(encoding="utf-8").lower()
    )
