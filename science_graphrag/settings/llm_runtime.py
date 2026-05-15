"""Resolve LLM default provider + task views for settings snapshot and runtime merge.

Single place for precedence: server-managed secrets > persisted JSON > process env
(:class:`Settings`) > built-in defaults. UI uses human-readable ``source`` labels;
legacy ``SCIENCE_GRAPHRAG_*`` names belong in ``diagnostics`` only.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from science_graphrag.config import Settings


def _strip(val: object | None) -> str:
    if val is None:
        return ""
    return str(val).strip()


def _mask(mask_fn: Callable[[str | None], str], key: str | None) -> str | None:
    if not key:
        return None
    return mask_fn(key)


def _operator_env_hints() -> list[str]:
    return [
        "SCIENCE_GRAPHRAG_API_KEY",
        "SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY",
        "SCIENCE_GRAPHRAG_VL_API_KEY",
    ]


def resolve_llm_runtime_views(
    *,
    persisted_llm: dict[str, Any],
    base_settings: Settings,
    saved_default_key: str | None,
    saved_vision_key: str | None,
    mask_secret: Callable[[str | None], str],
) -> dict[str, Any]:
    """Build default_provider, tasks, extended status, diagnostics, and effective blocks."""

    meta = dict(persisted_llm.get("_meta") or {})

    has_saved_default = bool(saved_default_key and _strip(saved_default_key))
    has_saved_vision = bool(saved_vision_key and _strip(saved_vision_key))

    env_extraction = _strip(base_settings.extraction_llm_api_key)
    env_vl_raw = _strip(base_settings.vl_api_key)

    # Effective default (text + chat transport) key: vault wins over env-loaded Settings.
    default_key_effective = _strip(saved_default_key) or env_extraction
    if has_saved_default:
        default_key_source = "server_managed"
        default_key_mask = _mask(mask_secret, saved_default_key)
    elif env_extraction:
        default_key_source = "environment"
        default_key_mask = _mask(mask_secret, env_extraction)
    else:
        default_key_source = "none"
        default_key_mask = None

    # Vision key effective: vault > env vl_api_key > inherit default key
    if has_saved_vision:
        vision_key_effective = _strip(saved_vision_key)
        vision_key_source = "server_managed"
        vision_key_mask = _mask(mask_secret, saved_vision_key)
    elif env_vl_raw:
        if env_vl_raw == env_extraction:
            vision_key_effective = default_key_effective
            vision_key_source = "inherited" if default_key_effective else "none"
            vision_key_mask = default_key_mask
        else:
            vision_key_effective = env_vl_raw
            vision_key_source = "environment"
            vision_key_mask = _mask(mask_secret, env_vl_raw)
    else:
        vision_key_effective = default_key_effective
        vision_key_source = "inherited" if default_key_effective else "none"
        vision_key_mask = default_key_mask

    vision_inherits_default = vision_key_source == "inherited"

    configured = bool(default_key_effective)
    needs_initial_setup = not configured
    setup_status = "needs_api_key" if needs_initial_setup else "ready"

    canonical_api_key_env_set = bool(_strip(base_settings.api_key))
    legacy_extraction_key_env_set = bool(
        os.getenv("SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY", "").strip()
    )
    vl_dedicated_env = bool(env_vl_raw) and env_vl_raw != env_extraction and not has_saved_vision
    uses_env_defaults = not (
        bool(_strip(persisted_llm.get("base_url")))
        or bool(_strip(persisted_llm.get("model")))
    )
    legacy_override_detected = bool(
        vl_dedicated_env or legacy_extraction_key_env_set or has_saved_vision
    )

    timeout_seconds = persisted_llm.get("timeout_seconds")
    if timeout_seconds is None:
        timeout_seconds = base_settings.extraction_llm_timeout_seconds

    persisted_base_url = _strip(persisted_llm.get("base_url"))
    persisted_model = _strip(persisted_llm.get("model"))
    resolved_base_url = persisted_base_url or _strip(base_settings.extraction_llm_base_url)
    resolved_model = persisted_model or _strip(base_settings.extraction_llm_model)

    persisted_chat = _strip(persisted_llm.get("chat_model"))
    env_chat = _strip(base_settings.chat_llm_model)
    resolved_chat_model = persisted_chat or env_chat or resolved_model
    chat_inherits_model = not persisted_chat and not env_chat

    persisted_vl_model = _strip(persisted_llm.get("vl_model"))
    persisted_vl_base = _strip(persisted_llm.get("vl_base_url")).rstrip("/")
    resolved_vl_model = persisted_vl_model or _strip(base_settings.vl_model)
    resolved_vl_base_url = persisted_vl_base or _strip(base_settings.vl_base_url)
    vl_model_inherited = not persisted_vl_model
    vl_base_inherited = not persisted_vl_base

    temperature = float(persisted_llm.get("temperature", base_settings.extraction_llm_temperature))

    or_emb = _strip(base_settings.openrouter_embedding_model)
    emb_mode: str
    if or_emb:
        emb_mode = "openrouter"
        emb_label = or_emb
        emb_inherits_key = True
    elif _strip(base_settings.embedding_model):
        emb_mode = "sentence_transformers"
        emb_label = _strip(base_settings.embedding_model)
        emb_inherits_key = False
    else:
        emb_mode = "hash_deterministic"
        emb_label = "hash-deterministic"
        emb_inherits_key = False

    secret_source = default_key_source

    status = {
        "configured": configured,
        "has_saved_secret": has_saved_default,
        "has_saved_vision_secret": has_saved_vision,
        "masked_key": default_key_mask,
        "masked_vision_key": vision_key_mask,
        "secret_source": secret_source,
        "vision_key_source": vision_key_source,
        "env_key_hint": None,
        "last_updated_at": meta.get("last_updated_at"),
        "last_updated_by": meta.get("last_updated_by"),
        "needs_initial_setup": needs_initial_setup,
        "setup_status": setup_status,
        "uses_env_defaults": uses_env_defaults,
        "legacy_override_detected": legacy_override_detected,
        "canonical_api_key_env_set": canonical_api_key_env_set,
        "legacy_extraction_key_env_set": legacy_extraction_key_env_set,
        "vl_api_key_explicit_env": vl_dedicated_env,
    }

    default_provider = {
        "base_url": resolved_base_url,
        "model": resolved_model,
        "temperature": temperature,
        "timeout_seconds": float(timeout_seconds),
        "api_key": {
            "source": default_key_source,
            "masked": default_key_mask,
        },
    }

    tasks = {
        "extraction": {
            "role": "extraction",
            "model": resolved_model,
            "base_url": resolved_base_url,
            "inherits_default_key": True,
            "api_key": {"source": default_key_source, "masked": default_key_mask},
        },
        "chat": {
            "role": "chat",
            "model": resolved_chat_model,
            "base_url": resolved_base_url,
            "inherits_default_key": True,
            "inherits_extraction_model": chat_inherits_model,
            "api_key": {"source": default_key_source, "masked": default_key_mask},
        },
        "vision": {
            "role": "vision",
            "model": resolved_vl_model,
            "base_url": resolved_vl_base_url,
            "key_configured": bool(vision_key_effective),
            "inherits_default_key": vision_inherits_default,
            "inherits_extraction_base_url": vl_base_inherited,
            "inherits_default_model": vl_model_inherited,
            "api_key": {"source": vision_key_source, "masked": vision_key_mask},
        },
        "embeddings": {
            "role": "embeddings",
            "mode": emb_mode,
            "model_label": emb_label,
            "inherits_default_key": emb_inherits_key,
            "openrouter_model": or_emb or None,
            "api_key": (
                {"source": default_key_source, "masked": default_key_mask}
                if emb_mode == "openrouter"
                else {"source": "none", "masked": None}
            ),
        },
    }

    diagnostics = {
        "operator_env_variables": _operator_env_hints(),
        "notes": (
            "Server process environment may supply API keys until you save keys in this UI. "
            "Variable names are listed above for operators only."
        ),
    }

    effective = {
        "resolved_base_url": resolved_base_url,
        "resolved_model": resolved_model,
        "resolved_chat_model": resolved_chat_model,
        "resolved_timeout_seconds": float(timeout_seconds),
        "resolved_temperature": temperature,
        "resolved_enabled": bool(
            persisted_llm.get("enabled", base_settings.extraction_llm_enabled)
        ),
        "resolved_vl_model": resolved_vl_model,
        "resolved_vl_base_url": resolved_vl_base_url,
        "resolved_default_key_source": default_key_source,
        "resolved_vision_key_source": vision_key_source,
    }

    return {
        "default_provider": default_provider,
        "tasks": tasks,
        "status": status,
        "diagnostics": diagnostics,
        "effective": effective,
    }


__all__ = ["resolve_llm_runtime_views"]
