"""Runtime settings service with secret-aware LLM configuration."""

from __future__ import annotations

import os
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Any

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, ValidationError

from science_graphrag.settings.benchmark_defaults import (
    build_benchmark_ui_snapshot,
    merge_persisted_benchmark_family,
    normalize_benchmark_family_key,
    validate_merged_benchmark_family_prefs,
)
from science_graphrag.settings.llm_advanced_fields import (
    LLM_ADVANCED_RUNTIME_KEYS,
    advanced_effective_map,
    advanced_schema_fields,
    clamp_advanced_field,
    merge_llm_advanced_into_overrides,
    recommended_advanced_values,
    validate_merged_runtime_settings,
)
from science_graphrag.settings.repository import SettingsRepository
from science_graphrag.settings.secret_display import mask_short_secret as _mask_secret
from science_graphrag.settings.secrets import SecretStore
from science_graphrag.settings.snapshots import (
    build_diagnostics_snapshot,
    build_security_snapshot,
    resolve_ingestion_fields,
)
from science_graphrag.settings.storage_runtime import (
    _SK_DATABASE_URL,
    _SK_NEO4J_PASSWORD,
    _SK_S3_SECRET,
    apply_storage_json_updates,
    build_storage_ui_snapshot,
    merge_storage_runtime_fields,
)

if TYPE_CHECKING:
    from science_graphrag.config import Settings

_LLM_SECRET_KEY = "llm.api_key"
_UNSET_CHAT_MODEL = object()

_LLM_ENV_KEY_HINT = (
    "SCIENCE_GRAPHRAG_API_KEY (canonical unified key) or "
    "SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY / SCIENCE_GRAPHRAG_VL_API_KEY for compatibility"
)


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _runtime_settings_root(repo_root: Path) -> Path:
    return repo_root / "data" / "settings"


class LlmTestDraft(BaseModel):
    """Draft configuration used for a one-off connection test."""

    model_config = ConfigDict(extra="ignore")

    base_url: str | None = None
    model: str | None = None
    api_key: str | None = None
    temperature: float | None = None
    timeout_seconds: float | None = None
    use_saved_secret: bool = True


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


