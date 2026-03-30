from pathlib import Path

from science_graphrag.ingestion.stages.authorships import extract_authorships
from science_graphrag.ingestion.stages.metadata import extract_metadata
from science_graphrag.ingestion.stages.references import extract_references

FIXTURE = Path(__file__).parent / "fixtures" / "sample_paper.txt"


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
