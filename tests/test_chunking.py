from science_graphrag.ingestion.chunking import (
    DocumentChunk,
    approx_tokens,
    chunk_document_for_retrieval,
    dedupe_chunks_for_embedding,
)


def test_approx_tokens_positive():
    assert approx_tokens("abcd") >= 1


def test_section_aware_chunks_respect_headings():
    md = (
        "# Title\n\nPara one.\n\n"
        "## Section A\n\nAlpha text here.\n\n"
        "## Section B\n\nBeta text here.\n\n"
    )
    chunks = chunk_document_for_retrieval(md, target_tokens=50, overlap_tokens=5)
    paths = {c.section_path for c in chunks}
    assert "(preamble)" in paths or any("Section" in p for p in paths)


def test_dedupe_chunks_keeps_first_fingerprint():
    a = DocumentChunk(
        chunk_fingerprint="same",
        section_path="S",
        text="x",
        start_offset=0,
        end_offset=1,
        chunk_index=0,
    )
    b = DocumentChunk(
        chunk_fingerprint="same",
        section_path="S",
        text="y",
        start_offset=1,
        end_offset=2,
        chunk_index=1,
    )
    out = dedupe_chunks_for_embedding([a, b])
    assert len(out) == 1
    assert out[0].text == "x"


def test_deterministic_fingerprint_same_input():
    md = "## Intro\n\nHello world.\n\n"
    c1 = chunk_document_for_retrieval(md, target_tokens=500, overlap_tokens=20)
    c2 = chunk_document_for_retrieval(md, target_tokens=500, overlap_tokens=20)
    assert [c.chunk_fingerprint for c in c1] == [c.chunk_fingerprint for c in c2]
