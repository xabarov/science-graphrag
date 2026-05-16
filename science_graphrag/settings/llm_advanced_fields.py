"""Persisted LLM runtime controls (Phase 3): field names align with ``Settings`` attributes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from annotated_types import Ge, Le

if TYPE_CHECKING:
    from science_graphrag.config import Settings


def _settings_model():
    """Late import: ``config`` imports ``SettingsService`` which imports this module."""

    from science_graphrag.config import Settings  # pylint: disable=import-outside-toplevel

    return Settings


# Persisted under runtime JSON ``llm`` with the same keys as ``Settings`` (flat).
LLM_ADVANCED_RUNTIME_KEYS: tuple[str, ...] = (
    "llm_concurrency_default",
    "llm_concurrency_translation",
    "llm_concurrency_extraction_references",
    "llm_concurrency_claims",
    "llm_concurrency_summary",
    "llm_concurrency_semantic",
    "llm_concurrency_dedup",
    "llm_concurrency_agent_chat",
    "llm_concurrency_agent_classifier",
    "llm_concurrency_query_answer",
    "extraction_llm_references_max_concurrency",
    "agent_step_timeout_seconds",
    "agent_turn_policy_classifier_timeout_seconds",
    "agent_turn_policy_llm_enabled",
    "agent_runtime",
    "agent_max_tool_calls",
    "work_dedup_llm_timeout_s",
    "author_dedup_llm_timeout_s",
    "agent_chat_max_retries",
    "agent_classifier_max_retries",
    "agent_graph_invoke_max_workers",
    "agent_min_llm_hop_reserve_seconds",
    "llm_distributed_quota_enabled",
    "llm_distributed_quota_key_prefix",
    "llm_distributed_quota_acquire_timeout_seconds",
    "llm_distributed_quota_lease_seconds",
)

AGENT_RUNTIME_ALLOWED: frozenset[str] = frozenset(
    ("langgraph_research_v1", "langgraph_supervisor_v1", "langgraph_supervisor_v3", "retrieval_v1")
)

# UI / OpenAPI grouping (``SettingsSchemaResponse``).
_ADVANCED_FIELD_GROUPS: dict[str, str] = {
    "llm_concurrency_default": "llm_concurrency",
    "llm_concurrency_translation": "llm_concurrency",
    "llm_concurrency_extraction_references": "llm_concurrency",
    "llm_concurrency_claims": "llm_concurrency",
    "llm_concurrency_summary": "llm_concurrency",
    "llm_concurrency_semantic": "llm_concurrency",
    "llm_concurrency_dedup": "llm_concurrency",
    "llm_concurrency_agent_chat": "llm_concurrency",
    "llm_concurrency_agent_classifier": "llm_concurrency",
    "llm_concurrency_query_answer": "llm_concurrency",
    "extraction_llm_references_max_concurrency": "llm_concurrency",
    "agent_step_timeout_seconds": "llm_deadlines",
    "agent_turn_policy_classifier_timeout_seconds": "llm_deadlines",
    "work_dedup_llm_timeout_s": "llm_deadlines",
    "author_dedup_llm_timeout_s": "llm_deadlines",
    "agent_chat_max_retries": "llm_agent_runtime",
    "agent_classifier_max_retries": "llm_agent_runtime",
    "agent_graph_invoke_max_workers": "llm_agent_runtime",
    "agent_min_llm_hop_reserve_seconds": "llm_deadlines",
    "agent_runtime": "llm_agent_runtime",
    "agent_max_tool_calls": "llm_agent_runtime",
    "agent_turn_policy_llm_enabled": "llm_agent_runtime",
    "llm_distributed_quota_enabled": "llm_distributed_quota",
    "llm_distributed_quota_key_prefix": "llm_distributed_quota",
    "llm_distributed_quota_acquire_timeout_seconds": "llm_distributed_quota",
    "llm_distributed_quota_lease_seconds": "llm_distributed_quota",
}

_RESERVED_LLM_JSON_KEYS: frozenset[str] = frozenset(
    (
        "base_url",
        "model",
        "chat_model",
        "chat_base_url",
        "vl_model",
        "vl_base_url",
        "embeddings_mode",
        "embeddings_model",
        "temperature",
        "timeout_seconds",
        "enabled",
        "_meta",
        "tasks",
    )
)


def _numeric_bounds(field_name: str) -> tuple[float, float]:
    lo, hi = float("-inf"), float("inf")
    field = _settings_model().model_fields[field_name]  # pylint: disable=unsubscriptable-object
    for meta in field.metadata:
        if isinstance(meta, Ge):
            lo = float(meta.ge)
        elif isinstance(meta, Le):
            hi = float(meta.le)
    return lo, hi


def recommended_advanced_values() -> dict[str, Any]:
    """Defaults from ``Settings`` field definitions (single source for UI reset)."""

    out: dict[str, Any] = {}
    sm = _settings_model()
    for key in LLM_ADVANCED_RUNTIME_KEYS:
        spec = sm.model_fields[key]  # pylint: disable=unsubscriptable-object
        if spec.default_factory is not None:
            out[key] = spec.default_factory()  # type: ignore[misc]
        else:
            out[key] = spec.default
    return out


def clamp_advanced_field(  # pylint: disable=too-many-return-statements
    field_name: str, raw: Any, base: Settings
) -> Any:
    """Clamp or coerce one advanced value to satisfy ``Settings`` constraints."""

    if field_name == "agent_runtime":
        s = str(raw or "").strip()
        if s not in AGENT_RUNTIME_ALLOWED:
            return str(getattr(base, field_name))
        return s
    if field_name == "agent_turn_policy_llm_enabled":
        if isinstance(raw, str):
            return raw.strip().lower() in ("1", "true", "yes", "on")
        return bool(raw)
    if field_name in (
        "llm_concurrency_default",
        "llm_concurrency_translation",
        "llm_concurrency_extraction_references",
        "llm_concurrency_claims",
        "llm_concurrency_summary",
        "llm_concurrency_semantic",
        "llm_concurrency_dedup",
        "llm_concurrency_agent_chat",
        "llm_concurrency_agent_classifier",
        "llm_concurrency_query_answer",
        "extraction_llm_references_max_concurrency",
        "agent_max_tool_calls",
        "agent_chat_max_retries",
        "agent_classifier_max_retries",
        "agent_graph_invoke_max_workers",
    ):
        lo, hi = _numeric_bounds(field_name)
        try:
            v = int(raw)
        except (TypeError, ValueError):
            v = int(getattr(base, field_name))
        return int(max(lo, min(hi, v)))
    if field_name in (
        "agent_step_timeout_seconds",
        "agent_turn_policy_classifier_timeout_seconds",
        "work_dedup_llm_timeout_s",
        "author_dedup_llm_timeout_s",
        "agent_min_llm_hop_reserve_seconds",
    ):
        lo, hi = _numeric_bounds(field_name)
        try:
            v = float(raw)
        except (TypeError, ValueError):
            v = float(getattr(base, field_name))
        return float(max(lo, min(hi, v)))
    if field_name == "llm_distributed_quota_enabled":
        if isinstance(raw, str):
            return raw.strip().lower() in ("1", "true", "yes", "on")
        return bool(raw)
    if field_name == "llm_distributed_quota_key_prefix":
        s = str(raw or "").strip()
        if not s:
            return str(getattr(base, field_name))
        return s[:200]
    if field_name == "llm_distributed_quota_acquire_timeout_seconds":
        lo, hi = _numeric_bounds(field_name)
        try:
            v = float(raw)
        except (TypeError, ValueError):
            v = float(getattr(base, field_name))
        return float(max(lo, min(hi, v)))
    if field_name == "llm_distributed_quota_lease_seconds":
        lo, hi = _numeric_bounds(field_name)
        try:
            v = int(raw)
        except (TypeError, ValueError):
            v = int(getattr(base, field_name))
        return int(max(lo, min(hi, v)))
    return getattr(base, field_name)


def advanced_effective_map(llm: dict[str, Any], base: Settings) -> dict[str, Any]:
    """Resolved advanced values (persisted override or env/base)."""

    out: dict[str, Any] = {}
    for key in LLM_ADVANCED_RUNTIME_KEYS:
        if key in llm and key not in _RESERVED_LLM_JSON_KEYS and llm[key] is not None:
            out[key] = clamp_advanced_field(key, llm[key], base)
        else:
            out[key] = getattr(base, key)
    return out


def merge_llm_advanced_into_overrides(
    non_secret_overrides: dict[str, Any],
    *,
    llm: dict[str, Any],
    base: Settings,
) -> None:
    """Mutates ``non_secret_overrides`` with clamped effective advanced fields."""

    eff = advanced_effective_map(llm, base)
    for key, val in eff.items():
        non_secret_overrides[key] = val


def advanced_schema_fields() -> list[dict[str, Any]]:
    """Field descriptors for ``SettingsService.get_schema`` (version 5+)."""

    out: list[dict[str, Any]] = []
    sm = _settings_model()
    for key in LLM_ADVANCED_RUNTIME_KEYS:
        spec = sm.model_fields[key]  # pylint: disable=unsubscriptable-object
        lo, hi = _numeric_bounds(key)
        group = _ADVANCED_FIELD_GROUPS.get(key, "llm_advanced")
        entry: dict[str, Any] = {
            "id": key,
            "required": False,
            "group": group,
            "description": (spec.description or "").strip(),
        }
        if key in ("agent_turn_policy_llm_enabled", "llm_distributed_quota_enabled"):
            entry["type"] = "boolean"
        elif key == "agent_runtime":
            entry["type"] = "string"
            entry["enum"] = sorted(AGENT_RUNTIME_ALLOWED)
        elif key == "llm_distributed_quota_key_prefix":
            entry["type"] = "string"
            entry["minLength"] = 1
            entry["maxLength"] = 200
        elif key in (
            "agent_step_timeout_seconds",
            "agent_turn_policy_classifier_timeout_seconds",
            "work_dedup_llm_timeout_s",
            "author_dedup_llm_timeout_s",
            "agent_min_llm_hop_reserve_seconds",
            "llm_distributed_quota_acquire_timeout_seconds",
        ):
            entry["type"] = "number"
            if lo > float("-inf"):
                entry["min"] = float(lo)
            if hi < float("inf"):
                entry["max"] = float(hi)
        elif key == "llm_distributed_quota_lease_seconds":
            entry["type"] = "integer"
            if lo > float("-inf"):
                entry["min"] = int(lo)
            if hi < float("inf"):
                entry["max"] = int(hi)
        else:
            entry["type"] = "integer"
            if lo > float("-inf"):
                entry["min"] = int(lo)
            if hi < float("inf"):
                entry["max"] = int(hi)
        out.append(entry)
    return out


def validate_merged_runtime_settings(settings: Any) -> None:
    """Cross-field checks for operator-facing LLM runtime (Phase 3 UI / API)."""

    step = float(settings.agent_step_timeout_seconds)
    classifier = float(settings.agent_turn_policy_classifier_timeout_seconds)
    transport = float(settings.extraction_llm_timeout_seconds)
    if step < classifier:
        raise ValueError(
            "agent_step_timeout_seconds must be >= agent_turn_policy_classifier_timeout_seconds"
        )
    if classifier > transport:
        raise ValueError(
            "agent_turn_policy_classifier_timeout_seconds must be <= extraction_llm_timeout_seconds"
        )
    if bool(settings.llm_distributed_quota_enabled):
        prefix = str(settings.llm_distributed_quota_key_prefix or "").strip()
        if not prefix:
            raise ValueError(
                "llm_distributed_quota_key_prefix must be non-empty when "
                "distributed quota is enabled"
            )
