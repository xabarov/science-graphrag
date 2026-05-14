"""LLM subsection for ``SettingsService.get_snapshot``."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, Callable

from science_graphrag.settings.llm_advanced_fields import (
    LLM_ADVANCED_RUNTIME_KEYS,
    advanced_effective_map,
    recommended_advanced_values,
)

if TYPE_CHECKING:
    from science_graphrag.config import Settings

_LLM_ENV_KEY_HINT = (
    "SCIENCE_GRAPHRAG_API_KEY (canonical unified key) or "
    "SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY / SCIENCE_GRAPHRAG_VL_API_KEY for compatibility"
)


def build_llm_snapshot(  # pylint: disable=too-many-locals
    *,
    persisted_llm: dict[str, Any],
    base_settings: Settings,
    saved_secret: str | None,
    mask_secret: Callable[[str | None], str],
) -> dict[str, Any]:
    """Build masked LLM snapshot dict (UI + effective fields)."""
    meta = dict(persisted_llm.get("_meta") or {})
    has_saved_secret = bool(saved_secret)
    env_key_raw = base_settings.extraction_llm_api_key
    env_key = (env_key_raw or "").strip() if env_key_raw else ""
    has_env_key = bool(env_key)

    if has_saved_secret:
        secret_source = "server_managed"
        active_key_for_mask = saved_secret
    elif has_env_key:
        secret_source = "environment"
        active_key_for_mask = env_key
    else:
        secret_source = "none"
        active_key_for_mask = None

    configured = has_saved_secret or has_env_key
    needs_initial_setup = not configured
    canonical_api_key_env_set = bool((base_settings.api_key or "").strip())
    legacy_extraction_key_env_set = bool(
        os.getenv("SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY", "").strip()
    )
    vl_raw = (base_settings.vl_api_key or "").strip()
    extraction_effective = (base_settings.extraction_llm_api_key or "").strip()
    vl_dedicated_api_key = bool(vl_raw) and vl_raw != extraction_effective
    uses_env_defaults = not (
        bool(str(persisted_llm.get("base_url") or "").strip())
        or bool(str(persisted_llm.get("model") or "").strip())
    )
    legacy_override_detected = bool(vl_dedicated_api_key or legacy_extraction_key_env_set)
    setup_status = "needs_api_key" if needs_initial_setup else "ready"

    timeout_seconds = persisted_llm.get("timeout_seconds")
    if timeout_seconds is None:
        timeout_seconds = base_settings.extraction_llm_timeout_seconds

    persisted_chat = str(persisted_llm.get("chat_model") or "").strip()
    env_chat = str(base_settings.chat_llm_model or "").strip()
    resolved_chat_model = persisted_chat or env_chat or base_settings.extraction_llm_model

    persisted_vl_model = str(persisted_llm.get("vl_model") or "").strip()
    persisted_vl_base = str(persisted_llm.get("vl_base_url") or "").strip().rstrip("/")
    resolved_vl_model = persisted_vl_model or base_settings.vl_model
    resolved_vl_base_url = persisted_vl_base or base_settings.vl_base_url

    llm_snapshot = {
        "provider_mode": "openai_compatible",
        "base_url": persisted_llm.get("base_url") or base_settings.extraction_llm_base_url,
        "model": persisted_llm.get("model") or base_settings.extraction_llm_model,
        "vl_model": persisted_vl_model,
        "vl_base_url": persisted_vl_base,
        "chat_model": persisted_chat,
        "temperature": persisted_llm.get("temperature", base_settings.extraction_llm_temperature),
        "timeout_seconds": timeout_seconds,
        "status": {
            "configured": configured,
            "has_saved_secret": has_saved_secret,
            "masked_key": mask_secret(active_key_for_mask),
            "secret_source": secret_source,
            "env_key_hint": _LLM_ENV_KEY_HINT if secret_source == "environment" else None,
            "last_updated_at": meta.get("last_updated_at"),
            "last_updated_by": meta.get("last_updated_by"),
            "needs_initial_setup": needs_initial_setup,
            "setup_status": setup_status,
            "uses_env_defaults": uses_env_defaults,
            "legacy_override_detected": legacy_override_detected,
            "canonical_api_key_env_set": canonical_api_key_env_set,
            "legacy_extraction_key_env_set": legacy_extraction_key_env_set,
            "vl_api_key_explicit_env": vl_dedicated_api_key,
        },
        "effective": {
            "resolved_base_url": persisted_llm.get("base_url")
            or base_settings.extraction_llm_base_url,
            "resolved_model": persisted_llm.get("model") or base_settings.extraction_llm_model,
            "resolved_chat_model": resolved_chat_model,
            "resolved_timeout_seconds": timeout_seconds,
            "resolved_temperature": persisted_llm.get(
                "temperature", base_settings.extraction_llm_temperature
            ),
            "resolved_enabled": bool(
                persisted_llm.get("enabled", base_settings.extraction_llm_enabled)
            ),
            "resolved_vl_model": resolved_vl_model,
            "resolved_vl_base_url": resolved_vl_base_url,
        },
    }

    adv_eff = advanced_effective_map(persisted_llm, base_settings)
    llm_snapshot["advanced_controls"] = {
        k: {"persisted": persisted_llm[k] if k in persisted_llm else None, "effective": adv_eff[k]}
        for k in LLM_ADVANCED_RUNTIME_KEYS
    }
    llm_snapshot["recommended_advanced"] = recommended_advanced_values()
    return llm_snapshot
