"""One-time import of LLM configuration from process Settings into persisted JSON + vault.

After ``bootstrap_from_env_v1`` is set under ``llm._meta``, runtime merge may treat secrets
as authoritative (no silent re-injection of env API keys when vault is empty).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from science_graphrag.settings.secret_store_keys import LLM_API_KEY, LLM_VISION_API_KEY

if TYPE_CHECKING:
    from science_graphrag.config import Settings
    from science_graphrag.settings.service import SettingsService

BOOTSTRAP_FLAG = "bootstrap_from_env_v1"


def _strip(val: object | None) -> str:
    if val is None:
        return ""
    return str(val).strip()


def llm_bootstrap_applied(persisted: dict[str, Any]) -> bool:
    llm = dict(persisted.get("llm") or {})
    meta = dict(llm.get("_meta") or {})
    return bool(meta.get(BOOTSTRAP_FLAG))


def ensure_llm_runtime_bootstrap_from_env(service: SettingsService, base_settings: Settings) -> None:
    """Populate persisted LLM + vault from env-derived Settings once per repo (idempotent)."""

    with service._lock:
        payload = dict(service._repository.load())
        llm = dict(payload.get("llm") or {})
        meta = dict(llm.get("_meta") or {})
        if meta.get(BOOTSTRAP_FLAG):
            return

        changed = False

        if not _strip(llm.get("base_url")) and _strip(base_settings.extraction_llm_base_url):
            llm["base_url"] = _strip(base_settings.extraction_llm_base_url)
            changed = True
        if not _strip(llm.get("model")) and _strip(base_settings.extraction_llm_model):
            llm["model"] = _strip(base_settings.extraction_llm_model)
            changed = True
        if "temperature" not in llm:
            llm["temperature"] = float(base_settings.extraction_llm_temperature)
            changed = True
        if "timeout_seconds" not in llm or not str(llm.get("timeout_seconds") or "").strip():
            llm["timeout_seconds"] = float(base_settings.extraction_llm_timeout_seconds)
            changed = True
        if "enabled" not in llm:
            llm["enabled"] = bool(base_settings.extraction_llm_enabled)
            changed = True

        cm = _strip(base_settings.chat_llm_model)
        if cm and not _strip(llm.get("chat_model")):
            llm["chat_model"] = cm
            changed = True

        vm = _strip(base_settings.vl_model)
        if vm and not _strip(llm.get("vl_model")):
            llm["vl_model"] = vm
            changed = True
        vb = _strip(base_settings.vl_base_url)
        if vb and not _strip(llm.get("vl_base_url")):
            llm["vl_base_url"] = vb.rstrip("/")
            changed = True

        ex_key = _strip(base_settings.extraction_llm_api_key)
        if ex_key and not service._secret_store.get_secret(LLM_API_KEY):
            service._secret_store.set_secret(LLM_API_KEY, ex_key)
            changed = True

        vl_raw = _strip(base_settings.vl_api_key)
        if vl_raw and vl_raw != ex_key and not service._secret_store.get_secret(LLM_VISION_API_KEY):
            service._secret_store.set_secret(LLM_VISION_API_KEY, vl_raw)
            changed = True

        meta[BOOTSTRAP_FLAG] = True
        meta["last_updated_at"] = datetime.now(tz=UTC).isoformat()
        meta.setdefault("last_updated_by", "runtime_bootstrap")
        llm["_meta"] = meta
        payload["llm"] = llm
        service._repository.save(payload)
        del changed  # repository save always; flag always set


__all__ = ["BOOTSTRAP_FLAG", "ensure_llm_runtime_bootstrap_from_env", "llm_bootstrap_applied"]
