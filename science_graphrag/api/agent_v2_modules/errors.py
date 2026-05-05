"""Error normalization helpers for Agent API v2."""

from __future__ import annotations


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
