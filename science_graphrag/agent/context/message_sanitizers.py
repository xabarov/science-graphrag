"""Pre-compact sanitizers (Train T2 §10.5.4 / Wave H §H1).

Two layers:

* Structural — drop images and duplicate reinjected XML blocks
  (``<paper_sources_restored>`` / ``<client_history_digest>``) so L4 compact
  does not double-include carry-over evidence into ``session_summary``.
* Sensitive material — redact API key shapes, bearer tokens, AWS access keys,
  and emails before they reach ``_invoke_summary_llm``. The redaction is
  string-level on the digest blob to avoid leaking secrets into a
  long-lived, model-readable ``<session_memory>`` block.
"""

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

# Wave H §H1: secret/PII redaction patterns. Each entry is a (regex, replacement)
# pair. Patterns are intentionally loose — a small false-positive on a benign
# blob is preferable to a leaked credential surviving into ``session_summary``.
_RE_OPENAI_KEY = re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b")
_RE_ANTHROPIC_KEY = re.compile(r"\bsk-ant-[A-Za-z0-9_-]{16,}\b")
_RE_OPENROUTER_KEY = re.compile(r"\bsk-or-[A-Za-z0-9_-]{16,}\b")
_RE_BEARER = re.compile(r"\b[Bb]earer\s+[A-Za-z0-9._\-]{16,}\b")
_RE_AWS_ACCESS_KEY = re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")
_RE_AWS_SECRET = re.compile(r"\baws_secret_access_key\s*[:=]\s*[\"']?([A-Za-z0-9/+=]{30,})[\"']?")
_RE_GENERIC_API_KEY = re.compile(
    r"\b(?:api[_-]?key|api_token|access_token)\s*[:=]\s*[\"']?([A-Za-z0-9._\-]{16,})[\"']?",
    re.IGNORECASE,
)
_RE_GITHUB_TOKEN = re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b")
_RE_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")


def _redact_generic_api_key_match(match: re.Match[str]) -> str:
    """Keep the ``api_key=`` lvalue verbatim, redact only the captured value."""
    full = match.group(0)
    secret = match.group(1)
    if not secret:
        return full
    return full.replace(secret, "[REDACTED:api_key]")


def redact_sensitive_material(text: str) -> str:
    """Replace API key / bearer / AWS / email shapes with stable ``[REDACTED:<kind>]``.

    Stability matters: the helper is invoked **before** ``run_side_llm_chat`` so the
    cache-stable prefix property of L4 compact is preserved across turns even when
    secrets briefly leaked into a single digest.
    """
    s = str(text or "")
    if not s:
        return s
    s = _RE_ANTHROPIC_KEY.sub("[REDACTED:anthropic_api_key]", s)
    s = _RE_OPENROUTER_KEY.sub("[REDACTED:openrouter_api_key]", s)
    s = _RE_GITHUB_TOKEN.sub("[REDACTED:github_token]", s)
    s = _RE_OPENAI_KEY.sub("[REDACTED:openai_api_key]", s)
    s = _RE_BEARER.sub("Bearer [REDACTED:bearer_token]", s)
    s = _RE_AWS_ACCESS_KEY.sub("[REDACTED:aws_access_key]", s)
    s = _RE_AWS_SECRET.sub("aws_secret_access_key=[REDACTED:aws_secret]", s)
    s = _RE_GENERIC_API_KEY.sub(_redact_generic_api_key_match, s)
    s = _RE_EMAIL.sub("[REDACTED:email]", s)
    return s


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
    """Return a shallow copy with long text fields scrubbed for L4 digest compaction.

    Scrubs (in this order):

    1. Reinjected XML markers (Train T2) so digest does not double-include them.
    2. API keys / bearer tokens / AWS keys / emails (Wave H §H1) so secrets that
       briefly appeared in a tool payload do not survive into ``session_summary``.
    """
    out = dict(d)
    for key in ("user_intent", "answer_excerpt"):
        if key in out and isinstance(out[key], str):
            cleaned = _strip_reinjected_markers(out[key])
            out[key] = redact_sensitive_material(cleaned)
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
