from pathlib import Path

from science_graphrag.domain.models import ReferenceDraft
from science_graphrag.ingestion.arxiv_ids import extract_arxiv_id_from_text, normalize_arxiv_id
from science_graphrag.ingestion.llm.reference_tool_router import (
    extract_references_from_bibliography_excerpt,
)
from science_graphrag.ingestion.llm.stage_extraction import (
    _canonicalize_arxiv_id,
    _merge_reference_sets,
    _reference_chunk_groups,
    _reference_chunks,
)
from science_graphrag.ingestion.stages.authorships import extract_authorships
from science_graphrag.ingestion.stages.metadata import extract_metadata
from science_graphrag.ingestion.stages.references import extract_references, split_reference_entries

FIXTURE = Path(__file__).parent / "fixtures" / "sample_paper.txt"
CORNERNET_FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "benchmarks"
    / "layer1"
    / "cornernet_realpdf"
    / "article.md"
)


def test_fixture_metadata():
    text = FIXTURE.read_text(encoding="utf-8")
    d = extract_metadata(text)
    assert d.doi == "10.1038/s41586-020-2649-2"
    assert d.title is not None


def test_fixture_authorships():
    text = FIXTURE.read_text(encoding="utf-8")
    a = extract_authorships(text)
    assert len(a) >= 1


def test_fixture_references():
    text = FIXTURE.read_text(encoding="utf-8")
    r = extract_references(text)
    assert any(ref.doi for ref in r)


def test_reference_chunks_split_numbered_entries():
    ref_text = "\n".join(
        [
            "[1] First reference line",
            "continuation",
            "[2] Second reference line",
            "[3] Third reference line",
        ]
    )
    chunks = _reference_chunks(ref_text, batch_size=2)
    assert len(chunks) == 2
    assert "First reference line" in chunks[0]
    assert "Third reference line" in chunks[1]


def test_reference_chunk_groups_preserve_expected_entry_counts():
    ref_text = "\n".join(
        [
            "[1] First reference line",
            "continuation",
            "[2] Second reference line",
            "[3] Third reference line",
        ]
    )
    groups = _reference_chunk_groups(ref_text, batch_size=2)
    assert [len(group) for group in groups] == [2, 1]


def test_canonicalize_arxiv_id_drops_version_suffix():
    assert _canonicalize_arxiv_id("1506.01497v3") == "1506.01497"


def test_normalize_arxiv_id_repairs_compact_form():
    assert normalize_arxiv_id("170306870") == "1703.06870"


def test_normalize_arxiv_id_rejects_invalid_modern_short_suffix():
    assert normalize_arxiv_id("1612.0000") is None


def test_extract_arxiv_id_from_text_handles_abs_and_arxiv_prefix():
    assert extract_arxiv_id_from_text("CoRR, abs/1703.06211") == "1703.06211"
    assert extract_arxiv_id_from_text("arXiv:1504.08083v2") == "1504.08083"


def test_split_reference_entries_handles_author_year_bibliography():
    text = CORNERNET_FIXTURE.read_text(encoding="utf-8")
    entries = split_reference_entries(text)
    assert len(entries) >= 40
    assert entries[0].startswith("Bell, S., Lawrence Zitnick, C., Bala, K., and Girshick,")


def test_reference_chunks_split_author_year_entries():
    text = CORNERNET_FIXTURE.read_text(encoding="utf-8")
    ref_section = text.split("## References", maxsplit=1)[1].strip()
    chunks = _reference_chunks(ref_section, batch_size=10)
    assert len(chunks) >= 4


def test_merge_reference_sets_enriches_heuristic_entries():
    heuristic = [
        ReferenceDraft(raw_reference="A paper", doi=None, arxiv_id=None),
    ]
    llm = [
        ReferenceDraft(raw_reference="A paper", doi="10.1000/test", arxiv_id="1703.06211"),
    ]
    merged, stats = _merge_reference_sets(heuristic, llm)
    assert len(merged) == 1
    assert merged[0].doi == "10.1000/test"
    assert merged[0].arxiv_id == "1703.06211"
    assert stats["llm_enriched_entries"] == 1


def test_merge_reference_sets_adds_new_llm_entries():
    heuristic = [
        ReferenceDraft(raw_reference="A paper", doi="10.1000/a"),
    ]
    llm = [
        ReferenceDraft(raw_reference="Another paper", arxiv_id="1703.06211"),
    ]
    merged, stats = _merge_reference_sets(heuristic, llm)
    assert len(merged) == 2
    assert stats["llm_new_entries"] == 1


def test_merge_conservative_skips_unmatched_bare_llm_rows():
    heuristic = [
        ReferenceDraft(raw_reference="First ref", doi="10.1000/a"),
    ]
    llm = [
        ReferenceDraft(raw_reference="Unmatched noise without ids", doi=None, arxiv_id=None),
    ]
    merged, stats = _merge_reference_sets(heuristic, llm, mode="conservative")
    assert len(merged) == 1
    assert stats["llm_skipped_bare"] == 1
    assert stats["llm_new_entries"] == 0


def test_merge_conservative_cap_falls_back_to_enrich_only():
    heuristic = [
        ReferenceDraft(raw_reference="A", doi=None),
        ReferenceDraft(raw_reference="B", doi=None),
    ]
    llm = [
        ReferenceDraft(raw_reference="x1", doi="10.1000/one"),
        ReferenceDraft(raw_reference="x2", doi="10.1000/two"),
        ReferenceDraft(raw_reference="x3", doi="10.1000/three"),
        ReferenceDraft(raw_reference="x4", doi="10.1000/four"),
    ]
    merged, stats = _merge_reference_sets(
        heuristic,
        llm,
        mode="conservative",
        max_extra_beyond_heuristic=0,
    )
    assert stats["merge_cap_applied"] == 1
    assert len(merged) == 2


def test_normalize_raw_reference_key_strips_leading_enum():
    from science_graphrag.ingestion.llm.stage_extraction import _normalize_raw_reference_key

    a = _normalize_raw_reference_key("[12] Same title text")
    b = _normalize_raw_reference_key("Same title text")
    assert a == b


def test_extract_references_from_bibliography_excerpt_runs_heuristic_stage():
    excerpt = "[1] Doe, J. Example. https://doi.org/10.1000/xyz"
    refs = extract_references_from_bibliography_excerpt(excerpt)
    assert len(refs) >= 1
    assert refs[0].doi is not None