class SettingsService:
    """Read, write, and test runtime settings persisted outside env files."""

    def __init__(
        self,
        *,
        repo_root: Path,
        repository: SettingsRepository | None = None,
        secret_store: SecretStore | None = None,
    ) -> None:
        self._repo_root = repo_root
        root_dir = _runtime_settings_root(repo_root)
        self._repository = repository or SettingsRepository(root_dir)
        self._secret_store = secret_store or SecretStore(root_dir)
        self._lock = Lock()

    def _non_secret_overrides_dict(  # pylint: disable=too-many-locals
        self,
        base_settings: Settings,
        *,
        llm: dict[str, Any],
        ingestion_cfg: dict[str, Any],
        general_cfg: dict[str, Any] | None = None,
        storage_cfg: dict[str, Any] | None = None,
        storage_secret_explicit: dict[str, str | None] | None = None,
    ) -> dict[str, Any]:
        """Build the same overlay dict as ``get_snapshot`` uses for ``model_copy``."""

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
            self._secret_store,
            explicit_secrets=storage_secret_explicit,
        )
        non_secret_overrides.update(storage_fields)
        return non_secret_overrides

    def build_runtime_settings(self, base_settings: Settings) -> Settings:
        """Overlay persisted runtime overrides onto env-derived settings."""
        overrides = self.get_snapshot(base_settings).non_secret_overrides
        payload = dict(overrides)
        api_key = self._secret_store.get_secret(_LLM_SECRET_KEY)
        if api_key:
            payload["extraction_llm_api_key"] = api_key
        if not payload:
            return base_settings
        return base_settings.model_copy(update=payload)

    def get_snapshot(  # pylint: disable=too-many-locals,too-many-statements
        self, base_settings: Settings
    ) -> SettingsSnapshot:
        """Return a masked UI-facing snapshot of runtime settings."""
        persisted = self._repository.load()
        llm = dict(persisted.get("llm") or {})
        ingestion_cfg = dict(persisted.get("ingestion") or {})
        general_cfg = dict(persisted.get("general") or {})
        storage_cfg = dict(persisted.get("storage") or {})
        general_meta = dict(general_cfg.get("_meta") or {})
        ingestion_meta = dict(ingestion_cfg.get("_meta") or {})
        meta = dict(llm.get("_meta") or {})
        saved_secret = self._secret_store.get_secret(_LLM_SECRET_KEY)
        has_saved_secret = bool(saved_secret)
        env_key_raw = base_settings.extraction_llm_api_key
        env_key = (env_key_raw or "").strip() if env_key_raw else ""
        has_env_key = bool(env_key)

        if has_saved_secret:
            secret_source = "server_managed"
            active_key_for_mask = saved_secret
        elif has_env_key:
            secret_source = "environment"
            active_key_for_mask = env_key
        else:
            secret_source = "none"
            active_key_for_mask = None

        configured = has_saved_secret or has_env_key
        needs_initial_setup = not configured
        # Prefer Settings fields: matches pydantic/.env resolution, not getenv alone.
        canonical_api_key_env_set = bool((base_settings.api_key or "").strip())
        legacy_extraction_key_env_set = bool(
            os.getenv("SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY", "").strip()
        )
        vl_raw = (base_settings.vl_api_key or "").strip()
        extraction_effective = (base_settings.extraction_llm_api_key or "").strip()
        # Redundant VL_API_KEY identical to unified/extraction should not surface as an override.
        vl_dedicated_api_key = bool(vl_raw) and vl_raw != extraction_effective
        uses_env_defaults = not (
            bool(str(llm.get("base_url") or "").strip())
            or bool(str(llm.get("model") or "").strip())
        )
        legacy_override_detected = bool(vl_dedicated_api_key or legacy_extraction_key_env_set)
        setup_status = "needs_api_key" if needs_initial_setup else "ready"

        timeout_seconds = llm.get("timeout_seconds")
        if timeout_seconds is None:
            timeout_seconds = base_settings.extraction_llm_timeout_seconds

        persisted_chat = str(llm.get("chat_model") or "").strip()
        env_chat = str(base_settings.chat_llm_model or "").strip()
        resolved_chat_model = persisted_chat or env_chat or base_settings.extraction_llm_model

        persisted_vl_model = str(llm.get("vl_model") or "").strip()
        persisted_vl_base = str(llm.get("vl_base_url") or "").strip().rstrip("/")
        resolved_vl_model = persisted_vl_model or base_settings.vl_model
        resolved_vl_base_url = persisted_vl_base or base_settings.vl_base_url

        llm_snapshot = {
            "provider_mode": "openai_compatible",
            "base_url": llm.get("base_url") or base_settings.extraction_llm_base_url,
            "model": llm.get("model") or base_settings.extraction_llm_model,
            "vl_model": persisted_vl_model,
            "vl_base_url": persisted_vl_base,
            "chat_model": persisted_chat,
            "temperature": llm.get("temperature", base_settings.extraction_llm_temperature),
            "timeout_seconds": timeout_seconds,
            "status": {
                "configured": configured,
                "has_saved_secret": has_saved_secret,
                "masked_key": _mask_secret(active_key_for_mask),
                "secret_source": secret_source,
                "env_key_hint": _LLM_ENV_KEY_HINT if secret_source == "environment" else None,
                "last_updated_at": meta.get("last_updated_at"),
                "last_updated_by": meta.get("last_updated_by"),
                "needs_initial_setup": needs_initial_setup,
                "setup_status": setup_status,
                "uses_env_defaults": uses_env_defaults,
                "legacy_override_detected": legacy_override_detected,
                "canonical_api_key_env_set": canonical_api_key_env_set,
                "legacy_extraction_key_env_set": legacy_extraction_key_env_set,
                # API key name kept for stability; true only when VL env key differs
                # from extraction key.
                "vl_api_key_explicit_env": vl_dedicated_api_key,
            },
            "effective": {
                "resolved_base_url": llm.get("base_url") or base_settings.extraction_llm_base_url,
                "resolved_model": llm.get("model") or base_settings.extraction_llm_model,
                "resolved_chat_model": resolved_chat_model,
                "resolved_timeout_seconds": timeout_seconds,
                "resolved_temperature": llm.get(
                    "temperature", base_settings.extraction_llm_temperature
                ),
                "resolved_enabled": bool(llm.get("enabled", base_settings.extraction_llm_enabled)),
                "resolved_vl_model": resolved_vl_model,
                "resolved_vl_base_url": resolved_vl_base_url,
            },
        }

        adv_eff = advanced_effective_map(llm, base_settings)
        llm_snapshot["advanced_controls"] = {
            k: {"persisted": llm[k] if k in llm else None, "effective": adv_eff[k]}
            for k in LLM_ADVANCED_RUNTIME_KEYS
        }
        llm_snapshot["recommended_advanced"] = recommended_advanced_values()

        resolved_upload_mb, resolved_claims_enabled = resolve_ingestion_fields(
            ingestion_cfg, base_settings
        )

        ingestion_snapshot = {
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

        persisted_openalex_mailto = str(general_cfg.get("openalex_mailto") or "").strip()
        resolved_openalex_mailto = (
            persisted_openalex_mailto or str(base_settings.openalex_mailto or "").strip()
        )
        general_snapshot = {
            "openalex_mailto": persisted_openalex_mailto,
            "effective": {"resolved_openalex_mailto": resolved_openalex_mailto},
            "status": {
                "source": "server_managed" if persisted_openalex_mailto else "environment",
                "last_updated_at": general_meta.get("last_updated_at"),
                "last_updated_by": general_meta.get("last_updated_by"),
                "uses_env_default": not persisted_openalex_mailto,
            },
        }

        storage_snapshot = build_storage_ui_snapshot(
            base_settings=base_settings,
            storage_cfg=storage_cfg,
            secret_store=self._secret_store,
        )

        benchmark_cfg = dict(persisted.get("benchmark") or {})
        benchmark_snapshot = build_benchmark_ui_snapshot(benchmark_cfg)

        diagnostics_snapshot = build_diagnostics_snapshot()
        security_snapshot = build_security_snapshot(base_settings)

        non_secret_overrides = self._non_secret_overrides_dict(
            base_settings,
            llm=llm,
            ingestion_cfg=ingestion_cfg,
            general_cfg=general_cfg,
            storage_cfg=storage_cfg,
        )
        merged_settings = base_settings.model_copy(update=non_secret_overrides)

        q_work = merged_settings.qdrant_work_embeddings_collection
        q_author = merged_settings.qdrant_author_embeddings_collection
        work_dedup_snapshot = {
            "effective": {
                "qdrant_work_embeddings_collection": q_work,
                "qdrant_author_embeddings_collection": q_author,
                "work_dedup_sim_low": float(base_settings.work_dedup_sim_low),
                "work_dedup_sim_high": float(base_settings.work_dedup_sim_high),
                "work_dedup_max_candidates": int(base_settings.work_dedup_max_candidates),
                "work_dedup_llm_mode": str(base_settings.work_dedup_llm_mode),
                "work_dedup_llm_timeout_s": float(merged_settings.work_dedup_llm_timeout_s),
                "author_dedup_sim_low": float(base_settings.author_dedup_sim_low),
                "author_dedup_sim_high": float(base_settings.author_dedup_sim_high),
                "author_dedup_max_candidates": int(base_settings.author_dedup_max_candidates),
                "author_dedup_llm_timeout_s": float(merged_settings.author_dedup_llm_timeout_s),
            }
        }

        sections = [
            {
                "id": "general",
                "label": "General",
                "status": "ready",
                "description": (
                    "Interface language, appearance, and server-managed OpenAlex contact email."
                ),
            },
            {
                "id": "llm",
                "label": "LLM",
                "status": "ready",
                "description": "Provider endpoint, model defaults, credentials, and test tools.",
            },
            {
                "id": "ingestion",
                "label": "Ingestion",
                "status": "ready",
                "description": "Workspace file uploads and related limits.",
            },
            {
                "id": "storage",
                "label": "Storage & Integrations",
                "status": "ready",
                "description": ("Neo4j, Qdrant, Postgres, Redis, object storage, and local paths."),
            },
            {
                "id": "benchmark",
                "label": "Benchmark",
                "status": "ready",
                "description": ("Teacher/student defaults and benchmark-specific execution knobs."),
            },
            {
                "id": "security",
                "label": "Security & Access",
                "status": "ready",
                "description": "Read-only flags for admin and settings API protection.",
            },
            {
                "id": "diagnostics",
                "label": "Diagnostics",
                "status": "ready",
                "description": "Runtime build identity (read-only).",
            },
        ]

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
        )

    def get_schema(self) -> dict[str, Any]:
        """Return a UI-friendly schema so future sections can extend the page safely."""
        llm_fields: list[dict[str, Any]] = [
            {"id": "base_url", "type": "url", "required": True, "group": "llm_provider"},
            {"id": "model", "type": "string", "required": True, "group": "llm_provider"},
            {
                "id": "chat_model",
                "type": "string",
                "required": False,
                "group": "llm_provider",
                "description": (
                    "Research chat model override; empty uses env "
                    "SCIENCE_GRAPHRAG_CHAT_LLM_MODEL or extraction model."
                ),
            },
            {
                "id": "temperature",
                "type": "number",
                "required": True,
                "min": 0.0,
                "max": 2.0,
                "group": "llm_provider",
            },
            {
                "id": "timeout_seconds",
                "type": "number",
                "required": True,
                "min": 1.0,
                "max": 900.0,
                "group": "llm_provider",
                "description": (
                    "Shared extraction/provider HTTP transport timeout "
                    "(extraction_llm_timeout_seconds)."
                ),
            },
            {
                "id": "vl_model",
                "type": "string",
                "required": False,
                "group": "llm_provider",
                "description": (
                    "Vision-language model id for PDF→Markdown " "(SCIENCE_GRAPHRAG_VL_MODEL)."
                ),
            },
            {
                "id": "vl_base_url",
                "type": "url",
                "required": False,
                "group": "llm_provider",
                "description": (
                    "OpenAI-compatible base URL for VL; "
                    "defaults to extraction base URL when unset."
                ),
            },
            {"id": "api_key", "type": "secret", "required": False, "group": "llm_provider"},
            {
                "id": "runtime_overrides",
                "type": "object",
                "required": False,
                "group": "llm_provider",
                "description": (
                    "Nested map of advanced LLM runtime limits (same keys as Settings)."
                ),
            },
        ]
        llm_fields.extend(advanced_schema_fields())
        storage_fields: list[dict[str, Any]] = [
            {"id": "neo4j_uri", "type": "url", "required": False, "group": "neo4j"},
            {"id": "neo4j_user", "type": "string", "required": False, "group": "neo4j"},
            {"id": "neo4j_password", "type": "secret", "required": False, "group": "neo4j"},
            {"id": "qdrant_url", "type": "url", "required": False, "group": "qdrant"},
            {"id": "qdrant_collection", "type": "string", "required": False, "group": "qdrant"},
            {
                "id": "qdrant_claims_collection",
                "type": "string",
                "required": False,
                "group": "qdrant",
            },
            {
                "id": "qdrant_work_embeddings_collection",
                "type": "string",
                "required": False,
                "group": "qdrant",
            },
            {
                "id": "qdrant_author_embeddings_collection",
                "type": "string",
                "required": False,
                "group": "qdrant",
            },
            {"id": "database_url", "type": "secret", "required": False, "group": "postgres"},
            {"id": "redis_url", "type": "url", "required": False, "group": "redis"},
            {"id": "blob_root", "type": "string", "required": False, "group": "paths"},
            {"id": "artifact_root", "type": "string", "required": False, "group": "paths"},
            {"id": "s3_endpoint_url", "type": "url", "required": False, "group": "s3"},
            {"id": "s3_bucket", "type": "string", "required": False, "group": "s3"},
            {"id": "s3_use_ssl", "type": "boolean", "required": False, "group": "s3"},
            {
                "id": "s3_addressing_style",
                "type": "string",
                "required": False,
                "group": "s3",
            },
            {"id": "s3_artifact_key_prefix", "type": "string", "required": False, "group": "s3"},
            {"id": "s3_access_key_id", "type": "string", "required": False, "group": "s3"},
            {"id": "s3_secret_access_key", "type": "secret", "required": False, "group": "s3"},
            {
                "id": "s3_benchmark_runs_key_prefix",
                "type": "string",
                "required": False,
                "group": "s3",
            },
            {
                "id": "s3_diagnostics_key_prefix",
                "type": "string",
                "required": False,
                "group": "s3",
            },
        ]
        benchmark_fields: list[dict[str, Any]] = [
            {
                "id": "by_family",
                "type": "object",
                "required": False,
                "group": "benchmark_defaults",
                "description": (
                    "Per-family defaults for benchmark launcher (model profile, gold, thresholds, API hints)."
                ),
            },
        ]
        return {
            "version": 10,
            "sections": [
                {
                    "id": "general",
                    "fields": [
                        {
                            "id": "openalex_mailto",
                            "type": "string",
                            "required": True,
                            "group": "openalex",
                            "description": (
                                "Polite-pool contact for OpenAlex HTTP API "
                                "(SCIENCE_GRAPHRAG_OPENALEX_MAILTO when not overridden here)."
                            ),
                        },
                    ],
                },
                {
                    "id": "llm",
                    "fields": llm_fields,
                },
                {
                    "id": "ingestion",
                    "fields": [
                        {
                            "id": "max_file_size_mb",
                            "type": "integer",
                            "required": True,
                            "min": 1,
                            "max": 2048,
                        },
                        {
                            "id": "claims_extraction_enabled",
                            "type": "boolean",
                            "required": True,
                        },
                    ],
                },
                {"id": "storage", "fields": storage_fields},
                {"id": "benchmark", "fields": benchmark_fields},
            ],
        }

    def update_llm_settings(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals,too-many-branches
        self,
        *,
        base_settings: Settings,
        base_url: str,
        model: str,
        temperature: float,
        timeout_seconds: float,
        actor: str,
        api_key: str | None = None,
        chat_model: Any = _UNSET_CHAT_MODEL,
        vl_model: Any = _UNSET_CHAT_MODEL,
        vl_base_url: Any = _UNSET_CHAT_MODEL,
        advanced_patch: dict[str, Any] | None = None,
    ) -> SettingsSnapshot:
        """Persist editable LLM config and optionally replace the managed secret."""
        with self._lock:
            payload = self._repository.load()
            llm = dict(payload.get("llm") or {})
            llm.update(
                {
                    "base_url": base_url.rstrip("/"),
                    "model": model.strip(),
                    "temperature": float(temperature),
                    "timeout_seconds": float(timeout_seconds),
                    "enabled": True,
                    "_meta": {
                        "last_updated_at": _now_iso(),
                        "last_updated_by": actor,
                    },
                }
            )
            if chat_model is not _UNSET_CHAT_MODEL:
                cm = str(chat_model or "").strip()
                if cm:
                    llm["chat_model"] = cm
                else:
                    llm.pop("chat_model", None)
            if vl_model is not _UNSET_CHAT_MODEL:
                vm = str(vl_model or "").strip()
                if vm:
                    llm["vl_model"] = vm
                else:
                    llm.pop("vl_model", None)
            if vl_base_url is not _UNSET_CHAT_MODEL:
                vb = str(vl_base_url or "").strip().rstrip("/")
                if vb:
                    llm["vl_base_url"] = vb
                else:
                    llm.pop("vl_base_url", None)
            if advanced_patch:
                for key, raw in advanced_patch.items():
                    if key in LLM_ADVANCED_RUNTIME_KEYS:
                        llm[key] = clamp_advanced_field(key, raw, base_settings)
            ingestion_cfg = dict(payload.get("ingestion") or {})
            general_cfg = dict(payload.get("general") or {})
            storage_cfg = dict(payload.get("storage") or {})
            merged_non_secret = self._non_secret_overrides_dict(
                base_settings,
                llm=llm,
                ingestion_cfg=ingestion_cfg,
                general_cfg=general_cfg,
                storage_cfg=storage_cfg,
            )
            validate_merged_runtime_settings(
                base_settings.model_copy(update=merged_non_secret),
            )
            payload["llm"] = llm
            self._repository.save(payload)
            if api_key is not None:
                self._secret_store.set_secret(_LLM_SECRET_KEY, api_key.strip())
        return self.get_snapshot(base_settings)

    def update_ingestion_settings(
        self,
        base_settings: Settings,
        max_file_size_mb: int,
        claims_extraction_enabled: bool,
        actor: str,
    ) -> SettingsSnapshot:
        """Persist workspace upload size limit (megabytes per file)."""
        bounded = max(1, min(2048, int(max_file_size_mb)))
        with self._lock:
            payload = self._repository.load()
            ingestion = dict(payload.get("ingestion") or {})
            ingestion.update(
                {
                    "max_file_size_mb": bounded,
                    "claims_extraction_enabled": bool(claims_extraction_enabled),
                    "_meta": {
                        "last_updated_at": _now_iso(),
                        "last_updated_by": actor,
                    },
                },
            )
            payload["ingestion"] = ingestion
            self._repository.save(payload)
        return self.get_snapshot(base_settings)

    def update_general_settings(
        self,
        *,
        base_settings: Settings,
        openalex_mailto: str,
        actor: str,
    ) -> SettingsSnapshot:
        """Persist OpenAlex polite-pool contact email (non-secret)."""

        mailto = str(openalex_mailto or "").strip()
        if "@" not in mailto or " " in mailto:
            raise ValueError("openalex_mailto must be a single email-like address")
        if len(mailto) > 320:
            raise ValueError("openalex_mailto is too long")

        with self._lock:
            payload = self._repository.load()
            general = dict(payload.get("general") or {})
            general["openalex_mailto"] = mailto
            general["_meta"] = {
                "last_updated_at": _now_iso(),
                "last_updated_by": actor,
            }
            payload["general"] = general
            llm = dict(payload.get("llm") or {})
            ingestion_cfg = dict(payload.get("ingestion") or {})
            storage_cfg = dict(payload.get("storage") or {})
            merged_non_secret = self._non_secret_overrides_dict(
                base_settings,
                llm=llm,
                ingestion_cfg=ingestion_cfg,
                general_cfg=general,
                storage_cfg=storage_cfg,
            )
            validate_merged_runtime_settings(
                base_settings.model_copy(update=merged_non_secret),
            )
            self._repository.save(payload)
        return self.get_snapshot(base_settings)

    def update_storage_settings(  # pylint: disable=too-many-branches
        self,
        *,
        base_settings: Settings,
        actor: str,
        updates: dict[str, Any],
    ) -> SettingsSnapshot:
        """Persist storage / integration overrides (requires API restart to reconnect stores)."""

        if not updates:
            return self.get_snapshot(base_settings)

        secret_body_keys = ("neo4j_password", "database_url", "s3_secret_access_key")
        with self._lock:
            payload = self._repository.load()
            storage_next = dict(payload.get("storage") or {})
            json_updates = {k: v for k, v in updates.items() if k not in secret_body_keys}
            apply_storage_json_updates(storage_next, json_updates)

            explicit: dict[str, str | None] = {}
            if "neo4j_password" in updates:
                explicit[_SK_NEO4J_PASSWORD] = updates["neo4j_password"]
            if "database_url" in updates:
                explicit[_SK_DATABASE_URL] = updates["database_url"]
            if "s3_secret_access_key" in updates:
                explicit[_SK_S3_SECRET] = updates["s3_secret_access_key"]

            llm = dict(payload.get("llm") or {})
            ingestion_cfg = dict(payload.get("ingestion") or {})
            general_cfg = dict(payload.get("general") or {})
            merged_non_secret = self._non_secret_overrides_dict(
                base_settings,
                llm=llm,
                ingestion_cfg=ingestion_cfg,
                general_cfg=general_cfg,
                storage_cfg=storage_next,
                storage_secret_explicit=explicit if explicit else None,
            )
            candidate = base_settings.model_copy(update=merged_non_secret)
            validate_merged_runtime_settings(candidate)
            try:
                type(candidate).model_validate(candidate.model_dump(mode="python"))
            except ValidationError as exc:
                raise ValueError(str(exc)) from exc

            storage_next["_meta"] = {
                "last_updated_at": _now_iso(),
                "last_updated_by": actor,
                "restart_recommended": True,
            }
            payload["storage"] = storage_next

            if "neo4j_password" in updates:
                val = updates["neo4j_password"]
                if val is None or (isinstance(val, str) and not str(val).strip()):
                    self._secret_store.delete_secret(_SK_NEO4J_PASSWORD)
                else:
                    self._secret_store.set_secret(_SK_NEO4J_PASSWORD, str(val).strip())
            if "database_url" in updates:
                val = updates["database_url"]
                if val is None or (isinstance(val, str) and not str(val).strip()):
                    self._secret_store.delete_secret(_SK_DATABASE_URL)
                else:
                    self._secret_store.set_secret(_SK_DATABASE_URL, str(val).strip())
            if "s3_secret_access_key" in updates:
                val = updates["s3_secret_access_key"]
                if val is None or (isinstance(val, str) and not str(val).strip()):
                    self._secret_store.delete_secret(_SK_S3_SECRET)
                else:
                    self._secret_store.set_secret(_SK_S3_SECRET, str(val).strip())

            self._repository.save(payload)
        return self.get_snapshot(base_settings)

    def update_benchmark_settings(
        self,
        *,
        base_settings: Settings,
        actor: str,
        by_family: dict[str, dict[str, Any]],
    ) -> SettingsSnapshot:
        """Persist per-family benchmark launcher defaults (non-secret, UI + launcher merge)."""
        if not by_family:
            return self.get_snapshot(base_settings)
        allowed_keys = (
            "model_profile",
            "custom_model_id",
            "gold_source",
            "threshold_profile",
            "base_url_override",
            "api_key_env_name",
        )
        with self._lock:
            payload = self._repository.load()
            bench = dict(payload.get("benchmark") or {})
            by_existing: dict[str, Any] = dict(bench.get("by_family") or {})
            for fam_key, patch in by_family.items():
                fam = normalize_benchmark_family_key(fam_key)
                prev_slice = dict(by_existing.get(fam) or {})
                merged_input = dict(prev_slice)
                for key in allowed_keys:
                    if key in patch:
                        merged_input[key] = patch[key]
                merged = merge_persisted_benchmark_family(fam, merged_input)
                validate_merged_benchmark_family_prefs(fam, merged)
                by_existing[fam] = merged
            bench["by_family"] = by_existing
            bench["_meta"] = {
                "last_updated_at": _now_iso(),
                "last_updated_by": actor,
            }
            payload["benchmark"] = bench
            self._repository.save(payload)
        return self.get_snapshot(base_settings)

    def delete_llm_secret(self, *, base_settings: Settings) -> SettingsSnapshot:
        """Remove the managed LLM secret while keeping non-secret config intact."""
        with self._lock:
            self._secret_store.delete_secret(_LLM_SECRET_KEY)
        return self.get_snapshot(base_settings)

    def test_llm_connection(  # pylint: disable=too-many-locals
        self,
        *,
        base_settings: Settings,
        actor: str,
        draft: LlmTestDraft | None = None,
    ) -> dict[str, Any]:
        """Run a minimal OpenAI-compatible probe using current or draft settings."""
        del actor  # Reserved for future audit trail.
        snapshot = self.get_snapshot(base_settings)
        effective = deepcopy(snapshot.llm["effective"])
        candidate = draft or LlmTestDraft()

        base_url = (candidate.base_url or effective["resolved_base_url"]).strip().rstrip("/")
        model = (candidate.model or effective["resolved_model"]).strip()
        timeout_seconds = float(
            candidate.timeout_seconds
            if candidate.timeout_seconds is not None
            else effective["resolved_timeout_seconds"]
        )
        temperature = float(
            candidate.temperature
            if candidate.temperature is not None
            else effective["resolved_temperature"]
        )
        api_key = (candidate.api_key or "").strip() if candidate.api_key is not None else None
        if not api_key and candidate.use_saved_secret:
            api_key = self._secret_store.get_secret(_LLM_SECRET_KEY)
        if not api_key and candidate.use_saved_secret:
            env_fallback = (base_settings.extraction_llm_api_key or "").strip()
            if env_fallback:
                api_key = env_fallback

        if not api_key:
            return {
                "status": "error",
                "error_kind": "missing_api_key",
                "message": (
                    "API key is not configured (set SCIENCE_GRAPHRAG_API_KEY or "
                    "SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY, save a key in Settings, "
                    "or pass api_key in the draft request)."
                ),
                "resolved": {
                    "base_url": base_url,
                    "model": model,
                    "timeout_seconds": timeout_seconds,
                    "temperature": temperature,
                    "used_saved_secret": False,
                },
            }

        started = datetime.now(tz=UTC)
        try:
            client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout_seconds)
            completion = client.chat.completions.create(
                model=model,
                temperature=temperature,
                max_tokens=12,
                messages=[
                    {"role": "system", "content": "Reply with exactly OK."},
                    {"role": "user", "content": "Connection test. Reply OK."},
                ],
            )
            reply = (
                completion.choices[0].message.content if completion and completion.choices else None
            ) or ""
            elapsed_ms = int((datetime.now(tz=UTC) - started).total_seconds() * 1000)
            normalized = reply.strip()
            return {
                "status": "connected" if normalized.upper() == "OK" else "unexpected_response",
                "message": normalized or "No response text returned by provider.",
                "latency_ms": elapsed_ms,
                "tested_at": _now_iso(),
                "resolved": {
                    "base_url": base_url,
                    "model": model,
                    "timeout_seconds": timeout_seconds,
                    "temperature": temperature,
                    "used_saved_secret": candidate.api_key is None,
                },
            }
        except Exception as exc:  # noqa: BLE001
            text = str(exc)
            lower = text.lower()
            if "401" in lower or "unauthorized" in lower or "invalid api key" in lower:
                error_kind = "auth_failed"
            elif "404" in lower or "model" in lower and "not found" in lower:
                error_kind = "model_unavailable"
            elif "timeout" in lower:
                error_kind = "timeout"
            else:
                error_kind = "provider_error"
            return {
                "status": "error",
                "error_kind": error_kind,
                "message": text,
                "tested_at": _now_iso(),
                "resolved": {
                    "base_url": base_url,
                    "model": model,
                    "timeout_seconds": timeout_seconds,
                    "temperature": temperature,
                    "used_saved_secret": candidate.api_key is None,
                },
            }
