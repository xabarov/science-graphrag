"""Runtime settings service with secret-aware LLM configuration."""

from __future__ import annotations

import os
import sys
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Any

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field

from science_graphrag.settings.repository import SettingsRepository
from science_graphrag.settings.secrets import SecretStore

if TYPE_CHECKING:
    from science_graphrag.config import Settings

_LLM_SECRET_KEY = "llm.api_key"

_LLM_ENV_KEY_HINT = "SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY (or MAIN_LLM_API_KEY / API_KEY per .env.example merge rules)"


def _settings_auth_required() -> bool:
    return os.getenv("SCIENCE_GRAPHRAG_SETTINGS_AUTH_REQUIRED", "false").lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _build_diagnostics_snapshot() -> dict[str, Any]:
    try:
        app_version = metadata.version("science-graphrag")
    except metadata.PackageNotFoundError:
        app_version = None
    git_commit = (
        os.getenv("SCIENCE_GRAPHRAG_GIT_COMMIT")
        or os.getenv("CI_COMMIT_SHA")
        or os.getenv("GIT_COMMIT_SHA")
    )
    return {
        "app_version": app_version or "unknown",
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "in_docker": Path("/.dockerenv").is_file(),
        "git_commit": git_commit,
    }


def _build_security_snapshot(base_settings: Settings) -> dict[str, Any]:
    return {
        "admin_api_key_configured": bool((base_settings.admin_api_key or "").strip()),
        "settings_auth_required": _settings_auth_required(),
    }


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * max(4, len(value) - 8)}{value[-4:]}"


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

    def get_snapshot(self, base_settings: Settings) -> SettingsSnapshot:
        """Return a masked UI-facing snapshot of runtime settings."""
        persisted = self._repository.load()
        llm = dict(persisted.get("llm") or {})
        ingestion_cfg = dict(persisted.get("ingestion") or {})
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

        timeout_seconds = llm.get("timeout_seconds")
        if timeout_seconds is None:
            timeout_seconds = base_settings.extraction_llm_timeout_seconds

        llm_snapshot = {
            "provider_mode": "openai_compatible",
            "base_url": llm.get("base_url") or base_settings.extraction_llm_base_url,
            "model": llm.get("model") or base_settings.extraction_llm_model,
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
            },
            "effective": {
                "resolved_base_url": llm.get("base_url") or base_settings.extraction_llm_base_url,
                "resolved_model": llm.get("model") or base_settings.extraction_llm_model,
                "resolved_timeout_seconds": timeout_seconds,
                "resolved_temperature": llm.get(
                    "temperature", base_settings.extraction_llm_temperature
                ),
                "resolved_enabled": bool(llm.get("enabled", base_settings.extraction_llm_enabled)),
            },
        }

        raw_upload_mb = ingestion_cfg.get("max_file_size_mb")
        try:
            persisted_upload_mb = int(raw_upload_mb) if raw_upload_mb is not None else None
        except (TypeError, ValueError):
            persisted_upload_mb = None
        if persisted_upload_mb is not None:
            persisted_upload_mb = max(1, min(2048, persisted_upload_mb))
        resolved_upload_mb = (
            persisted_upload_mb
            if persisted_upload_mb is not None
            else int(base_settings.workspace_upload_max_file_size_mb)
        )
        resolved_upload_mb = max(1, min(2048, resolved_upload_mb))

        ingestion_snapshot = {
            "max_file_size_mb": resolved_upload_mb,
            "status": {
                "last_updated_at": ingestion_meta.get("last_updated_at"),
                "last_updated_by": ingestion_meta.get("last_updated_by"),
            },
            "effective": {
                "resolved_max_file_size_mb": resolved_upload_mb,
            },
        }

        diagnostics_snapshot = _build_diagnostics_snapshot()
        security_snapshot = _build_security_snapshot(base_settings)

        work_dedup_snapshot = {
            "effective": {
                "qdrant_work_embeddings_collection": base_settings.qdrant_work_embeddings_collection,
                "qdrant_author_embeddings_collection": base_settings.qdrant_author_embeddings_collection,
                "work_dedup_sim_low": float(base_settings.work_dedup_sim_low),
                "work_dedup_sim_high": float(base_settings.work_dedup_sim_high),
                "work_dedup_max_candidates": int(base_settings.work_dedup_max_candidates),
                "work_dedup_llm_mode": str(base_settings.work_dedup_llm_mode),
                "work_dedup_llm_timeout_s": float(base_settings.work_dedup_llm_timeout_s),
                "author_dedup_sim_low": float(base_settings.author_dedup_sim_low),
                "author_dedup_sim_high": float(base_settings.author_dedup_sim_high),
                "author_dedup_max_candidates": int(base_settings.author_dedup_max_candidates),
            }
        }

        sections = [
            {
                "id": "general",
                "label": "General",
                "status": "ready",
                "description": "Interface language and environment documentation hints.",
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
                "status": "coming_soon",
                "description": "Neo4j, Qdrant, Postgres, OpenAlex, and external integration settings.",
            },
            {
                "id": "benchmark",
                "label": "Benchmark",
                "status": "coming_soon",
                "description": "Teacher/student defaults and benchmark-specific execution knobs.",
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

        non_secret_overrides = {
            "extraction_llm_base_url": llm.get("base_url") or base_settings.extraction_llm_base_url,
            "extraction_llm_model": llm.get("model") or base_settings.extraction_llm_model,
            "extraction_llm_temperature": llm.get(
                "temperature", base_settings.extraction_llm_temperature
            ),
            "extraction_llm_timeout_seconds": timeout_seconds,
        }
        if "enabled" in llm:
            non_secret_overrides["extraction_llm_enabled"] = bool(llm["enabled"])
        non_secret_overrides["workspace_upload_max_file_size_mb"] = resolved_upload_mb

        return SettingsSnapshot(
            non_secret_overrides=non_secret_overrides,
            llm=llm_snapshot,
            ingestion=ingestion_snapshot,
            diagnostics=diagnostics_snapshot,
            security=security_snapshot,
            sections=sections,
            work_dedup=work_dedup_snapshot,
        )

    def get_schema(self) -> dict[str, Any]:
        """Return a UI-friendly schema so future sections can extend the page safely."""
        return {
            "version": 2,
            "sections": [
                {
                    "id": "llm",
                    "fields": [
                        {"id": "base_url", "type": "url", "required": True},
                        {"id": "model", "type": "string", "required": True},
                        {
                            "id": "temperature",
                            "type": "number",
                            "required": True,
                            "min": 0.0,
                            "max": 2.0,
                        },
                        {
                            "id": "timeout_seconds",
                            "type": "number",
                            "required": True,
                            "min": 1.0,
                            "max": 900.0,
                        },
                        {"id": "api_key", "type": "secret", "required": False},
                    ],
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
                    ],
                },
            ],
        }

    def update_llm_settings(
        self,
        *,
        base_settings: Settings,
        base_url: str,
        model: str,
        temperature: float,
        timeout_seconds: float,
        actor: str,
        api_key: str | None = None,
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
            payload["llm"] = llm
            self._repository.save(payload)
            if api_key is not None:
                self._secret_store.set_secret(_LLM_SECRET_KEY, api_key.strip())
        return self.get_snapshot(base_settings)

    def update_ingestion_settings(
        self,
        *,
        base_settings: Settings,
        max_file_size_mb: int,
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
                    "_meta": {
                        "last_updated_at": _now_iso(),
                        "last_updated_by": actor,
                    },
                },
            )
            payload["ingestion"] = ingestion
            self._repository.save(payload)
        return self.get_snapshot(base_settings)

    def delete_llm_secret(self, *, base_settings: Settings) -> SettingsSnapshot:
        """Remove the managed LLM secret while keeping non-secret config intact."""
        with self._lock:
            self._secret_store.delete_secret(_LLM_SECRET_KEY)
        return self.get_snapshot(base_settings)

    def test_llm_connection(
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
                "message": "API key is not configured on the server and was not provided in the draft.",
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
