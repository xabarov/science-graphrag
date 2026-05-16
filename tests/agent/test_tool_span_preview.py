"""Tests for Phoenix tool span payload previews."""

from __future__ import annotations

from science_graphrag.agent.tools.base import _tool_span_payload_preview


def test_tool_span_preview_surfaces_ok_false_and_error() -> None:
    preview = _tool_span_payload_preview(
        {
            "ok": False,
            "error": "fetch_failed",
            "detail": "HTTP 403",
            "row_count": 0,
        }
    )
    assert preview["ok"] is False
    assert preview["error"] == "fetch_failed"
    assert preview["detail"] == "HTTP 403"


def test_tool_span_preview_ok_true_includes_row_count() -> None:
    preview = _tool_span_payload_preview({"ok": True, "row_count": 3, "summary": "long text"})
    assert preview == {"ok": True, "row_count": 3}
