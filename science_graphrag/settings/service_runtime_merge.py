"""Shared merge + validate for persisted runtime JSON (``SettingsService``)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from science_graphrag.settings.llm_advanced_fields import validate_merged_runtime_settings
from science_graphrag.settings.runtime_overlay import build_non_secret_overrides
from science_graphrag.settings.secrets import SecretStore

if TYPE_CHECKING:
    from science_graphrag.config import Settings


def merged_runtime_candidate_from_persisted_payload(
    *,
    base_settings: Settings,
    payload: dict[str, Any],
    secret_store: SecretStore,
    storage_secret_explicit: dict[str, str | None] | None = None,
) -> Any:
    """Return ``Settings`` candidate = base + non-secret overrides (for merge validation)."""
    llm = dict(payload.get("llm") or {})
    ingestion_cfg = dict(payload.get("ingestion") or {})
    general_cfg = dict(payload.get("general") or {})
    storage_cfg = dict(payload.get("storage") or {})
    agent_tools_cfg = dict(payload.get("agent_tools") or {})
    merged_non_secret = build_non_secret_overrides(
        base_settings=base_settings,
        llm=llm,
        ingestion_cfg=ingestion_cfg,
        general_cfg=general_cfg,
        storage_cfg=storage_cfg,
        secret_store=secret_store,
        storage_secret_explicit=storage_secret_explicit,
        agent_tools=agent_tools_cfg,
    )
    candidate = base_settings.model_copy(update=merged_non_secret)
    validate_merged_runtime_settings(candidate)
    return candidate


def validate_settings_model_roundtrip(candidate: Any) -> None:
    """Full Pydantic round-trip (stricter than merge-only validation)."""
    try:
        type(candidate).model_validate(candidate.model_dump(mode="python"))
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc


__all__ = [
    "merged_runtime_candidate_from_persisted_payload",
    "validate_settings_model_roundtrip",
]
