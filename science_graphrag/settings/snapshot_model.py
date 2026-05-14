"""UI-facing settings snapshot type (decoupled from SettingsService orchestration)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SettingsSnapshot:
    """Materialized runtime state for the settings UI and config overlay."""

    non_secret_overrides: dict[str, Any]
    llm: dict[str, Any]
    ingestion: dict[str, Any]
    general: dict[str, Any]
    storage: dict[str, Any]
    benchmark: dict[str, Any]
    diagnostics: dict[str, Any]
    security: dict[str, Any]
    sections: list[dict[str, Any]]
    work_dedup: dict[str, Any]
    agent_tools: dict[str, Any]


__all__ = ["SettingsSnapshot"]
