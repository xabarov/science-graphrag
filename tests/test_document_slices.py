from science_graphrag.ingestion.document_slices import (
    build_references_scope_text,
    find_reference_section_spans,
    front_matter_slice,
    strip_repeated_boilerplate,
)


def test_front_matter_stops_before_introduction():
    text = (
        "# Title\n\nAuthor One, Author Two\n\n"
        "Abstract\n\nWe study X.\n\n"
        "## Introduction\n\nBody here."
    )
    sl = front_matter_slice(text, max_chars=50_000)
    assert "Abstract" in sl.text
    assert "## Introduction" not in sl.text
    assert "Body here" not in sl.text
    assert sl.slice_type == "front_matter"


def test_references_scope_finds_mid_document_section():
    text = (
        "# Paper\n\n## Methods\n\nWe did Y.\n\n"
        "## References\n\n[1] Doe et al. 2020.\n\n"
        "## Appendix\n\nExtra."
    )
    scope = build_references_scope_text(text, max_chars=50_000)
    assert "Doe et al" in scope
    assert "Methods" not in scope
    spans = find_reference_section_spans(text)
    assert len(spans) == 1


def test_reference_span_stops_before_plain_appendix_when_no_next_heading():
    """EOF fallback must not swallow appendix tail (real-PDF MD pattern)."""
    text = "# Paper\n\n## References\n\n[1] Doe et al. 2020.\n\n" "A Appendix\n\nExtra."
    spans = find_reference_section_spans(text)
    assert len(spans) == 1
    start, end = spans[0]
    body = text[start:end]
    assert "Doe" in body
    assert "Appendix" not in body


def test_reference_span_stops_at_ocr_double_a_appendix():
    """OCR sometimes emits ``A A PPENDIX`` without markdown heading (ICLR PDF MD)."""
    text = "# Paper\n\n## References\n\n[1] Doe et al. 2020.\n\n" "A A PPENDIX\n\nMore."
    spans = find_reference_section_spans(text)
    assert len(spans) == 1
    start, end = spans[0]
    body = text[start:end]
    assert "Doe" in body
    assert "PPENDIX" not in body


def test_strip_repeated_boilerplate_drops_consecutive_page_numbers():
    raw = "Intro\n12\n12\n12\nMore text"
    out = strip_repeated_boilerplate(raw)
    assert out.count("12") < raw.count("12")
