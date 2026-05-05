"""Curated OpenRouter model metadata (pricing + structured-output hints).

``OPENROUTER_POPULAR_MODEL_IDS`` follows **OpenRouter › Models › sort "Most Popular"**
(see https://openrouter.ai/models?order=most-popular). The public REST feed
``GET https://openrouter.ai/api/v1/models`` lists the same slug universe and
pricing, but **does not reproduce the site's popularity ranking** reliably
(e.g. responses may start with provider aliases such as ``~anthropic/claude-haiku-latest``),
so we keep an explicit slug order aligned to the Models UI.

Downstream uses:
- Instructor mode auto-selection for extraction (``SyncInstructorExtractor``).
- Optional reference $/1M token pricing surfaced in agent ``run_metadata`` for UI.

Refresh procedure:
  curl -fsS 'https://openrouter.ai/api/v1/models' | python -m json.tool > /tmp/or-models.json
Then diff pricing / ``supported_parameters`` for slugs here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

_OPENROUTER_BASE_URL_MARKERS: Final[tuple[str, ...]] = (
    "https://openrouter.ai/api",
    "http://openrouter.ai/api",
)

# Snapshot: 2026-05-05 — order ~ first page of Models UI "Most Popular" (resolvable API slugs).
OPENROUTER_POPULAR_MODEL_IDS: Final[tuple[str, ...]] = (
    "tencent/hy3-preview:free",
    "moonshotai/kimi-k2.6",
    "anthropic/claude-sonnet-4.6",
    "google/gemini-3-flash-preview",
    "anthropic/claude-opus-4.7",
    "deepseek/deepseek-v3.2",
    "deepseek/deepseek-v4-flash",
    "minimax/minimax-m2.7",
    "x-ai/grok-4.1-fast",
    "stepfun/step-3.5-flash",
    "google/gemini-2.5-flash-lite",
    "google/gemini-2.5-flash",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "deepseek/deepseek-v4-pro",
    "inclusionai/ling-2.6-1t:free",
    "anthropic/claude-opus-4.6",
    "openai/gpt-4o-mini",
    "qwen/qwen3-235b-a22b-2507",
    "minimax/minimax-m2.5",
    "anthropic/claude-haiku-4.5",
)


@dataclass(frozen=True, slots=True)
class OpenRouterModelProfile:
    """Static profile for a single OpenRouter model slug."""

    prompt_usd_per_1m_tokens: float
    completion_usd_per_1m_tokens: float
    openrouter_structured_outputs: bool
    requires_reasoning_extra_body: bool


# Keys MUST be lower-cased OpenRouter model ids. Union: popular page + legacy slugs still used in configs.
_OPENROUTER_MODEL_REGISTRY: Final[dict[str, OpenRouterModelProfile]] = {
    # --- "Most popular" page snapshot (2026-05-05) ---
    "tencent/hy3-preview:free": OpenRouterModelProfile(0.0, 0.0, False, False),
    "moonshotai/kimi-k2.6": OpenRouterModelProfile(0.74, 3.49, True, False),
    "anthropic/claude-sonnet-4.6": OpenRouterModelProfile(3.0, 15.0, True, False),
    "google/gemini-3-flash-preview": OpenRouterModelProfile(0.5, 3.0, True, False),
    "anthropic/claude-opus-4.7": OpenRouterModelProfile(5.0, 25.0, True, False),
    "deepseek/deepseek-v3.2": OpenRouterModelProfile(0.252, 0.378, True, False),
    "deepseek/deepseek-v4-flash": OpenRouterModelProfile(0.14, 0.28, True, False),
    "minimax/minimax-m2.7": OpenRouterModelProfile(0.3, 1.2, True, False),
    "x-ai/grok-4.1-fast": OpenRouterModelProfile(0.2, 0.5, True, False),
    "stepfun/step-3.5-flash": OpenRouterModelProfile(0.1, 0.3, False, False),
    "google/gemini-2.5-flash-lite": OpenRouterModelProfile(0.1, 0.4, True, False),
    "google/gemini-2.5-flash": OpenRouterModelProfile(0.3, 2.5, True, False),
    "nvidia/nemotron-3-super-120b-a12b:free": OpenRouterModelProfile(0.0, 0.0, True, False),
    # List price from product (API showed 0.435/M in at the same time).
    "deepseek/deepseek-v4-pro": OpenRouterModelProfile(0.485, 0.87, True, False),
    "inclusionai/ling-2.6-1t:free": OpenRouterModelProfile(0.0, 0.0, True, False),
    "anthropic/claude-opus-4.6": OpenRouterModelProfile(5.0, 25.0, True, False),
    "openai/gpt-4o-mini": OpenRouterModelProfile(0.15, 0.6, True, False),
    "qwen/qwen3-235b-a22b-2507": OpenRouterModelProfile(0.071, 0.1, True, False),
    "minimax/minimax-m2.5": OpenRouterModelProfile(0.15, 1.15, True, False),
    "anthropic/claude-haiku-4.5": OpenRouterModelProfile(1.0, 5.0, True, False),
    # --- Legacy / still common (not on first page of popularity snapshot) ---
    "openai/gpt-4o": OpenRouterModelProfile(2.5, 10.0, True, False),
    "anthropic/claude-sonnet-4": OpenRouterModelProfile(3.0, 15.0, False, False),
    "anthropic/claude-3.7-sonnet": OpenRouterModelProfile(3.0, 15.0, False, False),
    "google/gemini-2.5-pro": OpenRouterModelProfile(1.25, 10.0, True, False),
    "deepseek/deepseek-chat": OpenRouterModelProfile(0.32, 0.89, True, False),
    "meta-llama/llama-3.3-70b-instruct": OpenRouterModelProfile(0.1, 0.32, True, False),
    "x-ai/grok-4": OpenRouterModelProfile(3.0, 15.0, True, False),
    "mistralai/mistral-large-2411": OpenRouterModelProfile(2.0, 6.0, True, False),
    "openai/o3": OpenRouterModelProfile(2.0, 8.0, True, False),
    "openai/o4-mini": OpenRouterModelProfile(1.1, 4.4, True, False),
    "deepseek/deepseek-r1": OpenRouterModelProfile(0.7, 2.5, False, False),
    "anthropic/claude-3.7-sonnet:thinking": OpenRouterModelProfile(3.0, 15.0, False, False),
    "qwen/qwen-plus": OpenRouterModelProfile(0.26, 0.78, False, False),
    "mistralai/mistral-small-3.2-24b-instruct": OpenRouterModelProfile(0.075, 0.2, True, False),
    "x-ai/grok-3": OpenRouterModelProfile(3.0, 15.0, True, False),
    "meta-llama/llama-3.1-70b-instruct": OpenRouterModelProfile(0.4, 0.4, True, False),
    "mistralai/mistral-nemo": OpenRouterModelProfile(0.02, 0.03, True, False),
    "openai/gpt-4-turbo": OpenRouterModelProfile(10.0, 30.0, True, False),
    # Common extraction default; needs SO + extra_body.
    "qwen/qwen3.5-397b-a17b": OpenRouterModelProfile(0.39, 2.34, True, True),
}


def is_openrouter_base_url(base_url: str) -> bool:
    """Return True when the client targets OpenRouter's HTTP API."""

    u = (base_url or "").strip().lower()
    return any(u.startswith(m) for m in _OPENROUTER_BASE_URL_MARKERS)


