"""Agent tools subsection for ``SettingsService.get_snapshot``."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from science_graphrag.settings.stored_bool import optional_stored_bool

if TYPE_CHECKING:
    from science_graphrag.config import Settings

_SOURCE_IDS = ("crossref", "arxiv", "unpaywall", "openalex", "semantic_scholar")


def _mailto_configured(settings: Settings) -> bool:
    mailto = str(getattr(settings, "openalex_mailto", "") or "").strip()
    return bool(mailto) and "@" in mailto and " " not in mailto


def _persisted_int(cfg: dict[str, Any], key: str) -> int | None:
    raw = cfg.get(key)
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _persisted_float(cfg: dict[str, Any], key: str) -> float | None:
    raw = cfg.get(key)
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _persisted_bool(cfg: dict[str, Any], key: str) -> bool | None:
    if key not in cfg:
        return None
    return optional_stored_bool(cfg.get(key))


def _diag(cfg: dict[str, Any], source_id: str) -> tuple[Any, Any]:
    root = cfg.get("source_diagnostics") or {}
    if not isinstance(root, dict):
        return None, None
    row = root.get(source_id) or {}
    if not isinstance(row, dict):
        return None, None
    return row.get("last_test"), row.get("last_error")


def _source_row(
    *,
    source_id: str,
    merged_settings: Settings,
    agent_tools_cfg: dict[str, Any],
) -> dict[str, Any]:
    last_test, last_error = _diag(agent_tools_cfg, source_id)
    mailto_ok = _mailto_configured(merged_settings)

    if source_id == "crossref":
        en = bool(getattr(merged_settings, "external_research_source_crossref_enabled", True))
        return {
            "id": "crossref",
            "label": "Crossref",
            "enabled": en,
            "available": True,
            "configured": mailto_ok,
            "requires_key": False,
            "status": "ok" if en else "disabled",
            "tier": "stable",
            "last_test": last_test,
            "last_error": last_error,
        }
    if source_id == "arxiv":
        en = bool(getattr(merged_settings, "external_research_source_arxiv_enabled", True))
        return {
            "id": "arxiv",
            "label": "arXiv",
            "enabled": en,
            "available": True,
            "configured": True,
            "requires_key": False,
            "status": "ok" if en else "disabled",
            "tier": "stable",
            "last_test": last_test,
            "last_error": last_error,
        }
    if source_id == "unpaywall":
        en = bool(getattr(merged_settings, "external_research_source_unpaywall_enabled", True))
        tool_on = bool(getattr(merged_settings, "agent_unpaywall_oa_tool_enabled", False))
        effective = en and tool_on
        return {
            "id": "unpaywall",
            "label": "Unpaywall",
            "enabled": effective,
            "available": True,
            "configured": mailto_ok,
            "requires_key": False,
            "status": "needs_live_smoke" if effective else "disabled",
            "tier": "stable",
            "last_test": last_test,
            "last_error": last_error,
        }
    if source_id == "openalex":
        en = bool(getattr(merged_settings, "external_research_source_openalex_enabled", True))
        return {
            "id": "openalex",
            "label": "OpenAlex",
            "enabled": en,
            "available": True,
            "configured": mailto_ok,
            "requires_key": False,
            "status": "ok" if en else "disabled",
            "tier": "stable",
            "last_test": last_test,
            "last_error": last_error,
        }
    if source_id == "semantic_scholar":
        return {
            "id": "semantic_scholar",
            "label": "Semantic Scholar",
            "enabled": False,
            "available": False,
            "configured": False,
            "requires_key": True,
            "status": "planned",
            "tier": "planned",
            "last_test": last_test,
            "last_error": last_error,
        }
    raise ValueError(f"unknown source_id={source_id!r}")


def build_agent_tools_snapshot(
    *,
    agent_tools_cfg: dict[str, Any],
    merged_settings: Settings,
) -> dict[str, Any]:
    """Build the ``agent_tools`` subsection for settings snapshots (non-secret)."""
    agent_tools_meta = dict(agent_tools_cfg.get("_meta") or {})
    persisted_sup_rounds = agent_tools_cfg.get("agent_supervisor_max_rounds")

    pr_int: int | None = None
    if persisted_sup_rounds is not None and str(persisted_sup_rounds).strip() != "":
        try:
            pr_int = int(persisted_sup_rounds)
        except (TypeError, ValueError):
            pr_int = None

    persisted_external_default = _persisted_bool(
        agent_tools_cfg, "external_research_default_enabled"
    )
    persisted_pdf_mode = agent_tools_cfg.get("pdf_reading_mode")
    persisted_unpaywall = _persisted_bool(agent_tools_cfg, "agent_unpaywall_oa_tool_enabled")
    persisted_ext_timeout = _persisted_float(agent_tools_cfg, "agent_external_http_timeout_seconds")
    persisted_max_calls = _persisted_int(agent_tools_cfg, "agent_external_max_calls_per_turn")
    persisted_max_cards = _persisted_int(agent_tools_cfg, "agent_external_max_source_cards")
    persisted_pdf_tool_enabled = _persisted_bool(agent_tools_cfg, "agent_pdf_read_tool_enabled")
    persisted_pdf_max_bytes = _persisted_int(agent_tools_cfg, "agent_pdf_read_max_bytes")
    persisted_pdf_max_pages = _persisted_int(agent_tools_cfg, "agent_pdf_read_max_pages")
    persisted_pdf_cache_ttl = _persisted_int(agent_tools_cfg, "agent_pdf_read_cache_ttl_seconds")

    src_cfg = agent_tools_cfg.get("external_research_sources") or {}
    persisted_sources: dict[str, Any] = {}
    if isinstance(src_cfg, dict):
        for k in ("crossref", "arxiv", "unpaywall", "openalex"):
            if k in src_cfg:
                persisted_sources[k] = src_cfg[k]

    persisted_keys = {k for k in agent_tools_cfg if k not in {"_meta", "source_diagnostics"}}
    status_source = "server_managed" if persisted_keys else "environment"

    sources = [
        _source_row(source_id=sid, merged_settings=merged_settings, agent_tools_cfg=agent_tools_cfg)
        for sid in _SOURCE_IDS
    ]

    mailto_ok = _mailto_configured(merged_settings)

    return {
        "agent_supervisor_max_rounds": pr_int,
        "external_research_default_enabled": persisted_external_default,
        "pdf_reading_mode": (
            persisted_pdf_mode if persisted_pdf_mode in {"off", "ask", "auto_safe_oa"} else None
        ),
        "agent_unpaywall_oa_tool_enabled": persisted_unpaywall,
        "agent_external_http_timeout_seconds": persisted_ext_timeout,
        "agent_external_max_calls_per_turn": persisted_max_calls,
        "agent_external_max_source_cards": persisted_max_cards,
        "agent_pdf_read_tool_enabled": persisted_pdf_tool_enabled,
        "agent_pdf_read_max_bytes": persisted_pdf_max_bytes,
        "agent_pdf_read_max_pages": persisted_pdf_max_pages,
        "agent_pdf_read_cache_ttl_seconds": persisted_pdf_cache_ttl,
        "external_research_sources": persisted_sources or None,
        "effective": {
            "resolved_agent_supervisor_max_rounds": int(
                merged_settings.agent_supervisor_max_rounds
            ),
            "resolved_external_research_default_enabled": bool(
                merged_settings.external_research_default_enabled
            ),
            "resolved_pdf_reading_mode": str(merged_settings.pdf_reading_mode),
            "resolved_agent_unpaywall_oa_tool_enabled": bool(
                merged_settings.agent_unpaywall_oa_tool_enabled
            ),
            "resolved_agent_external_http_timeout_seconds": float(
                merged_settings.agent_external_http_timeout_seconds
            ),
            "resolved_agent_external_max_calls_per_turn": int(
                merged_settings.agent_external_max_calls_per_turn
            ),
            "resolved_agent_external_max_source_cards": int(
                merged_settings.agent_external_max_source_cards
            ),
            "resolved_agent_pdf_read_tool_enabled": bool(
                getattr(merged_settings, "agent_pdf_read_tool_enabled", True)
            ),
            "resolved_agent_pdf_read_max_bytes": int(
                getattr(merged_settings, "agent_pdf_read_max_bytes", 8_000_000)
            ),
            "resolved_agent_pdf_read_max_pages": int(
                getattr(merged_settings, "agent_pdf_read_max_pages", 30)
            ),
            "resolved_agent_pdf_read_cache_ttl_seconds": int(
                getattr(merged_settings, "agent_pdf_read_cache_ttl_seconds", 300)
            ),
            "resolved_external_research_sources": {
                "crossref": bool(merged_settings.external_research_source_crossref_enabled),
                "arxiv": bool(merged_settings.external_research_source_arxiv_enabled),
                "unpaywall": bool(merged_settings.external_research_source_unpaywall_enabled),
                "openalex": bool(
                    getattr(merged_settings, "external_research_source_openalex_enabled", True)
                ),
            },
        },
        "sources": sources,
        "integrations": {
            "mcp_tools_enabled": bool(getattr(merged_settings, "agent_mcp_tools_enabled", False)),
            "mcp_http_base_url_configured": bool(
                str(getattr(merged_settings, "agent_mcp_http_base_url", None) or "").strip()
            ),
            "mcp_server_denylist_count": len(
                list(getattr(merged_settings, "agent_mcp_server_denylist", None) or [])
            ),
        },
        "credentials": {
            "research_contact_email_configured": mailto_ok,
            "research_contact_email_status": "configured" if mailto_ok else "not_configured",
        },
        "status": {
            "source": status_source,
            "last_updated_at": agent_tools_meta.get("last_updated_at"),
            "last_updated_by": agent_tools_meta.get("last_updated_by"),
        },
    }
