"""LLM factory for agent runtime."""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from science_graphrag.config import Settings


def build_chat_model(
    settings: Settings,
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> ChatOpenAI:
    """Build ChatOpenAI client pointing to OpenRouter-compatible endpoint."""
    return ChatOpenAI(
        model=settings.extraction_llm_model,
        api_key=settings.extraction_llm_api_key,
        base_url=settings.extraction_llm_base_url,
        temperature=temperature if temperature is not None else settings.agent_chat_temperature,
        max_tokens=max_tokens if max_tokens is not None else settings.agent_chat_max_tokens,
        timeout=settings.extraction_llm_timeout_seconds,
    )
