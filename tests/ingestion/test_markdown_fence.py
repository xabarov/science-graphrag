"""Tests for whole-document markdown fence stripping."""

from __future__ import annotations

from science_graphrag.ingestion.document_slices import strip_repeated_boilerplate
from science_graphrag.ingestion.markdown_fence import strip_whole_document_markdown_fence
from science_graphrag.ingestion.normalize import normalize_text


def test_strips_markdown_labeled_fence() -> None:
    raw = "```markdown\n# Title\n\n**bold**\n```"
    assert strip_whole_document_markdown_fence(raw) == "# Title\n\n**bold**"


def test_strips_plain_triple_backtick_fence() -> None:
    raw = "```\nHello\n```"
    assert strip_whole_document_markdown_fence(raw) == "Hello"


def test_strips_with_leading_trailing_blank_lines() -> None:
    raw = "\n\n```markdown\nBody\n```\n\n"
    assert strip_whole_document_markdown_fence(raw) == "Body"


def test_no_change_when_not_wrapped() -> None:
    raw = "# Hi\n\n```python\nx = 1\n```\n"
    assert strip_whole_document_markdown_fence(raw) == raw


def test_no_change_when_only_opening_fence() -> None:
    raw = "```markdown\narXiv only\nno closing"
    assert strip_whole_document_markdown_fence(raw) == raw


def test_no_change_on_empty() -> None:
    assert strip_whole_document_markdown_fence("") == ""
    assert strip_whole_document_markdown_fence("   \n  \n") == "   \n  \n"


def test_inner_empty_returns_source() -> None:
    raw = "```markdown\n```"
    assert strip_whole_document_markdown_fence(raw) == raw


def test_pipeline_order_strip_then_normalize_like_ingest() -> None:
    raw = "```markdown\n# T\n\n**x**\n```"
    normalized = strip_repeated_boilerplate(normalize_text(strip_whole_document_markdown_fence(raw)))
    assert normalized == "# T\n\n**x**"
