"""General subsection for ``SettingsService.get_snapshot``."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from science_graphrag.config import Settings


def build_general_snapshot(
    *, general_cfg: dict[str, Any], base_settings: Settings
) -> dict[str, Any]:
    general_meta = dict(general_cfg.get("_meta") or {})
    persisted_openalex_mailto = str(general_cfg.get("openalex_mailto") or "").strip()
    resolved_openalex_mailto = (
        persisted_openalex_mailto or str(base_settings.openalex_mailto or "").strip()
    )
    return {
        "openalex_mailto": persisted_openalex_mailto,
        "effective": {"resolved_openalex_mailto": resolved_openalex_mailto},
        "status": {
            "source": "server_managed" if persisted_openalex_mailto else "environment",
            "last_updated_at": general_meta.get("last_updated_at"),
            "last_updated_by": general_meta.get("last_updated_by"),
            "uses_env_default": not persisted_openalex_mailto,
        },
    }
