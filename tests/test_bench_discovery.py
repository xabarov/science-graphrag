"""Benchmark discovery helpers."""

from __future__ import annotations

from pathlib import Path

from eval.bench_common import discover_layer1_case_dirs
from science_graphrag.ingestion.pipeline import discover_corpus_files

FIXTURES_LAYER1 = Path(__file__).resolve().parent / "fixtures" / "benchmarks" / "layer1"


def test_discover_layer1_case_dirs_finds_known_cases() -> None:
    cases = discover_layer1_case_dirs(FIXTURES_LAYER1)
    ids = {p.name for p in cases}
    assert "yolov1" in ids
    assert "doi_refs_heavy" in ids
    assert "arxiv_refs_heavy" in ids
    assert "noisy_layout_stub" in ids
    assert "retinanet_focal_realpdf" in ids
    assert "fcos_realpdf" in ids
    assert "detr_realpdf" in ids
    assert len(cases) >= 11


def test_discover_layer1_merge_safe_tier() -> None:
    cases = discover_layer1_case_dirs(FIXTURES_LAYER1, tier="merge_safe")
    ids = {p.name for p in cases}
    assert ids == {
        "arxiv_refs_heavy",
        "doi_refs_heavy",
        "noisy_layout_stub",
        "yolov1",
    }


def test_discover_corpus_files_finds_suffixes(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("x", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_text("y", encoding="utf-8")
    (tmp_path / "skip.py").write_text("#", encoding="utf-8")
    found = discover_corpus_files(tmp_path)
    assert {p.name for p in found} == {"a.md", "b.txt"}
