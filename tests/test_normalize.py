from science_graphrag.ingestion.normalize import chunk_text, normalize_text


def test_normalize_collapses_space():
    t = normalize_text("a  \n\n  b")
    assert "a" in t and "b" in t


def test_chunk_overlap():
    t = "x" * 100
    chunks = chunk_text(t, size=30, overlap=5)
    assert len(chunks) >= 2
    assert all(len(c) <= 30 for c in chunks)
