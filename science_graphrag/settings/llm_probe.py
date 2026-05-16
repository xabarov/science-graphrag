"""LLM connectivity probe helpers for settings service."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Callable

from openai import OpenAI


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def run_llm_connection_probe(
    *,
    base_url: str,
    model: str,
    timeout_seconds: float,
    temperature: float,
    api_key: str | None,
    used_saved_secret: bool,
    completion_factory: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Run OpenAI-compatible connection probe and normalize result payload."""
    if not api_key:
        return {
            "status": "error",
            "error_kind": "missing_api_key",
            "message": (
                "API key is not configured (set SCIENCE_GRAPHRAG_API_KEY or "
                "SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY, save a key in Settings, "
                "or pass api_key in the draft request). For Ollama local endpoints use a "
                "non-empty placeholder such as ollama (Ollama ignores it but OpenAI clients "
                "require it)."
            ),
            "resolved": {
                "base_url": base_url,
                "model": model,
                "timeout_seconds": timeout_seconds,
                "temperature": temperature,
                "used_saved_secret": False,
            },
        }

    started = datetime.now(tz=UTC)
    try:
        if completion_factory is None:
            client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout_seconds)
            completion = client.chat.completions.create(
                model=model,
                temperature=temperature,
                max_tokens=12,
                messages=[
                    {"role": "system", "content": "Reply with exactly OK."},
                    {"role": "user", "content": "Connection test. Reply OK."},
                ],
            )
        else:
            completion = completion_factory(
                api_key=api_key,
                base_url=base_url,
                timeout_seconds=timeout_seconds,
                model=model,
                temperature=temperature,
            )
        reply = (completion.choices[0].message.content if completion and completion.choices else None) or ""
        elapsed_ms = int((datetime.now(tz=UTC) - started).total_seconds() * 1000)
        normalized = reply.strip()
        return {
            "status": "connected" if normalized.upper() == "OK" else "unexpected_response",
            "message": normalized or "No response text returned by provider.",
            "latency_ms": elapsed_ms,
            "tested_at": _now_iso(),
            "resolved": {
                "base_url": base_url,
                "model": model,
                "timeout_seconds": timeout_seconds,
                "temperature": temperature,
                "used_saved_secret": used_saved_secret,
            },
        }
    except Exception as exc:  # noqa: BLE001
        text = str(exc)
        lower = text.lower()
        if "401" in lower or "unauthorized" in lower or "invalid api key" in lower:
            error_kind = "auth_failed"
        elif "404" in lower or "model" in lower and "not found" in lower:
            error_kind = "model_unavailable"
        elif "timeout" in lower:
            error_kind = "timeout"
        else:
            error_kind = "provider_error"
        return {
            "status": "error",
            "error_kind": error_kind,
            "message": text,
            "tested_at": _now_iso(),
            "resolved": {
                "base_url": base_url,
                "model": model,
                "timeout_seconds": timeout_seconds,
                "temperature": temperature,
                "used_saved_secret": used_saved_secret,
            },
        }

