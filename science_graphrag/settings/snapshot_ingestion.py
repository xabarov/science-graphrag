"""Ingestion subsection for ``SettingsService.get_snapshot``."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from science_graphrag.settings.snapshots import resolve_ingestion_fields

if TYPE_CHECKING:
    from science_graphrag.config import Settings


def build_ingestion_snapshot(
    *,
    ingestion_cfg: dict[str, Any],
    base_settings: Settings,
) -> dict[str, Any]:
    ingestion_meta = dict(ingestion_cfg.get("_meta") or {})
    resolved_upload_mb, resolved_claims_enabled = resolve_ingestion_fields(
        ingestion_cfg, base_settings
    )
    return {
        "max_file_size_mb": resolved_upload_mb,
        "claims_extraction_enabled": resolved_claims_enabled,
        "status": {
            "last_updated_at": ingestion_meta.get("last_updated_at"),
            "last_updated_by": ingestion_meta.get("last_updated_by"),
        },
        "effective": {
            "resolved_max_file_size_mb": resolved_upload_mb,
            "resolved_claims_extraction_enabled": resolved_claims_enabled,
        },
    }