def normalize_openrouter_model_id(model_id: str) -> str:
    """Lower-case OpenRouter slug used as registry dictionary key."""

    return (model_id or "").strip().lower()


def get_openrouter_model_profile(model_id: str) -> OpenRouterModelProfile | None:
    """Return the static profile for ``model_id`` if it is in the registry."""

    return _OPENROUTER_MODEL_REGISTRY.get(normalize_openrouter_model_id(model_id))


def openrouter_auto_uses_instructor_structured_outputs(*, base_url: str, model_id: str) -> bool:
    """Whether ``mode=auto`` should prefer ``OPENROUTER_STRUCTURED_OUTPUTS`` for this model."""

    if not is_openrouter_base_url(base_url):
        return False
    prof = get_openrouter_model_profile(model_id)
    return bool(prof and prof.openrouter_structured_outputs)


def openrouter_auto_reasoning_extra_body(*, base_url: str, model_id: str) -> bool:
    """Whether to attach the Qwen/OpenRouter ``reasoning`` workaround in ``extra_body``."""

    if not is_openrouter_base_url(base_url):
        return False
    prof = get_openrouter_model_profile(model_id)
    return bool(prof and prof.requires_reasoning_extra_body)


def openrouter_reference_pricing_block(*, model_id: str) -> dict[str, float] | None:
    """USD per 1M tokens (prompt/completion) for UI; None if unknown."""

    prof = get_openrouter_model_profile(model_id)
    if not prof:
        return None
    return {
        "prompt_usd_per_1m": float(prof.prompt_usd_per_1m_tokens),
        "completion_usd_per_1m": float(prof.completion_usd_per_1m_tokens),
    }


def openrouter_reference_pricing_run_metadata(
    *,
    base_url: str,
    chat_model_id: str,
    extraction_model_id: str,
) -> dict[str, object]:
    """Slice of ``run_metadata`` with reference list pricing for resolved model ids."""

    if not is_openrouter_base_url(base_url):
        return {}

    chat_mid = normalize_openrouter_model_id(chat_model_id)
    extraction_mid = normalize_openrouter_model_id(extraction_model_id)

    body: dict[str, object] = {}
    pb_chat = openrouter_reference_pricing_block(model_id=chat_mid)
    if pb_chat:
        body["chat"] = {"model_id": chat_mid, **pb_chat}
    pb_ex = openrouter_reference_pricing_block(model_id=extraction_mid)
    if pb_ex:
        body["extraction"] = {"model_id": extraction_mid, **pb_ex}
    if not body:
        return {}
    return {"openrouter_reference_pricing_usd_per_1m": body}
