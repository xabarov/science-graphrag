"""Sync OpenAI-compatible client + instructor for structured extraction."""

from __future__ import annotations

from typing import TypeVar

import instructor
from openai import OpenAI
from pydantic import BaseModel

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
        self._client = instructor.from_openai(raw)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

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
        try:
            result = self._client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_model=instructor.Maybe(response_model),
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
        except Exception as exc:  # noqa: BLE001
            return None, f"{type(exc).__name__}: {exc}"

        if getattr(result, "error", False):
            return None, str(getattr(result, "message", None) or "llm_maybe_error")

        parsed = getattr(result, "result", None)
        if parsed is None:
            return None, "llm_empty_result"
        return parsed, None
