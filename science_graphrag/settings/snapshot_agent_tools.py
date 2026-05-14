"""Agent tools subsection for ``SettingsService.get_snapshot``."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from science_graphrag.config import Settings


def build_agent_tools_snapshot(
    *,
    agent_tools_cfg: dict[str, Any],
    merged_settings: Settings,
) -> dict[str, Any]:
    agent_tools_meta = dict(agent_tools_cfg.get("_meta") or {})
    persisted_sup_rounds = agent_tools_cfg.get("agent_supervisor_max_rounds")

    pr_int: int | None = None
    if persisted_sup_rounds is not None and str(persisted_sup_rounds).strip() != "":
        try:
            pr_int = int(persisted_sup_rounds)
        except (TypeError, ValueError):
            pr_int = None
    return {
        "agent_supervisor_max_rounds": pr_int,
        "effective": {
            "resolved_agent_supervisor_max_rounds": int(
                merged_settings.agent_supervisor_max_rounds
            ),
        },
        "status": {
            "source": "server_managed" if pr_int is not None else "environment",
            "last_updated_at": agent_tools_meta.get("last_updated_at"),
            "last_updated_by": agent_tools_meta.get("last_updated_by"),
        },
    }
