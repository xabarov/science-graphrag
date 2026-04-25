"""OpenAI-compatible LLM wrapper used by the dual-validate extractors.

Resolves base URL / API key / model the same way ``scripts/teacher_llm_settings.py``
does for layer-1 teacher gold: CLI > ``benchmark_teacher_*`` > ``extraction_llm_*``.
"""

from __future__ import annotations

import hashlib
import json
import random
import time
from dataclasses import dataclass
from typing import Any

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
    # OpenRouter ``reasoning`` knob — only emitted when not None. Use one of:
    #   {"enabled": False}                       — strict no-CoT
    #   {"effort": "low"|"medium"|"high"}        — bounded CoT effort
    #   {"max_tokens": <int>}                    — explicit CoT budget
    # Required for reasoning models such as ``moonshotai/kimi-k2.6`` whose hidden
    # CoT can starve the JSON output budget when left unbounded.
    reasoning: dict[str, Any] | None = None


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
            "reasoning": spec.reasoning,
        },
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


class DualValidateLLMClient:
    """Synchronous OpenRouter-compatible client with one retry on rate limit."""

    def __init__(self, *, api_key: str, base_url: str, timeout_seconds: float = 120.0) -> None:
        self._client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout_seconds)

    def call(self, spec: LLMCallSpec, *, max_retries: int = 5) -> LLMCallResult:
        """Run one chat completion with jittered exponential backoff on transients.

        Honours OpenRouter ``retry_after_seconds`` metadata when the upstream
        provider supplies it; otherwise falls back to ``2 ** attempt`` (capped at
        30s) plus a small random jitter so parallel callers don't synchronise.
        """

        last_err: Exception | None = None
        for attempt in range(max_retries):
            t0 = time.perf_counter()
            try:
                # OpenRouter ``reasoning`` knob travels via ``extra_body`` so that the
                # OpenAI SDK forwards it untouched. We only emit it when explicitly
                # requested — otherwise providers fall back to their default behaviour.
                extra_body: dict[str, Any] | None = None
                if spec.reasoning is not None:
                    extra_body = {"reasoning": dict(spec.reasoning)}
                resp = self._client.chat.completions.create(
                    model=spec.model,
                    messages=[
                        {"role": "system", "content": spec.system_prompt},
                        {"role": "user", "content": spec.user_prompt},
                    ],
                    temperature=spec.temperature,
                    max_tokens=spec.max_tokens,
                    response_format={"type": spec.response_format},
                    extra_body=extra_body,
                )
                latency_ms = int((time.perf_counter() - t0) * 1000)
                # OpenRouter occasionally returns 200-OK envelopes whose ``choices``
                # are empty/None (provider failure surfaces as ``error`` field instead).
                # Surface that as a retryable RuntimeError rather than a confusing
                # ``'NoneType' object is not subscriptable`` from ``resp.choices[0]``.
                choices = getattr(resp, "choices", None) or []
                if not choices:
                    err_field = getattr(resp, "error", None)
                    last_err = RuntimeError(
                        f"empty choices from upstream "
                        f"(provider error={err_field!r}, model={spec.model})"
                    )
                    time.sleep(_compute_backoff(attempt, hint=None))
                    continue
                choice = choices[0]
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
                time.sleep(_compute_backoff(attempt, hint=_extract_retry_after(exc)))
            except APIError as exc:
                last_err = exc
                # 5xx responses from upstream providers (Together/etc.) are usually
                # transient. Treat them like rate limits — back off and retry.
                if attempt + 1 >= max_retries:
                    break
                time.sleep(_compute_backoff(attempt, hint=_extract_retry_after(exc)))
        raise RuntimeError(f"LLM call failed after {max_retries} attempts: {last_err}")


def _extract_retry_after(exc: Exception) -> float | None:
    """Mine ``retry_after_seconds`` out of OpenRouter's nested error metadata."""

    body = getattr(exc, "body", None) or getattr(exc, "response", None)
    if body is None:
        return None
    try:
        if hasattr(body, "json"):
            payload = body.json()
        elif isinstance(body, (bytes, str)):
            payload = json.loads(body)
        else:
            payload = body
        meta = payload.get("error", {}).get("metadata", {}) if isinstance(payload, dict) else {}
        ra = meta.get("retry_after_seconds")
        return float(ra) if ra is not None else None
    except (json.JSONDecodeError, AttributeError, TypeError, ValueError):
        return None


def _compute_backoff(attempt: int, *, hint: float | None, cap: float = 30.0) -> float:
    """Exponential backoff (2^attempt) clamped to ``cap`` seconds, plus jitter.

    When the upstream supplied a ``retry_after_seconds`` hint we respect it
    (with a small jitter) — this avoids hammering a provider that explicitly
    asked us to wait longer.
    """

    base = max(hint, 1.0) if hint is not None else min(2.0**attempt, cap)
    jitter = random.uniform(0.0, 0.5)
    return base + jitter


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
