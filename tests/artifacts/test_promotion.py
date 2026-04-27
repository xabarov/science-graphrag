"""Promotion sanitization (Phase 4)."""

from __future__ import annotations

import json

from science_graphrag.artifacts.promotion import build_promoted_document, promoted_json_bytes


def test_build_promoted_document_adds_meta_and_redacts() -> None:
    """Sanitizer strips secrets and host paths; meta block is attached."""
    payload = {
        "workspace": "/home/user/proj/data/ws",
        "nested": {"api_key": "secret"},
        "ok": 1,
    }
    out = build_promoted_document(
        payload, source_label="test", s3_key="science-diagnostics/od/x.json"
    )
    assert out["_promotion_meta"]["source"] == "test"
    assert out["_promotion_meta"]["s3_key"] == "science-diagnostics/od/x.json"
    assert out["workspace"] == "<redacted-absolute-path>"
    assert out["nested"]["api_key"] == "<redacted>"
    assert out["ok"] == 1


def test_promoted_json_bytes_size_reasonable() -> None:
    """promoted_json_bytes is valid UTF-8 JSON."""
    raw = promoted_json_bytes({"a": "b"}, source_label="local:/x")
    data = json.loads(raw.decode("utf-8"))
    assert data["_promotion_meta"]["source"] == "local:/x"
    assert data["a"] == "b"


def test_secretary_key_not_treated_as_secret() -> None:
    """Segment-based detector must not redact 'secret' inside unrelated words."""
    out = build_promoted_document(
        {"secretary_name": "Jane", "nested": {"tokenization": "bpe"}},
        source_label="test",
    )
    assert out["secretary_name"] == "Jane"
    assert out["nested"]["tokenization"] == "bpe"


def test_max_tokens_field_not_redacted() -> None:
    """Common LLM config keys must not be over-redacted."""
    out = build_promoted_document({"max_tokens": 4096}, source_label="test")
    assert out["max_tokens"] == 4096


def test_stale_promotion_meta_replaced() -> None:
    """Prior _promotion_meta on payload is dropped before attaching a fresh block."""
    out = build_promoted_document(
        {"_promotion_meta": {"version": 0}, "x": 1},
        source_label="re-promote",
    )
    assert out["_promotion_meta"]["source"] == "re-promote"
    assert out["_promotion_meta"]["version"] == 1
    assert out["x"] == 1
