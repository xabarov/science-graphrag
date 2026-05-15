"""Unit tests for PDF read policy helpers (no HTTP)."""

from __future__ import annotations

from science_graphrag.agent.tools.external.pdf_read_pipeline import (
    policy_error_for_host,
    sanitize_pdf_url_for_prompt,
)


def test_sanitize_pdf_url_strips_xmlish_chars() -> None:
    raw = "https://example.org/a<b>test.pdf"
    assert "<" not in sanitize_pdf_url_for_prompt(raw)


def test_policy_error_blocked_domain() -> None:
    err = policy_error_for_host(
        "example.org",
        allowed_domains=None,
        blocked_domains=["example.org"],
    )
    assert err is not None
    assert err[0] == "host_not_allowed"
