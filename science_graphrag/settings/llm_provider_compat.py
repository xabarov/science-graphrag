"""Heuristics for OpenAI-compatible provider endpoints (Ollama, vLLM, OpenRouter)."""

from __future__ import annotations

from urllib.parse import urlparse


def is_probable_ollama_base_url(base_url: str | None) -> bool:
    """True when base URL looks like Ollama's OpenAI-compatible server (port 11434, /v1)."""

    raw = str(base_url or "").strip()
    if not raw:
        return False
    try:
        parsed = urlparse(raw)
    except ValueError:
        return False
    path = (parsed.path or "").rstrip("/") or ""
    if path != "/v1":
        return False
    return "11434" in (parsed.netloc or "")


def build_llm_provider_compatibility_diagnostics(
    *,
    extraction_base_url: str,
    chat_base_url: str,
    embeddings_base_url: str,
) -> dict[str, object]:
    """Operator-facing hints for settings snapshot (no provider-specific runtime mode)."""

    urls = (extraction_base_url, chat_base_url, embeddings_base_url)
    probable_ollama = any(is_probable_ollama_base_url(u) for u in urls)
    hints: list[str] = []
    if probable_ollama:
        hints.append(
            "probable_ollama: OpenAI-compatible /v1 on port 11434. "
            "Ollama ignores the API key but clients require a non-empty value (e.g. ollama). "
            "Pull models with `ollama pull` before use. Embeddings: POST /v1/embeddings."
        )
    return {
        "probable_ollama_endpoint": probable_ollama,
        "hints": hints,
    }


__all__ = [
    "build_llm_provider_compatibility_diagnostics",
    "is_probable_ollama_base_url",
]
