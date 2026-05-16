"""LLM subsection for ``SettingsService.get_snapshot``."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from science_graphrag.settings.llm_advanced_fields import (
    LLM_ADVANCED_RUNTIME_KEYS,
    advanced_effective_map,
    recommended_advanced_values,
)
from science_graphrag.settings.llm_runtime import resolve_llm_runtime_views
from science_graphrag.settings.llm_task_persisted import (
    embeddings_public_mode,
    get_normalized_llm_tasks,
)

if TYPE_CHECKING:
    from science_graphrag.config import Settings


def build_llm_snapshot(  # pylint: disable=too-many-locals
    *,
    persisted_llm: dict[str, Any],
    base_settings: Settings,
    saved_default_secret: str | None,
    saved_chat_secret: str | None,
    saved_embeddings_secret: str | None,
    saved_vision_secret: str | None,
    mask_secret: Callable[[str | None], str],
) -> dict[str, Any]:
    """Build masked LLM snapshot dict (UI + effective fields)."""
    views = resolve_llm_runtime_views(
        persisted_llm=persisted_llm,
        base_settings=base_settings,
        saved_default_key=saved_default_secret,
        saved_chat_key=saved_chat_secret,
        saved_embeddings_key=saved_embeddings_secret,
        saved_vision_key=saved_vision_secret,
        mask_secret=mask_secret,
    )

    tasks_cfg = get_normalized_llm_tasks(persisted_llm, base_settings)
    ext = tasks_cfg["extraction"]
    chat_block = tasks_cfg["chat"]
    vision_block = tasks_cfg["vision"]
    emb = tasks_cfg["embeddings"]

    persisted_vl_model = str(vision_block.get("model") or "").strip()
    persisted_vl_base = str(vision_block.get("base_url") or "").strip().rstrip("/")
    persisted_chat = str(chat_block.get("model") or "").strip()
    persisted_chat_base_url = str(chat_block.get("base_url") or "").strip().rstrip("/")
    persisted_embeddings_mode = embeddings_public_mode(emb)
    persisted_embeddings_model = str(emb.get("model") or "").strip()

    timeout_seconds = ext.get("timeout_seconds")
    if timeout_seconds is None:
        timeout_seconds = base_settings.extraction_llm_timeout_seconds

    llm_snapshot = {
        "provider_mode": "openai_compatible",
        "base_url": ext.get("base_url") or base_settings.extraction_llm_base_url,
        "model": ext.get("model") or base_settings.extraction_llm_model,
        "vl_model": persisted_vl_model,
        "vl_base_url": persisted_vl_base,
        "chat_model": persisted_chat,
        "chat_base_url": persisted_chat_base_url,
        "embeddings_mode": persisted_embeddings_mode,
        "embeddings_model": persisted_embeddings_model,
        "temperature": ext.get("temperature", base_settings.extraction_llm_temperature),
        "timeout_seconds": timeout_seconds,
        "default_provider": views["default_provider"],
        "tasks": views["tasks"],
        "diagnostics": views["diagnostics"],
        "status": views["status"],
        "effective": views["effective"],
    }

    adv_eff = advanced_effective_map(persisted_llm, base_settings)
    llm_snapshot["advanced_controls"] = {
        k: {"persisted": persisted_llm[k] if k in persisted_llm else None, "effective": adv_eff[k]}
        for k in LLM_ADVANCED_RUNTIME_KEYS
    }
    llm_snapshot["recommended_advanced"] = recommended_advanced_values()
    return llm_snapshot


__all__ = ["build_llm_snapshot"]
