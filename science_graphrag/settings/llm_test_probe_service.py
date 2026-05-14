"""LLM connection probe draft and execution helpers for settings service."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

from science_graphrag.settings.llm_probe import run_llm_connection_probe
from science_graphrag.settings.secret_store_keys import LLM_API_KEY

if TYPE_CHECKING:
    from science_graphrag.config import Settings
    from science_graphrag.settings.secrets import SecretStore


class LlmTestDraft(BaseModel):
    """Draft configuration used for a one-off connection test."""

    model_config = ConfigDict(extra="ignore")

    base_url: str | None = None
    model: str | None = None
    api_key: str | None = None
    temperature: float | None = None
    timeout_seconds: float | None = None
    use_saved_secret: bool = True


def run_settings_llm_test_probe(
    *,
    base_settings: Settings,
    secret_store: SecretStore,
    effective_llm_snapshot: dict[str, Any],
    draft: LlmTestDraft | None = None,
    probe_fn: Any = run_llm_connection_probe,
) -> dict[str, Any]:
    """Run probe against effective settings with optional draft overrides."""
    effective = deepcopy(effective_llm_snapshot)
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
    api_key_source = "draft" if api_key else "missing"
    if not api_key and candidate.use_saved_secret:
        api_key = secret_store.get_secret(LLM_API_KEY)
        if api_key:
            api_key_source = "secret_store"
    if not api_key and candidate.use_saved_secret:
        env_fallback = (base_settings.extraction_llm_api_key or "").strip()
        if env_fallback:
            api_key = env_fallback
            api_key_source = "env_fallback"

    return probe_fn(
        base_url=base_url,
        model=model,
        timeout_seconds=timeout_seconds,
        temperature=temperature,
        api_key=api_key,
        used_saved_secret=(api_key_source == "secret_store"),
    )


__all__ = ["LlmTestDraft", "run_settings_llm_test_probe"]
