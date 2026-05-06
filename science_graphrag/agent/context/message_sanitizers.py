"""Pre-compact sanitizers (Train T2 §10.5.4): drop images and duplicate reinjected blocks."""

from __future__ import annotations

import re
from typing import Any, Sequence

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

_RE_PAPER_SOURCES = re.compile(
    r"<paper_sources_restored>[\s\S]*?</paper_sources_restored>",
    re.IGNORECASE,
)
_RE_CLIENT_DIGEST = re.compile(
    r"<client_history_digest>[\s\S]*?</client_history_digest>",
    re.IGNORECASE,
)


def _strip_reinjected_markers(text: str) -> str:
    s = str(text or "")
    s = _RE_PAPER_SOURCES.sub("", s)
    s = _RE_CLIENT_DIGEST.sub("", s)
    return s


def _strip_image_parts_from_content(content: Any) -> Any:
    """Remove OpenAI-style image_url parts from multimodal message content."""
    if not isinstance(content, list):
        return content
    out: list[Any] = []
    for part in content:
        if isinstance(part, dict):
            if str(part.get("type") or "").lower() == "image_url":
                continue
        out.append(part)
    return out if out else ""


def strip_images_from_messages(messages: Sequence[BaseMessage]) -> list[BaseMessage]:
    """Return a shallow copy with image parts removed from human/AI multimodal content."""
    out: list[BaseMessage] = []
    for m in messages:
        if isinstance(m, HumanMessage):
            nc = _strip_image_parts_from_content(m.content)
            if nc is m.content:
                out.append(m)
            else:
                out.append(m.model_copy(update={"content": nc}))
        elif isinstance(m, AIMessage):
            nc = _strip_image_parts_from_content(m.content)
            if nc is m.content:
                out.append(m)
            else:
                out.append(m.model_copy(update={"content": nc}))
        else:
            out.append(m)
    return out


def strip_reinjected_attachments_from_messages(
    messages: Sequence[BaseMessage],
) -> list[BaseMessage]:
    """Drop reinjected XML blocks from HumanMessage string bodies (avoid double inclusion)."""
    out: list[BaseMessage] = []
    for m in messages:
        if isinstance(m, HumanMessage) and isinstance(m.content, str):
            cleaned = _strip_reinjected_markers(m.content)
            if cleaned == m.content:
                out.append(m)
            else:
                out.append(m.model_copy(update={"content": cleaned}))
        else:
            out.append(m)
    return out


def sanitize_messages_for_summary(messages: Sequence[BaseMessage]) -> list[BaseMessage]:
    """Apply both sanitizers in stable order."""
    step1 = strip_images_from_messages(messages)
    return strip_reinjected_attachments_from_messages(step1)


def sanitize_digest_dict_for_compact(d: dict[str, Any]) -> dict[str, Any]:
    """Return a shallow copy with long text fields scrubbed for L4 digest compaction."""
    out = dict(d)
    for key in ("user_intent", "answer_excerpt"):
        if key in out and isinstance(out[key], str):
            out[key] = _strip_reinjected_markers(out[key])
    return out


def sanitize_digest_list_for_compact(digests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deep-ish copy of digest list with per-row sanitizer."""
    return [sanitize_digest_dict_for_compact(dict(x)) for x in digests if isinstance(x, dict)]


def sanitize_messages_for_react_pre_compact(
    messages: Sequence[BaseMessage],
    *,
    enabled: bool,
) -> list[BaseMessage]:
    """Optional pre-compact pass before ToolMessage compaction (single-agent ReAct)."""
    if not enabled:
        return list(messages)
    return sanitize_messages_for_summary(messages)
