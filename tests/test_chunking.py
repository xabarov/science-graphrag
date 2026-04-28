import pytest

from science_graphrag.ingestion.chunking import (
    DEFAULT_CHUNKING_ENGINE,
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


def test_unknown_chunking_engine_raises():
    with pytest.raises(ValueError, match="Unknown chunking engine"):
        chunk_document_for_retrieval("x", engine="not_a_real_engine")


def test_chunking_default_engine_is_chonkie_recursive():
    assert DEFAULT_CHUNKING_ENGINE == "chonkie_recursive"
    md = "## Intro\n\nHello world.\n\n"
    by_default = chunk_document_for_retrieval(md, target_tokens=80, overlap_tokens=10)
    explicit = chunk_document_for_retrieval(
        md,
        target_tokens=80,
        overlap_tokens=10,
        engine="chonkie_recursive",
    )
    assert [c.chunk_fingerprint for c in by_default] == [c.chunk_fingerprint for c in explicit]


def test_chonkie_recursive_deterministic_fingerprints():
    pytest.importorskip("chonkie")
    md = "## Methods\n\n" + ("We describe the setup. " * 80) + "\n\n"
    c1 = chunk_document_for_retrieval(
        md,
        target_tokens=50,
        overlap_tokens=5,
        engine="chonkie_recursive",
    )
    c2 = chunk_document_for_retrieval(
        md,
        target_tokens=50,
        overlap_tokens=5,
        engine="chonkie_recursive",
    )
    assert [c.chunk_fingerprint for c in c1] == [c.chunk_fingerprint for c in c2]


def test_chonkie_recursive_chunk_text_matches_normalized_slice():
    pytest.importorskip("chonkie")
    md = "# Title\n\n" + "repeat\n\n" * 5 + "## Next\n\nBody here.\n\n"
    chunks = chunk_document_for_retrieval(
        md,
        target_tokens=30,
        overlap_tokens=0,
        engine="chonkie_recursive",
    )
    assert chunks
    for ch in chunks:
        assert md[ch.start_offset : ch.end_offset] == ch.text


def test_chonkie_recursive_section_paths_like_legacy():
    pytest.importorskip("chonkie")
    md = "# Title\n\nIntro.\n\n" "## Section A\n\nAlpha.\n\n" "## Section B\n\nBeta.\n\n"
    paths = {
        c.section_path
        for c in chunk_document_for_retrieval(
            md,
            target_tokens=200,
            overlap_tokens=10,
            engine="chonkie_recursive",
        )
    }
    assert any("Title" in p for p in paths)
    assert any("Section A" in p for p in paths)
    assert any("Section B" in p for p in paths)
