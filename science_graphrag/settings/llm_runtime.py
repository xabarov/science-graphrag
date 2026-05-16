"""Resolve LLM default provider + task views for settings snapshot.

Precedence for **non-secret** fields: persisted JSON > process env (:class:`Settings`) > defaults.

API keys in the UI snapshot never fall back to process env after ``bootstrap_from_env_v1`` is set
on the persisted ``llm`` block (see :mod:`science_graphrag.settings.runtime_llm_bootstrap`).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from science_graphrag.settings.llm_provider_compat import (
    build_llm_provider_compatibility_diagnostics,
)
from science_graphrag.settings.llm_task_persisted import (
    embeddings_public_mode,
    get_normalized_llm_tasks,
)
from science_graphrag.settings.runtime_llm_bootstrap import BOOTSTRAP_FLAG

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


def _public_key_source(internal: str) -> str:
    """Map internal resolution to product-facing labels (no env vocabulary)."""

    if internal in ("server_managed", "environment"):
        return "saved"
    if internal == "inherited":
        return "inherited"
    return "none"


def llm_block_bootstrap_applied(persisted_llm: dict[str, Any]) -> bool:
    meta = dict(persisted_llm.get("_meta") or {})
    return bool(meta.get(BOOTSTRAP_FLAG))


def resolve_llm_runtime_views(
    *,
    persisted_llm: dict[str, Any],
    base_settings: Settings,
    saved_default_key: str | None,
    saved_chat_key: str | None,
    saved_embeddings_key: str | None,
    saved_vision_key: str | None,
    mask_secret: Callable[[str | None], str],
) -> dict[str, Any]:
    """Build default_provider, tasks, slim status, empty diagnostics, and effective blocks."""

    meta = dict(persisted_llm.get("_meta") or {})
    hide_env_api_keys = llm_block_bootstrap_applied(persisted_llm)

    has_saved_default = bool(saved_default_key and _strip(saved_default_key))
    has_saved_chat = bool(saved_chat_key and _strip(saved_chat_key))
    has_saved_embeddings = bool(saved_embeddings_key and _strip(saved_embeddings_key))
    has_saved_vision = bool(saved_vision_key and _strip(saved_vision_key))

    env_extraction = "" if hide_env_api_keys else _strip(base_settings.extraction_llm_api_key)
    env_vl_raw = "" if hide_env_api_keys else _strip(base_settings.vl_api_key)

    default_key_effective = _strip(saved_default_key) or env_extraction
    if has_saved_default:
        default_key_internal = "server_managed"
        default_key_mask = _mask(mask_secret, saved_default_key)
    elif env_extraction:
        default_key_internal = "environment"
        default_key_mask = _mask(mask_secret, env_extraction)
    else:
        default_key_internal = "none"
        default_key_mask = None

    if has_saved_vision:
        vision_key_effective = _strip(saved_vision_key)
        vision_key_internal = "server_managed"
        vision_key_mask = _mask(mask_secret, saved_vision_key)
    elif env_vl_raw:
        if env_vl_raw == env_extraction:
            vision_key_effective = default_key_effective
            vision_key_internal = "inherited" if default_key_effective else "none"
            vision_key_mask = default_key_mask
        else:
            vision_key_effective = env_vl_raw
            vision_key_internal = "environment"
            vision_key_mask = _mask(mask_secret, env_vl_raw)
    else:
        vision_key_effective = default_key_effective
        vision_key_internal = "inherited" if default_key_effective else "none"
        vision_key_mask = default_key_mask

    vision_inherits_default = vision_key_internal == "inherited"

    if has_saved_chat:
        chat_key_internal = "server_managed"
        chat_key_mask = _mask(mask_secret, saved_chat_key)
    else:
        chat_key_internal = "inherited" if default_key_effective else "none"
        chat_key_mask = default_key_mask
    chat_inherits_default_key = chat_key_internal == "inherited"

    if has_saved_embeddings:
        embeddings_key_internal = "server_managed"
        embeddings_key_mask = _mask(mask_secret, saved_embeddings_key)
    else:
        embeddings_key_internal = "inherited" if default_key_effective else "none"
        embeddings_key_mask = default_key_mask
    embeddings_inherits_default_key = embeddings_key_internal == "inherited"

    configured = bool(default_key_effective)
    needs_initial_setup = not configured
    setup_status = "needs_api_key" if needs_initial_setup else "ready"

    default_key_source = _public_key_source(default_key_internal)
    chat_key_source = _public_key_source(chat_key_internal)
    embeddings_key_source = _public_key_source(embeddings_key_internal)
    vision_key_source = _public_key_source(vision_key_internal)

    tasks_cfg = get_normalized_llm_tasks(persisted_llm, base_settings)
    ext = tasks_cfg["extraction"]
    chat = tasks_cfg["chat"]
    vision = tasks_cfg["vision"]
    emb = tasks_cfg["embeddings"]

    timeout_seconds = float(
        ext.get("timeout_seconds", base_settings.extraction_llm_timeout_seconds)
    )

    persisted_base_url = _strip(ext.get("base_url"))
    persisted_model = _strip(ext.get("model"))
    resolved_base_url = persisted_base_url or _strip(base_settings.extraction_llm_base_url)
    resolved_model = persisted_model or _strip(base_settings.extraction_llm_model)

    persisted_chat = _strip(chat.get("model"))
    persisted_chat_base = _strip(chat.get("base_url")).rstrip("/")
    env_chat = _strip(base_settings.chat_llm_model)
    resolved_chat_model = persisted_chat or env_chat or resolved_model
    chat_base_setting = _strip(base_settings.chat_llm_base_url)
    resolved_chat_base_url = persisted_chat_base or chat_base_setting or resolved_base_url
    chat_inherits_model = not persisted_chat and not env_chat
    chat_inherits_base_url = not persisted_chat_base and not chat_base_setting

    persisted_vl_model = _strip(vision.get("model"))
    persisted_vl_base = _strip(vision.get("base_url")).rstrip("/")
    resolved_vl_model = persisted_vl_model or _strip(base_settings.vl_model)
    resolved_vl_base_url = persisted_vl_base or _strip(base_settings.vl_base_url)
    vl_model_inherited = not persisted_vl_model
    vl_base_inherited = not persisted_vl_base

    temperature = float(ext.get("temperature", base_settings.extraction_llm_temperature))
    chat_temperature = float(chat.get("temperature", temperature))
    chat_timeout = float(chat.get("timeout_seconds", timeout_seconds))
    vl_temperature = float(vision.get("temperature", 0.0))
    vl_timeout = float(vision.get("timeout_seconds", 300.0))

    emb_mode_internal = str(emb.get("mode") or "http").strip().lower()
    persisted_emb_base = _strip(emb.get("base_url")).rstrip("/")
    resolved_emb_base_url = (
        persisted_emb_base
        or _strip(base_settings.embeddings_http_base_url).rstrip("/")
        or resolved_base_url
    )
    persisted_emb_model = _strip(emb.get("model"))
    or_emb = _strip(base_settings.openrouter_embedding_model)
    emb_label: str
    if emb_mode_internal == "local":
        emb_mode = "sentence_transformers"
        emb_label = (
            persisted_emb_model or _strip(base_settings.embedding_model) or "all-MiniLM-L6-v2"
        )
    elif or_emb or emb_mode_internal == "http":
        emb_mode = "openrouter"
        emb_label = persisted_emb_model or or_emb or "baai/bge-m3"
    elif _strip(base_settings.embedding_model):
        emb_mode = "sentence_transformers"
        emb_label = _strip(base_settings.embedding_model)
    else:
        emb_mode = "hash_deterministic"
        emb_label = "hash-deterministic"

    status = {
        "configured": configured,
        "has_saved_secret": has_saved_default,
        "has_saved_chat_secret": has_saved_chat,
        "has_saved_embeddings_secret": has_saved_embeddings,
        "has_saved_vision_secret": has_saved_vision,
        "masked_key": default_key_mask,
        "masked_chat_key": chat_key_mask,
        "masked_embeddings_key": embeddings_key_mask,
        "masked_vision_key": vision_key_mask,
        "secret_source": default_key_source,
        "chat_key_source": chat_key_source,
        "embeddings_key_source": embeddings_key_source,
        "vision_key_source": vision_key_source,
        "last_updated_at": meta.get("last_updated_at"),
        "last_updated_by": meta.get("last_updated_by"),
        "needs_initial_setup": needs_initial_setup,
        "setup_status": setup_status,
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
            "temperature": temperature,
            "timeout_seconds": float(timeout_seconds),
            "inherits_default_key": True,
            "api_key": {"source": default_key_source, "masked": default_key_mask},
        },
        "chat": {
            "role": "chat",
            "model": resolved_chat_model,
            "base_url": resolved_chat_base_url,
            "temperature": chat_temperature,
            "timeout_seconds": chat_timeout,
            "inherits_default_key": chat_inherits_default_key,
            "inherits_extraction_model": chat_inherits_model,
            "inherits_extraction_base_url": chat_inherits_base_url,
            "api_key": {"source": chat_key_source, "masked": chat_key_mask},
        },
        "vision": {
            "role": "vision",
            "model": resolved_vl_model,
            "base_url": resolved_vl_base_url,
            "temperature": vl_temperature,
            "timeout_seconds": vl_timeout,
            "key_configured": bool(vision_key_effective),
            "inherits_default_key": vision_inherits_default,
            "inherits_extraction_base_url": vl_base_inherited,
            "inherits_default_model": vl_model_inherited,
            "api_key": {"source": vision_key_source, "masked": vision_key_mask},
        },
        "embeddings": {
            "role": "embeddings",
            "mode": emb_mode,
            "mode_code": emb_mode_internal,
            "public_mode": embeddings_public_mode(emb),
            "model_label": emb_label,
            "base_url": resolved_emb_base_url,
            "timeout_seconds": float(emb.get("timeout_seconds", 60.0)),
            "inherits_default_key": emb_mode == "openrouter" and embeddings_inherits_default_key,
            "supports_custom_key": emb_mode == "openrouter",
            "openrouter_model": emb_mode == "openrouter" and emb_label or None,
            "api_key": (
                {"source": embeddings_key_source, "masked": embeddings_key_mask}
                if emb_mode == "openrouter"
                else {"source": "none", "masked": None}
            ),
        },
    }

    effective = {
        "resolved_base_url": resolved_base_url,
        "resolved_model": resolved_model,
        "resolved_chat_model": resolved_chat_model,
        "resolved_chat_base_url": resolved_chat_base_url,
        "resolved_timeout_seconds": float(timeout_seconds),
        "resolved_temperature": temperature,
        "resolved_chat_temperature": chat_temperature,
        "resolved_chat_timeout_seconds": chat_timeout,
        "resolved_vl_temperature": vl_temperature,
        "resolved_vl_timeout_seconds": vl_timeout,
        "resolved_enabled": bool(
            persisted_llm.get("enabled", base_settings.extraction_llm_enabled)
        ),
        "resolved_vl_model": resolved_vl_model,
        "resolved_vl_base_url": resolved_vl_base_url,
        "resolved_embeddings_mode": embeddings_public_mode(emb),
        "resolved_embeddings_base_url": resolved_emb_base_url,
        "resolved_embeddings_timeout_seconds": float(emb.get("timeout_seconds", 60.0)),
    }

    provider_diagnostics = build_llm_provider_compatibility_diagnostics(
        extraction_base_url=resolved_base_url,
        chat_base_url=resolved_chat_base_url,
        embeddings_base_url=resolved_emb_base_url or "",
    )

    return {
        "default_provider": default_provider,
        "tasks": tasks,
        "status": status,
        "diagnostics": provider_diagnostics,
        "effective": effective,
    }


__all__ = [
    "llm_block_bootstrap_applied",
    "resolve_llm_runtime_views",
]
