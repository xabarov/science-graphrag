"""Runtime overlay helpers for settings service."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from science_graphrag.settings.llm_advanced_fields import merge_llm_advanced_into_overrides
from science_graphrag.settings.secrets import SecretStore
from science_graphrag.settings.snapshots import resolve_ingestion_fields
from science_graphrag.settings.storage_runtime import merge_storage_runtime_fields
from science_graphrag.settings.stored_bool import optional_stored_bool

if TYPE_CHECKING:
    from science_graphrag.config import Settings


def build_non_secret_overrides(
    *,
    base_settings: Settings,
    llm: dict[str, Any],
    ingestion_cfg: dict[str, Any],
    general_cfg: dict[str, Any] | None,
    storage_cfg: dict[str, Any] | None,
    secret_store: SecretStore,
    storage_secret_explicit: dict[str, str | None] | None = None,
    agent_tools: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build settings overlay dict used by snapshot + runtime merge."""
    timeout_seconds = llm.get("timeout_seconds")
    if timeout_seconds is None:
        timeout_seconds = base_settings.extraction_llm_timeout_seconds

    persisted_chat = str(llm.get("chat_model") or "").strip()
    env_chat = str(base_settings.chat_llm_model or "").strip()

    resolved_upload_mb, resolved_claims_enabled = resolve_ingestion_fields(
        ingestion_cfg, base_settings
    )

    persisted_vl_model = str(llm.get("vl_model") or "").strip()
    persisted_vl_base = str(llm.get("vl_base_url") or "").strip().rstrip("/")

    non_secret_overrides: dict[str, Any] = {
        "extraction_llm_base_url": llm.get("base_url") or base_settings.extraction_llm_base_url,
        "extraction_llm_model": llm.get("model") or base_settings.extraction_llm_model,
        "extraction_llm_temperature": llm.get(
            "temperature", base_settings.extraction_llm_temperature
        ),
        "extraction_llm_timeout_seconds": timeout_seconds,
        "vl_model": persisted_vl_model or base_settings.vl_model,
        "vl_base_url": persisted_vl_base or base_settings.vl_base_url,
    }
    if "enabled" in llm:
        non_secret_overrides["extraction_llm_enabled"] = bool(llm["enabled"])
    chat_override = persisted_chat or env_chat
    if chat_override:
        non_secret_overrides["chat_llm_model"] = chat_override
    non_secret_overrides["workspace_upload_max_file_size_mb"] = resolved_upload_mb
    non_secret_overrides["claims_extraction_enabled"] = resolved_claims_enabled
    gcfg = dict(general_cfg or {})
    persisted_mailto = str(gcfg.get("openalex_mailto") or "").strip()
    non_secret_overrides["openalex_mailto"] = (
        persisted_mailto if persisted_mailto else base_settings.openalex_mailto
    )
    merge_llm_advanced_into_overrides(
        non_secret_overrides,
        llm=llm,
        base=base_settings,
    )
    sc = dict(storage_cfg or {})
    storage_fields = merge_storage_runtime_fields(
        base_settings,
        sc,
        secret_store,
        explicit_secrets=storage_secret_explicit,
    )
    non_secret_overrides.update(storage_fields)
    _merge_persisted_agent_tools(non_secret_overrides, agent_tools)
    return non_secret_overrides


def _merge_persisted_agent_tools(
    non_secret_overrides: dict[str, Any],
    agent_tools: dict[str, Any] | None,
) -> None:
    """Apply allowlisted persisted ``agent_tools`` keys (Wave E admin slice).

    Only operator-facing Settings fields are merged; tool args_schema and internal
    guardrails stay out of this bucket.
    """
    if not agent_tools:
        return
    if "agent_supervisor_max_rounds" in agent_tools:
        raw = agent_tools.get("agent_supervisor_max_rounds")
        try:
            n = int(raw)
        except (TypeError, ValueError):
            pass
        else:
            non_secret_overrides["agent_supervisor_max_rounds"] = max(2, min(32, n))
    if "external_research_default_enabled" in agent_tools:
        raw = agent_tools.get("external_research_default_enabled")
        b = optional_stored_bool(raw)
        if b is not None:
            non_secret_overrides["external_research_default_enabled"] = b
    if "external_research_sources" in agent_tools:
        src = agent_tools.get("external_research_sources")
        if isinstance(src, dict):
            for key, field in (
                ("crossref", "external_research_source_crossref_enabled"),
                ("arxiv", "external_research_source_arxiv_enabled"),
                ("unpaywall", "external_research_source_unpaywall_enabled"),
                ("openalex", "external_research_source_openalex_enabled"),
            ):
                if key not in src:
                    continue
                b = optional_stored_bool(src.get(key))
                if b is not None:
                    non_secret_overrides[field] = b
    if "pdf_reading_mode" in agent_tools:
        raw = agent_tools.get("pdf_reading_mode")
        if raw in {"off", "ask", "auto_safe_oa"}:
            non_secret_overrides["pdf_reading_mode"] = raw
    if "agent_unpaywall_oa_tool_enabled" in agent_tools:
        raw = agent_tools.get("agent_unpaywall_oa_tool_enabled")
        b = optional_stored_bool(raw)
        if b is not None:
            non_secret_overrides["agent_unpaywall_oa_tool_enabled"] = b
    if "agent_external_http_timeout_seconds" in agent_tools:
        raw = agent_tools.get("agent_external_http_timeout_seconds")
        try:
            t = float(raw)
        except (TypeError, ValueError):
            pass
        else:
            non_secret_overrides["agent_external_http_timeout_seconds"] = max(5.0, min(120.0, t))
    if "agent_external_max_calls_per_turn" in agent_tools:
        raw = agent_tools.get("agent_external_max_calls_per_turn")
        try:
            n = int(raw)
        except (TypeError, ValueError):
            pass
        else:
            non_secret_overrides["agent_external_max_calls_per_turn"] = max(1, min(32, n))
    if "agent_external_max_source_cards" in agent_tools:
        raw = agent_tools.get("agent_external_max_source_cards")
        try:
            n = int(raw)
        except (TypeError, ValueError):
            pass
        else:
            non_secret_overrides["agent_external_max_source_cards"] = max(4, min(128, n))
    if "agent_pdf_read_tool_enabled" in agent_tools:
        raw = agent_tools.get("agent_pdf_read_tool_enabled")
        b = optional_stored_bool(raw)
        if b is not None:
            non_secret_overrides["agent_pdf_read_tool_enabled"] = b
    if "agent_pdf_read_max_bytes" in agent_tools:
        raw = agent_tools.get("agent_pdf_read_max_bytes")
        try:
            n = int(raw)
        except (TypeError, ValueError):
            pass
        else:
            non_secret_overrides["agent_pdf_read_max_bytes"] = max(
                100_000, min(100_000_000, n)
            )
    if "agent_pdf_read_max_pages" in agent_tools:
        raw = agent_tools.get("agent_pdf_read_max_pages")
        try:
            n = int(raw)
        except (TypeError, ValueError):
            pass
        else:
            non_secret_overrides["agent_pdf_read_max_pages"] = max(1, min(500, n))
    if "agent_pdf_read_cache_ttl_seconds" in agent_tools:
        raw = agent_tools.get("agent_pdf_read_cache_ttl_seconds")
        try:
            n = int(raw)
        except (TypeError, ValueError):
            pass
        else:
            non_secret_overrides["agent_pdf_read_cache_ttl_seconds"] = max(0, min(86_400, n))
