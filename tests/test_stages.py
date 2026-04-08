from pathlib import Path

from science_graphrag.ingestion.arxiv_ids import extract_arxiv_id_from_text, normalize_arxiv_id
from science_graphrag.ingestion.llm.stage_extraction import _canonicalize_arxiv_id, _reference_chunks
from science_graphrag.ingestion.stages.authorships import extract_authorships
from science_graphrag.ingestion.stages.metadata import extract_metadata
from science_graphrag.ingestion.stages.references import extract_references, split_reference_entries

FIXTURE = Path(__file__).parent / "fixtures" / "sample_paper.txt"
CORNERNET_FIXTURE = Path(__file__).parent / "fixtures" / "benchmarks" / "layer1" / "cornernet_realpdf" / "article.md"


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
