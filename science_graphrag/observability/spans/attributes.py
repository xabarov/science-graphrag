from __future__ import annotations

import json
import os
from typing import Any

from science_graphrag.observability.spans.decorators import (
    DEFAULT_SPAN_PAYLOAD_LIMIT,
    MIME_TYPE_JSON,
    MIME_TYPE_TEXT,
    OpenInferenceAttributes,
    set_span_attribute,
)


class SpanAttributes:
    """Helpers for OpenInference-compatible Phoenix attributes."""

    @staticmethod
    def _system_from_model(model: str | None) -> str | None:
        if not model:
            return None
        provider_hint = model.lower().split("/", maxsplit=1)[0]
        known = {
            "anthropic": "anthropic",
            "cohere": "cohere",
            "deepseek": "deepseek",
            "google": "google",
            "groq": "groq",
            "meta": "meta",
            "mistralai": "mistralai",
            "openai": "openai",
            "xai": "xai",
        }
        return known.get(provider_hint)

    @staticmethod
    def _provider_from_model(model: str | None) -> str | None:
        if not model:
            return None
        model_l = model.lower()
        if "/" in model_l:
            prefix = model_l.split("/", maxsplit=1)[0]
            return {
                "anthropic": "anthropic",
                "cohere": "cohere",
                "deepseek": "deepseek",
                "google": "google",
                "groq": "groq",
                "meta": "meta",
                "mistralai": "mistralai",
                "openai": "openai",
                "xai": "xai",
            }.get(prefix, prefix)
        if model_l.startswith(("gpt", "o1", "o3", "o4")):
            return "openai"
        if model_l.startswith("claude"):
            return "anthropic"
        if model_l.startswith("gemini"):
            return "google"
        if model_l.startswith("mistral"):
            return "mistralai"
        return None

    @staticmethod
    def _provider_from_base_url(base_url: str | None) -> str | None:
        if not base_url:
            return None
        url = base_url.lower()
        if "openrouter.ai" in url:
            return "openrouter"
        if "api.openai.com" in url:
            return "openai"
        if "anthropic.com" in url:
            return "anthropic"
        if "googleapis.com" in url or "generativelanguage.googleapis.com" in url:
            return "google"
        if "localhost" in url or "127.0.0.1" in url:
            return "local"
        return None

    @staticmethod
    def _safe_json(value: Any, *, limit: int | None = None) -> str:
        if isinstance(value, str):
            serialized = value
        else:
            try:
                serialized = json.dumps(value, ensure_ascii=False, default=str)
            except TypeError:
                serialized = str(value)
        max_len = (
            limit
            if limit is not None
            else int(os.getenv("PHOENIX_SPAN_IO_MAX_LEN", str(DEFAULT_SPAN_PAYLOAD_LIMIT)))
        )
        if max_len > 0 and len(serialized) > max_len:
            return serialized[:max_len] + "...[truncated]"
        return serialized

    @staticmethod
    def set_input(value: str | dict[str, Any] | list[Any], mime_type: str = MIME_TYPE_TEXT) -> None:
        if isinstance(value, (dict, list)):
            value = SpanAttributes._safe_json(value)
            mime_type = MIME_TYPE_JSON
        set_span_attribute(OpenInferenceAttributes.INPUT_VALUE, value)
        set_span_attribute(OpenInferenceAttributes.INPUT_MIME_TYPE, mime_type)

    @staticmethod
    def set_output(
        value: str | dict[str, Any] | list[Any], mime_type: str = MIME_TYPE_TEXT
    ) -> None:
        if isinstance(value, (dict, list)):
            value = SpanAttributes._safe_json(value)
            mime_type = MIME_TYPE_JSON
        set_span_attribute(OpenInferenceAttributes.OUTPUT_VALUE, value)
        set_span_attribute(OpenInferenceAttributes.OUTPUT_MIME_TYPE, mime_type)

    @staticmethod
    def set_llm_attrs(
        model: str,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
        base_url: str | None = None,
    ) -> None:
        set_span_attribute("llm.model_name", model)
        system = SpanAttributes._system_from_model(model)
        if system:
            set_span_attribute("llm.system", system)
        provider = SpanAttributes._provider_from_base_url(
            base_url
        ) or SpanAttributes._provider_from_model(model)
        if provider:
            set_span_attribute("llm.provider", provider)
        if temperature is not None:
            set_span_attribute("llm.temperature", temperature)
        if max_tokens is not None:
            set_span_attribute("llm.max_tokens", max_tokens)
        SpanAttributes.set_llm_token_counts(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            usage_source="api",
        )

    @staticmethod
    def set_llm_invocation_parameters(parameters: dict[str, Any]) -> None:
        set_span_attribute("llm.invocation_parameters", SpanAttributes._safe_json(parameters))

    @staticmethod
    def _set_message_attributes(prefix: str, message: dict[str, Any]) -> None:
        role = message.get("role")
        content = message.get("content")
        name = message.get("name")
        if role:
            set_span_attribute(f"{prefix}.message.role", str(role))
        if name:
            set_span_attribute(f"{prefix}.message.name", str(name))
        if content is not None:
            set_span_attribute(f"{prefix}.message.content", SpanAttributes._safe_json(content))

        tool_calls = message.get("tool_calls")
        if isinstance(tool_calls, list):
            for idx, tool_call in enumerate(tool_calls):
                if not isinstance(tool_call, dict):
                    continue
                call_prefix = f"{prefix}.message.tool_calls.{idx}"
                tool_call_id = tool_call.get("id")
                function_payload = tool_call.get("function") or {}
                if tool_call_id:
                    set_span_attribute(f"{call_prefix}.tool_call.id", str(tool_call_id))
                if isinstance(function_payload, dict):
                    function_name = function_payload.get("name")
                    function_args = function_payload.get("arguments")
                    if function_name:
                        set_span_attribute(
                            f"{call_prefix}.tool_call.function.name", str(function_name)
                        )
                    if function_args is not None:
                        set_span_attribute(
                            f"{call_prefix}.tool_call.function.arguments",
                            SpanAttributes._safe_json(function_args),
                        )

    @staticmethod
    def set_llm_input_messages(messages: list[dict[str, Any]]) -> None:
        for idx, message in enumerate(messages):
            SpanAttributes._set_message_attributes(f"llm.input_messages.{idx}", message)

    @staticmethod
    def set_llm_output_messages(messages: list[dict[str, Any]]) -> None:
        for idx, message in enumerate(messages):
            SpanAttributes._set_message_attributes(f"llm.output_messages.{idx}", message)

    @staticmethod
    def estimate_token_count(text: str | None) -> int:
        if not text:
            return 0
        normalized = " ".join(text.split())
        if not normalized:
            return 0
        return max(1, (len(normalized) + 3) // 4)

    @staticmethod
    def set_llm_token_counts(
        *,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
        usage_source: str = "api",
    ) -> None:
        if prompt_tokens is not None:
            set_span_attribute("llm.token_count.prompt", int(prompt_tokens))
        if completion_tokens is not None:
            set_span_attribute("llm.token_count.completion", int(completion_tokens))
        computed_total = total_tokens
        if computed_total is None and prompt_tokens is not None and completion_tokens is not None:
            computed_total = int(prompt_tokens) + int(completion_tokens)
        if computed_total is not None:
            set_span_attribute("llm.token_count.total", int(computed_total))
        set_span_attribute("llm.usage_source", usage_source)

    @staticmethod
    def set_llm_token_counts_from_text(
        *,
        prompt_text: str,
        completion_text: str,
        usage_source: str = "estimated",
    ) -> None:
        SpanAttributes.set_llm_token_counts(
            prompt_tokens=SpanAttributes.estimate_token_count(prompt_text),
            completion_tokens=SpanAttributes.estimate_token_count(completion_text),
            usage_source=usage_source,
        )

    @staticmethod
    def set_tool_attrs(
        tool_name: str, tool_type: str = "tool", tool_description: str | None = None
    ) -> None:
        set_span_attribute("tool.name", tool_name)
        set_span_attribute("tool.type", tool_type)
        if tool_description:
            set_span_attribute("tool.description", tool_description)

    @staticmethod
    def set_tool_parameters(parameters: dict[str, Any] | list[Any] | str) -> None:
        set_span_attribute("tool.parameters", SpanAttributes._safe_json(parameters))
