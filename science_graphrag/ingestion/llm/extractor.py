"""Sync OpenAI-compatible client + instructor for structured extraction."""

from __future__ import annotations

import json
from typing import Any, TypeVar

import instructor
from openai import OpenAI
from pydantic import BaseModel

from science_graphrag.observability.phoenix_tracer import SpanAttributes, set_span_error

T = TypeVar("T", bound=BaseModel)


class SyncInstructorExtractor:
    """Thin wrapper: chat.completions with instructor.Maybe for soft failures."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        timeout_seconds: float = 180.0,
    ) -> None:
        raw = OpenAI(
            api_key=api_key,
            base_url=base_url.rstrip("/"),
            timeout=timeout_seconds,
        )
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._extra_body = self._build_extra_body()
        self._client = instructor.from_openai(raw, mode=self._resolve_mode())

    def _is_openrouter_qwen35_397b(self) -> bool:
        return self.base_url.startswith("https://openrouter.ai/api") and (
            self.model.strip().lower() == "qwen/qwen3.5-397b-a17b"
        )

    def _resolve_mode(self) -> instructor.Mode:
        # OpenRouter + Qwen3.5 397B currently behaves better via structured outputs
        # than via the default TOOLS mode used by instructor.
        if self._is_openrouter_qwen35_397b():
            return instructor.Mode.OPENROUTER_STRUCTURED_OUTPUTS
        return instructor.Mode.TOOLS

    def _build_extra_body(self) -> dict[str, Any] | None:
        if not self._is_openrouter_qwen35_397b():
            return None
        return {
            "provider": {"require_parameters": True},
            # Qwen 3.5 on OpenRouter has known JSON issues when reasoning is disabled.
            "reasoning": {
                "enabled": True,
                "effort": "medium",
            },
        }

    @staticmethod
    def _extract_usage(result: Any) -> tuple[int | None, int | None, int | None]:
        usage = getattr(result, "usage", None)
        if usage is None:
            usage = getattr(getattr(result, "_raw_response", None), "usage", None)
        if usage is None:
            usage = getattr(getattr(result, "raw_response", None), "usage", None)
        if usage is None:
            return None, None, None

        def _to_int(value: Any) -> int | None:
            if value is None:
                return None
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        if isinstance(usage, dict):
            prompt_tokens = _to_int(usage.get("prompt_tokens"))
            completion_tokens = _to_int(usage.get("completion_tokens"))
            total_tokens = _to_int(usage.get("total_tokens"))
            return prompt_tokens, completion_tokens, total_tokens

        prompt_tokens = _to_int(getattr(usage, "prompt_tokens", None))
        completion_tokens = _to_int(getattr(usage, "completion_tokens", None))
        total_tokens = _to_int(getattr(usage, "total_tokens", None))
        return prompt_tokens, completion_tokens, total_tokens

    @staticmethod
    def _assistant_payload(parsed: BaseModel | None, fallback_message: str | None = None) -> str:
        if parsed is not None:
            return json.dumps(parsed.model_dump(mode="json"), ensure_ascii=False)
        if fallback_message:
            return fallback_message
        return ""

    def extract_maybe(
        self,
        response_model: type[T],
        *,
        system: str,
        user: str,
    ) -> tuple[T | None, str | None]:
        """
        Returns (parsed_model, None) on success, (None, error_message) on failure.

        Uses instructor.Maybe so the model can refuse / signal failure without exceptions.
        """
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        prompt_text = f"SYSTEM:\n{system}\n\nUSER:\n{user}"
        SpanAttributes.set_llm_attrs(
            self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            base_url=self.base_url,
        )
        SpanAttributes.set_llm_invocation_parameters(
            {
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "response_model": response_model.__name__,
            }
        )
        SpanAttributes.set_llm_input_messages(messages)
        SpanAttributes.set_input(
            {
                "response_model": response_model.__name__,
                "messages": messages,
            }
        )

        try:
            create_kwargs: dict[str, Any] = {
                "model": self.model,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "response_model": instructor.Maybe(response_model),
                "messages": messages,
            }
            if self._extra_body is not None:
                create_kwargs["extra_body"] = self._extra_body
            result = self._client.chat.completions.create(
                **create_kwargs,
            )
        except Exception as exc:  # noqa: BLE001
            set_span_error(exc)
            error_text = f"{type(exc).__name__}: {exc}"
            SpanAttributes.set_output({"error": error_text})
            SpanAttributes.set_llm_output_messages([{"role": "assistant", "content": error_text}])
            SpanAttributes.set_llm_token_counts_from_text(
                prompt_text=prompt_text,
                completion_text=error_text,
                usage_source="estimated_error",
            )
            return None, f"{type(exc).__name__}: {exc}"

        if getattr(result, "error", False):
            error_text = str(getattr(result, "message", None) or "llm_maybe_error")
            SpanAttributes.set_output({"error": error_text})
            SpanAttributes.set_llm_output_messages([{"role": "assistant", "content": error_text}])
            SpanAttributes.set_llm_token_counts_from_text(
                prompt_text=prompt_text,
                completion_text=error_text,
                usage_source="estimated_maybe_error",
            )
            return None, error_text

        parsed = getattr(result, "result", None)
        assistant_text = self._assistant_payload(parsed)
        SpanAttributes.set_output(assistant_text or {"status": "empty"})
        SpanAttributes.set_llm_output_messages(
            [{"role": "assistant", "content": assistant_text or "llm_empty_result"}]
        )
        prompt_tokens, completion_tokens, total_tokens = self._extract_usage(result)
        if prompt_tokens is not None or completion_tokens is not None or total_tokens is not None:
            SpanAttributes.set_llm_token_counts(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                usage_source="api",
            )
        else:
            SpanAttributes.set_llm_token_counts_from_text(
                prompt_text=prompt_text,
                completion_text=assistant_text or "llm_empty_result",
            )
        if parsed is None:
            return None, "llm_empty_result"
        return parsed, None
