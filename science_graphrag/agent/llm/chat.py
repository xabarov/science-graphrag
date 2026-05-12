"""LLM factory for agent runtime."""

from __future__ import annotations

from typing import Any, Sequence

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI

from science_graphrag.config import Settings


def agent_chat_transport_max_attempts(settings: Settings) -> int:
    """Upper bound on HTTP attempts for one agent chat ``invoke`` (1 + LangChain max_retries)."""

    return max(1, int(settings.agent_chat_max_retries) + 1)


def agent_classifier_transport_max_attempts(settings: Settings) -> int:
    """Upper bound on HTTP attempts for classifier ``invoke``."""

    return max(1, int(settings.agent_classifier_max_retries) + 1)


def effective_chat_llm_model(settings: Settings) -> str:
    """Model id for research chat; optional ``chat_llm_model`` overrides extraction default."""
    override = (getattr(settings, "chat_llm_model", None) or "").strip()
    if override:
        return override
    return (settings.extraction_llm_model or "").strip()


# Some OpenRouter / vLLM backends reject requests where the final chat turn is an
# assistant message while the client sets add_generation_prompt=True (default in
# LangChain). Nudge with a user turn when subgraphs concatenate full history.
_GENERATION_SAFE_NUDGE = (
    "Continue with the next required action (tool calls or final_answer) per your "
    "specialist instructions."
)


def ensure_messages_safe_for_generation(messages: Sequence[BaseMessage]) -> list[BaseMessage]:
    """Return a copy of ``messages`` ending with a non-assistant role when needed."""
    out: list[BaseMessage] = list(messages)
    if out and isinstance(out[-1], AIMessage):
        out.append(HumanMessage(content=_GENERATION_SAFE_NUDGE))
    return out


def build_chat_model(
    settings: Settings,
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout_seconds: float | None = None,
    max_retries: int | None = None,
    model: str | None = None,
    model_kwargs: dict[str, Any] | None = None,
) -> ChatOpenAI:
    """Build ChatOpenAI client pointing to OpenRouter-compatible endpoint."""
    retries = int(settings.agent_chat_max_retries) if max_retries is None else int(max_retries)
    retries = max(0, min(2, retries))
    override_id = (model or "").strip()
    resolved_model = override_id or effective_chat_llm_model(settings)
    mk = {k: v for k, v in (model_kwargs or {}).items() if v is not None}
    params: dict[str, Any] = {
        "model": resolved_model,
        "api_key": settings.extraction_llm_api_key,
        "base_url": settings.extraction_llm_base_url,
        "temperature": temperature if temperature is not None else settings.agent_chat_temperature,
        "max_tokens": max_tokens if max_tokens is not None else settings.agent_chat_max_tokens,
        "timeout": (
            timeout_seconds
            if timeout_seconds is not None
            else settings.extraction_llm_timeout_seconds
        ),
        "max_retries": retries,
    }
    if mk:
        params["model_kwargs"] = mk
    return ChatOpenAI(**params)
