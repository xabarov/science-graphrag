from __future__ import annotations

from eval.chat_agent.phoenix_export import (
    _classify_phoenix_json_payload,
    _normalize_otel_trace_id_hex,
    extract_span_names_for_trace,
    has_final_answer_tool_span,
    merge_span_name_lists,
    phoenix_ui_trace_url,
)


def test_normalize_otel_trace_id_hex() -> None:
    assert _normalize_otel_trace_id_hex("AB-cd-12") == "abcd12"
    assert _normalize_otel_trace_id_hex("0xFF") == "ff"


def test_classify_embedded_spans() -> None:
    valid, kind = _classify_phoenix_json_payload({"spans": [{"name": "tool.x"}]})
    assert valid is True
    assert kind == "embedded_spans"


def test_classify_html_raw_invalid() -> None:
    valid, kind = _classify_phoenix_json_payload({"raw": "<!DOCTYPE html><html>"})
    assert valid is False
    assert kind == "html_shell"


def test_phoenix_ui_trace_url_project_aware(monkeypatch) -> None:
    monkeypatch.setenv("PHOENIX_UI_BASE_URL", "http://phoenix.test:6006")
    monkeypatch.setenv("PHOENIX_PROJECT_NAME", "my-proj/1")
    u = phoenix_ui_trace_url(trace_id="abc123")
    assert u == "http://phoenix.test:6006/projects/my-proj%2F1/traces/abc123"
    monkeypatch.delenv("PHOENIX_PROJECT_NAME", raising=False)
    monkeypatch.delenv("PHOENIX_PROJECT_ID", raising=False)
    u2 = phoenix_ui_trace_url(trace_id="x", base_url="http://h", project_identifier="p")
    assert u2 == "http://h/projects/p/traces/x"


def test_extract_span_names_trace_list_filters_by_trace_id() -> None:
    want = "aa" * 16
    other = "bb" * 16
    payload = {
        "data": [
            {
                "trace_id": other,
                "spans": [{"name": "ingest_document"}, {"name": "tool.bad"}],
            },
            {
                "trace_id": want,
                "spans": [
                    {"name": "agent.query"},
                    {"name": "tool.idea_search", "metadata": {"name": "ingest_document"}},
                ],
            },
        ],
    }
    names = extract_span_names_for_trace(payload, want)
    assert names == ["agent.query", "tool.idea_search"]
    assert "ingest_document" not in names


def test_extract_span_names_span_list_no_trace_id_includes_all() -> None:
    want = "cc" * 16
    payload = {
        "data": [
            {"name": "llm.agent.react_turn", "span_id": "1"},
            {"name": "tool.final_answer", "span_id": "2", "parent_id": "0"},
        ],
    }
    names = extract_span_names_for_trace(payload, want)
    assert names == ["llm.agent.react_turn", "tool.final_answer"]


def test_classify_and_extract_span_list_name_only_rows() -> None:
    """REST may return span rows with ``name`` but no span_id (trace from query string)."""

    want = "cafe" * 8
    payload = {
        "data": [
            {"name": "agent.query", "start_time": "2024-01-01T00:00:00Z"},
            {"name": "tool.idea_search"},
        ],
    }
    valid, kind = _classify_phoenix_json_payload(payload)
    assert valid is True
    assert kind == "span_list"
    assert extract_span_names_for_trace(payload, want) == ["agent.query", "tool.idea_search"]


def test_extract_span_names_span_list_skips_unlabeled_when_mismatch() -> None:
    want = "dd" * 16
    foreign = "ee" * 16
    payload = {
        "data": [
            {"name": "orphan", "trace_id": foreign},
            {"name": "should_skip_unlabeled"},
        ],
    }
    names = extract_span_names_for_trace(payload, want)
    assert names == []


def test_extract_span_names_unknown_payload_empty() -> None:
    assert extract_span_names_for_trace({"foo": [{"name": "ingest_document"}]}, "ab" * 16) == []


def test_extract_span_names_embedded_root_trace_mismatch() -> None:
    want = "ff" * 16
    payload = {"trace_id": "00" * 16, "spans": [{"name": "agent.query"}]}
    assert extract_span_names_for_trace(payload, want) == []


def test_has_final_answer_tool_span_accepts_tool_prefix() -> None:
    assert has_final_answer_tool_span(["chat", "tool.final_answer"])
    assert not has_final_answer_tool_span(["chat", "llm.agent.writer"])


def test_merge_span_name_lists_preserves_order() -> None:
    merged = merge_span_name_lists(["a", "b"], ["b", "c"])
    assert merged == ["a", "b", "c"]


def test_collect_phoenix_span_names_merges_desc_and_asc(monkeypatch) -> None:
    from eval.chat_agent import phoenix_export as pe

    want = "ab" * 16
    payload_desc = {"data": [{"name": "llm.agent.writer", "span_id": "1"}]}
    payload_asc = {"data": [{"name": "tool.final_answer", "span_id": "2"}]}

    def _fake_fetch(
        trace_id: str,
        *,
        sort_order=None,
        **kwargs: object,
    ) -> dict[str, object]:
        _ = trace_id, kwargs
        if sort_order == "asc":
            return {"ok": True, "payload": payload_asc, "trace_id": want}
        return {"ok": True, "payload": payload_desc, "trace_id": want}

    monkeypatch.setattr(pe, "try_fetch_phoenix_spans", _fake_fetch)
    snap = pe.collect_phoenix_span_names_for_trace(want)
    assert snap["fetch_strategy"] == "desc_plus_asc"
    assert "tool.final_answer" in snap["span_names"]


def test_phoenix_project_identifier_default(monkeypatch) -> None:
    from eval.chat_agent.phoenix_export import phoenix_project_identifier

    monkeypatch.delenv("PHOENIX_PROJECT_ID", raising=False)
    monkeypatch.delenv("PHOENIX_PROJECT_NAME", raising=False)
    assert phoenix_project_identifier() == "science-graphrag"
    monkeypatch.setenv("PHOENIX_PROJECT_NAME", "custom")
    assert phoenix_project_identifier() == "custom"
    monkeypatch.setenv("PHOENIX_PROJECT_ID", "override-id")
    assert phoenix_project_identifier() == "override-id"
