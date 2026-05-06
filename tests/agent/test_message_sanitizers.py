"""Tests for pre-compact message sanitizers (§10.5.4)."""

from __future__ import annotations

from langchain_core.messages import HumanMessage

from science_graphrag.agent.context.message_sanitizers import (
    sanitize_digest_dict_for_compact,
    sanitize_messages_for_summary,
)


def test_strip_images_from_multimodal_human() -> None:
    msgs = [
        HumanMessage(
            content=[
                {"type": "text", "text": "hello"},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}},
            ]
        )
    ]
    out = sanitize_messages_for_summary(msgs)
    assert isinstance(out[0].content, list)
    assert all(
        not (isinstance(p, dict) and str(p.get("type") or "").lower() == "image_url")
        for p in out[0].content
    )


def test_strip_reinjected_blocks_from_human_string() -> None:
    raw = "<paper_sources_restored>\n- w1: x\n</paper_sources_restored>\n" "Question after?"
    msgs = [HumanMessage(content=raw)]
    out = sanitize_messages_for_summary(msgs)
    assert "<paper_sources_restored>" not in str(out[0].content)
    assert "Question after?" in str(out[0].content)


def test_sanitize_digest_dict_strips_markers() -> None:
    d = sanitize_digest_dict_for_compact(
        {
            "user_intent": "x",
            "answer_excerpt": "<client_history_digest>{}</client_history_digest> tail",
        }
    )
    assert "<client_history_digest>" not in d["answer_excerpt"]
    assert "tail" in d["answer_excerpt"]
