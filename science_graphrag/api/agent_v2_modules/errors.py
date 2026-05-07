"""Error normalization helpers for Agent API v2."""

from __future__ import annotations

import json
from typing import Final

from langchain_core.exceptions import OutputParserException
from langgraph.errors import GraphRecursionError
from pydantic import ValidationError

from science_graphrag.agent.graph.errors import (
    AgentGraphDeadlineExceeded,
    AgentGraphRecursionLimitExceeded,
)

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]

# HTTP status codes commonly returned by gateways / edge proxies on overload or upstream timeout.
_PROVIDER_GATEWAY_HTTP_CODES: Final[frozenset[int]] = frozenset({502, 503, 504, 524})

# Classes treated as external / transport flakes for live gates (not product regressions).
RETRYABLE_PROVIDER_ERROR_CLASSES: Final[frozenset[str]] = frozenset(
    {
        "provider_gateway_error",
        "provider_timeout",
        "provider_unreachable",
    }
)


def is_retryable_provider_error_class(error_class: str) -> bool:
    """True when ``error_class`` is a known transient upstream/edge failure."""
    return str(error_class or "").strip() in RETRYABLE_PROVIDER_ERROR_CLASSES


def classify_agent_stream_error(exc: BaseException) -> tuple[str, str]:
    """Return ``(error_class, short_message)`` for SSE ``error`` events.

    ``error_class`` is a stable enum the UI can localize via
    ``chat.errors.<error_class>`` keys; ``short_message`` is a safe English
    summary suitable as a fallback when the UI has no translation yet.

    Recognized classes:

    - ``provider_unauthorized`` — 401 from upstream LLM (bad / missing key).
    - ``provider_forbidden`` — 403 from upstream LLM (quota / region).
    - ``provider_rejected`` — other upstream LLM HTTP errors (4xx / 5xx with
      explicit code), excluding gateway overload codes (see ``provider_gateway_error``).
    - ``provider_gateway_error`` — edge/gateway overload or upstream timeout (502/503/504/524).
    - ``provider_timeout`` — request timed out before reaching us.
    - ``provider_unreachable`` — transport-level failure (DNS, refused).
    - ``agent_turn_deadline_exceeded`` — per-turn LangGraph / stream deadline.
    - ``agent_recursion_limit`` — LangGraph hit its hard ``recursion_limit`` for the turn.
    - ``llm_output_validation_error`` — Pydantic / structured output validation.
    - ``llm_output_parse_error`` — JSON parse failures on model output.
    - ``internal_error`` — anything else, including unknown exception types.
    """
    if isinstance(exc, AgentGraphDeadlineExceeded):
        return (
            "agent_turn_deadline_exceeded",
            "The assistant run exceeded the server time limit for one turn.",
        )
    if isinstance(exc, (AgentGraphRecursionLimitExceeded, GraphRecursionError)):
        return (
            "agent_recursion_limit",
            "The reasoning graph hit its hard step limit before finishing.",
        )
    if isinstance(exc, ValidationError):
        return (
            "llm_output_validation_error",
            "The model returned structured output that failed validation.",
        )
    if isinstance(exc, OutputParserException):
        return (
            "llm_output_parse_error",
            "The model output could not be parsed into the expected schema.",
        )
    if isinstance(exc, json.JSONDecodeError):
        return ("llm_output_parse_error", "The model returned invalid JSON.")

    if httpx is not None and isinstance(exc, httpx.HTTPStatusError):
        code = int(exc.response.status_code)
        if code in _PROVIDER_GATEWAY_HTTP_CODES:
            return (
                "provider_gateway_error",
                f"Upstream gateway or edge error (HTTP {code}).",
            )
        if code == 401:
            return "provider_unauthorized", "Upstream LLM rejected the API key (401)."
        if code == 403:
            return "provider_forbidden", "Upstream LLM access denied (403)."
        return (
            "provider_rejected",
            f"Upstream HTTP error (HTTP {code}).",
        )

    if isinstance(exc, ValueError) and exc.args:
        arg0 = exc.args[0]
        if isinstance(arg0, dict):
            code = arg0.get("code")
            msg = str(arg0.get("message") or "provider error").strip()[:200]
            try:
                code_int = int(code) if code is not None else None
            except (TypeError, ValueError):
                code_int = None
            if code_int == 401:
                return "provider_unauthorized", "Upstream LLM rejected the API key (401)."
            if code_int == 403:
                return "provider_forbidden", "Upstream LLM access denied (403)."
            if code_int is not None and code_int in _PROVIDER_GATEWAY_HTTP_CODES:
                return (
                    "provider_gateway_error",
                    f"Upstream gateway or edge error (HTTP {code_int}): {msg}",
                )
            if code_int is not None:
                return (
                    "provider_rejected",
                    f"Upstream LLM rejected the request (code {code_int}): {msg}",
                )
            return "provider_rejected", f"Upstream LLM error: {msg}"
    detail = str(exc).lower()
    name = type(exc).__name__.lower()
    if "timeout" in name:
        return "provider_timeout", "Upstream LLM call timed out."
    if "timeout" in detail or "timed out" in detail:
        return "provider_timeout", "Upstream LLM call timed out."
    if "validationerror" in name or "validation error" in detail:
        return (
            "llm_output_validation_error",
            "The model returned structured output that failed validation.",
        )
    if "jsondecodeerror" in name or "expecting value" in detail:
        return ("llm_output_parse_error", "The model returned invalid JSON.")
    if "outputparserexception" in name or "output parser" in detail:
        return (
            "llm_output_parse_error",
            "The model output could not be parsed into the expected schema.",
        )
    if "connection" in name or "unreachable" in name:
        return "provider_unreachable", "Upstream LLM was unreachable."
    if any(
        marker in detail
        for marker in (
            "connection refused",
            "name or service not known",
            "temporary failure in name resolution",
            "network is unreachable",
        )
    ):
        return "provider_unreachable", "Upstream LLM was unreachable."
    return "internal_error", str(exc)[:200] or "Internal error during agent run."


def format_agent_stream_error(exc: BaseException) -> str:
    """Map common LangChain/OpenRouter failures to short UI-facing text."""
    if isinstance(exc, ValueError) and exc.args:
        arg0 = exc.args[0]
        if isinstance(arg0, dict):
            msg = str(arg0.get("message") or "provider error").strip()
            code = arg0.get("code")
            meta = arg0.get("metadata")
            raw_hint = ""
            if isinstance(meta, dict):
                raw = meta.get("raw")
                if isinstance(raw, str) and raw.strip():
                    raw_hint = f" — {raw.strip()[:280]}"
            if code is not None:
                return f"Upstream LLM rejected the request (code {code}): {msg}{raw_hint}"
            return f"Upstream LLM error: {msg}{raw_hint}"
        if isinstance(arg0, str) and arg0.strip():
            return arg0.strip()
    return str(exc)
