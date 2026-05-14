"""Assemble :class:`SettingsSnapshot` from persisted JSON + secret store (pure orchestration)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from science_graphrag.settings.benchmark_defaults import build_benchmark_ui_snapshot
from science_graphrag.settings.runtime_overlay import build_non_secret_overrides
from science_graphrag.settings.secret_display import mask_short_secret as _mask_secret
from science_graphrag.settings.secret_store_keys import LLM_API_KEY
from science_graphrag.settings.secrets import SecretStore
from science_graphrag.settings.snapshot_agent_tools import build_agent_tools_snapshot
from science_graphrag.settings.snapshot_general import build_general_snapshot
from science_graphrag.settings.snapshot_ingestion import build_ingestion_snapshot
from science_graphrag.settings.snapshot_llm import build_llm_snapshot
from science_graphrag.settings.snapshot_model import SettingsSnapshot
from science_graphrag.settings.snapshot_sections import build_settings_sections_catalog
from science_graphrag.settings.snapshot_work_dedup import build_work_dedup_snapshot
from science_graphrag.settings.snapshots import (
    build_diagnostics_snapshot,
    build_security_snapshot,
)
from science_graphrag.settings.storage_runtime import build_storage_ui_snapshot

if TYPE_CHECKING:
    from science_graphrag.config import Settings


@dataclass(frozen=True)
class _PersistedJson:
    """Normalized top-level JSON blobs from the persisted settings file."""

    llm: dict[str, Any]
    ingestion_cfg: dict[str, Any]
    general_cfg: dict[str, Any]
    storage_cfg: dict[str, Any]
    benchmark_cfg: dict[str, Any]
    agent_tools_cfg: dict[str, Any]

    @staticmethod
    def from_persisted(persisted: dict[str, Any]) -> _PersistedJson:
        """Parse top-level keys from persisted settings JSON into mutable dict copies."""
        return _PersistedJson(
            llm=dict(persisted.get("llm") or {}),
            ingestion_cfg=dict(persisted.get("ingestion") or {}),
            general_cfg=dict(persisted.get("general") or {}),
            storage_cfg=dict(persisted.get("storage") or {}),
            benchmark_cfg=dict(persisted.get("benchmark") or {}),
            agent_tools_cfg=dict(persisted.get("agent_tools") or {}),
        )


def materialize_settings_snapshot(
    *,
    base_settings: Settings,
    persisted: dict[str, Any],
    secret_store: SecretStore,
) -> SettingsSnapshot:
    """Build a full UI snapshot from already-loaded persisted JSON."""
    pj = _PersistedJson.from_persisted(persisted)
    saved_secret = secret_store.get_secret(LLM_API_KEY)

    llm_snapshot = build_llm_snapshot(
        persisted_llm=pj.llm,
        base_settings=base_settings,
        saved_secret=saved_secret,
        mask_secret=_mask_secret,
    )
    ingestion_snapshot = build_ingestion_snapshot(
        ingestion_cfg=pj.ingestion_cfg, base_settings=base_settings
    )
    general_snapshot = build_general_snapshot(
        general_cfg=pj.general_cfg, base_settings=base_settings
    )

    storage_snapshot = build_storage_ui_snapshot(
        base_settings=base_settings,
        storage_cfg=pj.storage_cfg,
        secret_store=secret_store,
    )

    benchmark_snapshot = build_benchmark_ui_snapshot(pj.benchmark_cfg)

    diagnostics_snapshot = build_diagnostics_snapshot()
    security_snapshot = build_security_snapshot(base_settings)

    non_secret_overrides = build_non_secret_overrides(
        base_settings=base_settings,
        llm=pj.llm,
        ingestion_cfg=pj.ingestion_cfg,
        general_cfg=pj.general_cfg,
        storage_cfg=pj.storage_cfg,
        secret_store=secret_store,
        storage_secret_explicit=None,
        agent_tools=pj.agent_tools_cfg,
    )
    merged_settings = base_settings.model_copy(update=non_secret_overrides)

    agent_tools_snapshot = build_agent_tools_snapshot(
        agent_tools_cfg=pj.agent_tools_cfg,
        merged_settings=merged_settings,
    )
    work_dedup_snapshot = build_work_dedup_snapshot(
        base_settings=base_settings, merged_settings=merged_settings
    )
    sections = build_settings_sections_catalog()

    return SettingsSnapshot(
        non_secret_overrides=non_secret_overrides,
        llm=llm_snapshot,
        ingestion=ingestion_snapshot,
        general=general_snapshot,
        storage=storage_snapshot,
        benchmark=benchmark_snapshot,
        diagnostics=diagnostics_snapshot,
        security=security_snapshot,
        sections=sections,
        work_dedup=work_dedup_snapshot,
        agent_tools=agent_tools_snapshot,
    )


__all__ = ["materialize_settings_snapshot"]
