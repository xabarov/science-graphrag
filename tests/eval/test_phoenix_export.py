from __future__ import annotations

from eval.chat_agent.phoenix_export import (
    _classify_phoenix_json_payload,
    _normalize_otel_trace_id_hex,
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


def test_phoenix_project_identifier_default(monkeypatch) -> None:
    from eval.chat_agent.phoenix_export import phoenix_project_identifier

    monkeypatch.delenv("PHOENIX_PROJECT_ID", raising=False)
    monkeypatch.delenv("PHOENIX_PROJECT_NAME", raising=False)
    assert phoenix_project_identifier() == "science-graphrag"
    monkeypatch.setenv("PHOENIX_PROJECT_NAME", "custom")
    assert phoenix_project_identifier() == "custom"
    monkeypatch.setenv("PHOENIX_PROJECT_ID", "override-id")
    assert phoenix_project_identifier() == "override-id"
