"""Runtime settings service with secret-aware LLM configuration."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
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
    sections: list[dict[str, Any]]


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
        meta = dict(llm.get("_meta") or {})
        api_key = self._secret_store.get_secret(_LLM_SECRET_KEY)
        configured = bool(api_key)

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
                "masked_key": _mask_secret(api_key),
                "secret_source": "server_managed" if configured else "none",
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
                "resolved_enabled": bool(
                    llm.get("enabled", base_settings.extraction_llm_enabled)
                ),
            },
        }

        sections = [
            {
                "id": "general",
                "label": "General",
                "status": "coming_soon",
                "description": "Environment, app identity, and global defaults.",
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
                "status": "coming_soon",
                "description": "PDF, front-matter, references, and extraction pipeline tuning.",
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
                "status": "coming_soon",
                "description": "Permissions, access model, and secret governance.",
            },
            {
                "id": "diagnostics",
                "label": "Diagnostics",
                "status": "coming_soon",
                "description": "Connection status, recent tests, and runtime environment diagnostics.",
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

        return SettingsSnapshot(
            non_secret_overrides=non_secret_overrides,
            llm=llm_snapshot,
            sections=sections,
        )

    def get_schema(self) -> dict[str, Any]:
        """Return a UI-friendly schema so future sections can extend the page safely."""
        return {
            "version": 1,
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
                }
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
