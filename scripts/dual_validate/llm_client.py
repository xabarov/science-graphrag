"""OpenAI-compatible LLM wrapper used by the dual-validate extractors.

Resolves base URL / API key / model the same way ``scripts/teacher_llm_settings.py``
does for layer-1 teacher gold: CLI > ``benchmark_teacher_*`` > ``extraction_llm_*``.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass

from openai import APIError, OpenAI, RateLimitError

from science_graphrag.config import Settings


@dataclass(frozen=True)
class LLMCallSpec:
    """Single chat-completion request specification."""

    model: str
    base_url: str
    system_prompt: str
    user_prompt: str
    temperature: float = 0.1
    max_tokens: int = 2048
    response_format: str = "json_object"


@dataclass(frozen=True)
class LLMCallResult:
    """Wrapped response with provenance + a stable prompt hash for the report."""

    content: str
    prompt_hash: str
    latency_ms: int
    finish_reason: str | None
    usage_tokens: dict[str, int]


def prompt_hash(spec: LLMCallSpec) -> str:
    """Stable SHA-256 hash of all fields that influence the model output."""

    payload = json.dumps(
        {
            "model": spec.model,
            "base_url": spec.base_url,
            "system_prompt": spec.system_prompt,
            "user_prompt": spec.user_prompt,
            "temperature": spec.temperature,
            "response_format": spec.response_format,
        },
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


class DualValidateLLMClient:
    """Synchronous OpenRouter-compatible client with one retry on rate limit."""

    def __init__(self, *, api_key: str, base_url: str, timeout_seconds: float = 120.0) -> None:
        self._client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout_seconds)

    def call(self, spec: LLMCallSpec, *, max_retries: int = 2) -> LLMCallResult:
        """Run one chat completion; retry once on transient errors."""

        last_err: Exception | None = None
        for attempt in range(max_retries):
            t0 = time.perf_counter()
            try:
                resp = self._client.chat.completions.create(
                    model=spec.model,
                    messages=[
                        {"role": "system", "content": spec.system_prompt},
                        {"role": "user", "content": spec.user_prompt},
                    ],
                    temperature=spec.temperature,
                    max_tokens=spec.max_tokens,
                    response_format={"type": spec.response_format},
                )
                latency_ms = int((time.perf_counter() - t0) * 1000)
                choice = resp.choices[0]
                usage = getattr(resp, "usage", None)
                tokens = {
                    "prompt": getattr(usage, "prompt_tokens", 0) if usage else 0,
                    "completion": getattr(usage, "completion_tokens", 0) if usage else 0,
                    "total": getattr(usage, "total_tokens", 0) if usage else 0,
                }
                return LLMCallResult(
                    content=choice.message.content or "",
                    prompt_hash=prompt_hash(spec),
                    latency_ms=latency_ms,
                    finish_reason=choice.finish_reason,
                    usage_tokens=tokens,
                )
            except RateLimitError as exc:
                last_err = exc
                time.sleep(2.0 * (attempt + 1))
            except APIError as exc:
                last_err = exc
                if attempt + 1 >= max_retries:
                    break
                time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"LLM call failed after {max_retries} attempts: {last_err}")


def resolve_llm_settings(
    *,
    settings: Settings,
    cli_api_key: str | None,
    cli_base_url: str | None,
    cli_model: str | None,
) -> tuple[str, str, str]:
    """Pick api_key / base_url / model in priority order: CLI > teacher_* > extraction_*.

    Mirrors ``scripts/teacher_llm_settings.teacher_extraction_settings`` so the dual-
    validate runs hit the same OpenRouter account as the existing teacher-gold tooling.
    """

    api = (
        (cli_api_key or "").strip()
        or (settings.benchmark_teacher_llm_api_key or "").strip()
        or (settings.extraction_llm_api_key or "").strip()
    )
    base = (
        (cli_base_url or "").strip()
        or (settings.benchmark_teacher_llm_base_url or "").strip()
        or (settings.extraction_llm_base_url or "").strip()
        or "https://openrouter.ai/api/v1"
    )
    model = (
        (cli_model or "").strip()
        or (settings.benchmark_teacher_llm_model or "").strip()
        or "deepseek/deepseek-v3.2"
    )
    if not api:
        raise RuntimeError(
            "No API key found (set MAIN_LLM_API_KEY / "
            "SCIENCE_GRAPHRAG_BENCHMARK_TEACHER_LLM_API_KEY or pass --api-key)."
        )
    return api, base, model
