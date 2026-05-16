"""Task-oriented persisted LLM blocks under ``llm.tasks`` (Unified Task LLM Settings).

Legacy flat keys (``base_url``, ``chat_model``, ``embeddings_mode``, …) are merged
into ``tasks`` on read and stripped on write after migration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from science_graphrag.config import Settings

LLM_TASK_ROLES: tuple[str, ...] = ("extraction", "chat", "vision", "embeddings")

_LEGACY_FLAT_KEYS: frozenset[str] = frozenset(
    {
        "base_url",
        "model",
        "temperature",
        "timeout_seconds",
        "chat_model",
        "chat_base_url",
        "vl_model",
        "vl_base_url",
        "embeddings_mode",
        "embeddings_model",
    }
)


def _strip(val: object | None) -> str:
    if val is None:
        return ""
    return str(val).strip()


def _float_or(raw: object | None, default: float) -> float:
    if raw is None:
        return float(default)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return float(default)


def _tasks_from_legacy_flat(llm: dict[str, Any], base: Settings) -> dict[str, dict[str, Any]]:
    """Derive task blocks from historic flat ``llm`` JSON + env defaults."""

    ext_base = _strip(llm.get("base_url")) or _strip(base.extraction_llm_base_url)
    ext_model = _strip(llm.get("model")) or _strip(base.extraction_llm_model)
    ext_temp = _float_or(llm.get("temperature"), base.extraction_llm_temperature)
    ext_timeout = _float_or(llm.get("timeout_seconds"), base.extraction_llm_timeout_seconds)

    chat_model = _strip(llm.get("chat_model")) or _strip(base.chat_llm_model or "")
    chat_base = _strip(llm.get("chat_base_url")).rstrip("/") or _strip(
        (base.chat_llm_base_url or "").strip().rstrip("/")
    )
    chat_temp = ext_temp
    chat_timeout = ext_timeout

    vl_model = _strip(llm.get("vl_model")) or _strip(base.vl_model)
    vl_base = _strip(llm.get("vl_base_url")).rstrip("/") or _strip(base.vl_base_url).rstrip("/")
    vl_temp = 0.0
    vl_timeout = 300.0

    emb_mode_raw = _strip(llm.get("embeddings_mode")).lower()
    if emb_mode_raw == "local":
        emb_mode = "local"
    else:
        emb_mode = "http"
    emb_model = _strip(llm.get("embeddings_model"))
    emb_base = ""
    emb_timeout = 60.0

    return {
        "extraction": {
            "base_url": ext_base,
            "model": ext_model,
            "temperature": ext_temp,
            "timeout_seconds": ext_timeout,
        },
        "chat": {
            "base_url": chat_base,
            "model": chat_model,
            "temperature": chat_temp,
            "timeout_seconds": chat_timeout,
        },
        "vision": {
            "base_url": vl_base,
            "model": vl_model,
            "temperature": vl_temp,
            "timeout_seconds": vl_timeout,
        },
        "embeddings": {
            "mode": emb_mode,
            "base_url": emb_base,
            "model": emb_model,
            "timeout_seconds": emb_timeout,
        },
    }


def _deep_merge_task_block(
    base_block: dict[str, Any],
    patch: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(patch, dict):
        return dict(base_block)
    out = dict(base_block)
    for k, v in patch.items():
        if v is None:
            continue
        out[k] = v
    return out


def get_normalized_llm_tasks(llm: dict[str, Any], base: Settings) -> dict[str, dict[str, Any]]:
    """Return merged task blocks (legacy flat + optional ``llm.tasks`` overlay)."""

    legacy_tasks = _tasks_from_legacy_flat(llm, base)
    nested = llm.get("tasks")
    if not isinstance(nested, dict):
        return legacy_tasks
    out: dict[str, dict[str, Any]] = {}
    for role in LLM_TASK_ROLES:
        merged = _deep_merge_task_block(legacy_tasks[role], nested.get(role))
        if role == "embeddings":
            mode = str(merged.get("mode") or "http").strip().lower()
            merged["mode"] = "local" if mode == "local" else "http"
        out[role] = merged
    return out


def strip_legacy_llm_task_flat_keys(llm: dict[str, Any]) -> None:
    """Remove migrated flat keys after ``tasks`` became canonical."""

    for k in _LEGACY_FLAT_KEYS:
        llm.pop(k, None)


def apply_tasks_to_llm_dict(llm: dict[str, Any], tasks: dict[str, dict[str, Any]]) -> None:
    """Persist canonical ``tasks`` subtree (shallow copy per role)."""

    llm["tasks"] = {role: dict(tasks.get(role) or {}) for role in LLM_TASK_ROLES}


def merge_partial_tasks_patch(
    prev_tasks: dict[str, dict[str, Any]],
    patch: dict[str, dict[str, Any] | None],
) -> dict[str, dict[str, Any]]:
    """Deep-merge operator PATCH ``tasks`` into previous task blocks."""

    out: dict[str, dict[str, Any]] = {
        role: dict(prev_tasks.get(role) or {}) for role in LLM_TASK_ROLES
    }
    for role, delta in (patch or {}).items():
        if role not in LLM_TASK_ROLES or not isinstance(delta, dict):
            continue
        base_role = dict(out.get(role) or {})
        for k, v in delta.items():
            if v is None:
                continue
            if k == "model" and isinstance(v, str) and not v.strip():
                base_role.pop("model", None)
                continue
            if k == "base_url" and isinstance(v, str) and not v.strip():
                base_role["base_url"] = ""
                continue
            base_role[k] = v
        out[role] = base_role
    return out


def embeddings_public_mode(tasks_emb: dict[str, Any]) -> str:
    """Map internal ``http|local`` to snapshot/API ``openrouter|local``."""

    if str(tasks_emb.get("mode") or "").strip().lower() == "local":
        return "local"
    return "openrouter"


__all__ = [
    "LLM_TASK_ROLES",
    "_LEGACY_FLAT_KEYS",
    "apply_tasks_to_llm_dict",
    "embeddings_public_mode",
    "get_normalized_llm_tasks",
    "merge_partial_tasks_patch",
    "strip_legacy_llm_task_flat_keys",
]
