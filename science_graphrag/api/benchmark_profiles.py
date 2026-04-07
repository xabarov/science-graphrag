"""Benchmark model profiles and execution config helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from science_graphrag.config import Settings, get_settings


@dataclass(frozen=True)
class BenchmarkModelProfile:
    """Declarative model preset surfaced in the benchmark UI."""

    profile_id: str
    label: str
    role: str
    family_support: tuple[str, ...]
    model_id: str | None = None
    default_gold_source: str | None = None
    default_threshold_profile: str | None = None
    supports_custom_model_id: bool = False


MODEL_PROFILES: tuple[BenchmarkModelProfile, ...] = (
    BenchmarkModelProfile(
        profile_id="env_default",
        label="Environment default",
        role="generic",
        family_support=("layer1", "layer2"),
    ),
    BenchmarkModelProfile(
        profile_id="student_mistral_small_32",
        label="Student Mistral Small 3.2",
        role="student",
        family_support=("layer1", "layer2"),
        model_id="mistralai/mistral-small-3.2-24b-instruct",
        default_gold_source="teacher_gold",
        default_threshold_profile="student_mistral",
    ),
    BenchmarkModelProfile(
        profile_id="teacher_deepseek_v32",
        label="Teacher DeepSeek V3.2",
        role="teacher",
        family_support=("layer1", "layer2"),
        model_id="deepseek/deepseek-v3.2",
        default_gold_source="curated_gold",
    ),
    BenchmarkModelProfile(
        profile_id="custom",
        label="Custom model id",
        role="generic",
        family_support=("layer1", "layer2"),
        supports_custom_model_id=True,
    ),
)


def list_model_profiles(*, settings: Settings | None = None) -> list[dict[str, Any]]:
    """Return UI-friendly model profile payloads."""
    base_settings = settings or get_settings()
    items: list[dict[str, Any]] = []
    for profile in MODEL_PROFILES:
        resolved_model_id = _resolve_profile_model_id(profile, base_settings)
        items.append(
            {
                "profile_id": profile.profile_id,
                "label": profile.label,
                "role": profile.role,
                "family_support": list(profile.family_support),
                "model_id": resolved_model_id,
                "default_gold_source": profile.default_gold_source,
                "default_threshold_profile": profile.default_threshold_profile,
                "supports_custom_model_id": profile.supports_custom_model_id,
            }
        )
    return items


def get_model_profile(profile_id: str | None) -> BenchmarkModelProfile | None:
    """Resolve a model profile by id."""
    if not profile_id:
        return None
    normalized = profile_id.strip()
    for profile in MODEL_PROFILES:
        if profile.profile_id == normalized:
            return profile
    return None


def prepare_run_config(
    *,
    benchmark_family: str,
    requested_config: dict[str, Any] | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Resolve requested benchmark config into an execution-ready snapshot."""
    base_settings = settings or get_settings()
    family = (benchmark_family or "layer1").strip().lower()
    requested = dict(requested_config or {})
    profile_id = (requested.get("model_profile") or "env_default").strip()
    profile = get_model_profile(profile_id)
    if profile is None:
        raise ValueError(f"unknown_model_profile:{profile_id}")
    if family not in profile.family_support:
        raise ValueError(f"model_profile_not_supported_for_family:{profile_id}:{family}")

    explicit_model_id = _strip_or_none(requested.get("model_id"))
    if profile.profile_id == "custom" and not explicit_model_id:
        raise ValueError("custom_model_id_required")
    resolved_model_id = explicit_model_id or _resolve_profile_model_id(profile, base_settings)

    gold_source = _resolve_gold_source(profile, family, requested.get("gold_source"))
    threshold_profile = _resolve_threshold_profile(profile, requested.get("threshold_profile"))
    resolved_base_url = _resolve_base_url(profile, base_settings, requested.get("base_url_override"))
    resolved_api_key, api_key_source = _resolve_api_key(
        profile,
        base_settings,
        requested.get("api_key_env_name"),
    )

    if family == "layer2" and gold_source not in ("semantic_gold", "curated_gold"):
        raise ValueError(f"gold_source_not_supported_for_family:{gold_source}:{family}")

    return {
        "model_profile": profile.profile_id,
        "profile_label": profile.label,
        "model_role": profile.role,
        "requested_model_id": explicit_model_id,
        "resolved_model_id": resolved_model_id,
        "gold_source": gold_source,
        "threshold_profile": threshold_profile,
        "base_url_override": _strip_or_none(requested.get("base_url_override")),
        "resolved_base_url": resolved_base_url,
        "api_key_env_name": _strip_or_none(requested.get("api_key_env_name")),
        "api_key_source": api_key_source,
        "_resolved_api_key": resolved_api_key,
        "effective_settings": {
            "extraction_llm_model": resolved_model_id or base_settings.extraction_llm_model,
            "extraction_llm_base_url": resolved_base_url or base_settings.extraction_llm_base_url,
            "semantic_graph_confidence_threshold": base_settings.semantic_graph_confidence_threshold,
            "extraction_llm_enabled": base_settings.extraction_llm_enabled,
            "semantic_extraction_enabled": base_settings.semantic_extraction_enabled,
        },
        "layer1_gold": _resolve_layer1_gold_config(
            repo_root=Path(__file__).resolve().parents[2],
            gold_source=gold_source,
        )
        if family == "layer1"
        else None,
    }


def build_settings_for_run(
    run_config: dict[str, Any] | None,
    *,
    settings: Settings | None = None,
) -> Settings:
    """Build an immutable settings snapshot for a benchmark run."""
    base_settings = settings or get_settings()
    config = run_config or {}
    update: dict[str, Any] = {}

    model_id = _strip_or_none(config.get("resolved_model_id"))
    if model_id:
        update["extraction_llm_model"] = model_id

    base_url = _strip_or_none(config.get("resolved_base_url"))
    if base_url:
        update["extraction_llm_base_url"] = base_url.rstrip("/")

    api_key = _strip_or_none(config.get("_resolved_api_key"))
    if api_key:
        update["extraction_llm_api_key"] = api_key

    return base_settings.model_copy(update=update)


def public_run_config(run_config: dict[str, Any] | None) -> dict[str, Any]:
    """Strip secrets from run config before exposing it over the API."""
    config = dict(run_config or {})
    config.pop("_resolved_api_key", None)
    return config


def _resolve_layer1_gold_config(*, repo_root: Path, gold_source: str) -> dict[str, Any]:
    if gold_source == "teacher_gold":
        external_root = repo_root / "eval" / "teacher_gold" / "layer1"
        return {
            "external_gold_root": str(external_root.resolve()),
            "gold_filename": "gold_teacher.json",
        }
    return {
        "external_gold_root": None,
        "gold_filename": "gold.json",
    }


def _resolve_profile_model_id(profile: BenchmarkModelProfile, settings: Settings) -> str | None:
    if profile.profile_id == "env_default":
        return settings.extraction_llm_model
    if profile.profile_id == "teacher_deepseek_v32":
        return settings.benchmark_teacher_llm_model or profile.model_id
    return profile.model_id or settings.extraction_llm_model


def _resolve_gold_source(
    profile: BenchmarkModelProfile,
    family: str,
    gold_source: Any,
) -> str:
    requested = _strip_or_none(gold_source)
    if requested:
        return requested
    if family == "layer2":
        return "semantic_gold"
    return profile.default_gold_source or "curated_gold"


def _resolve_threshold_profile(profile: BenchmarkModelProfile, threshold_profile: Any) -> str | None:
    requested = _strip_or_none(threshold_profile)
    if requested in ("none", "from_gold"):
        return None
    if requested:
        return requested
    return profile.default_threshold_profile


def _resolve_base_url(
    profile: BenchmarkModelProfile,
    settings: Settings,
    requested_override: Any,
) -> str | None:
    override = _strip_or_none(requested_override)
    if override:
        return override.rstrip("/")
    if profile.profile_id == "teacher_deepseek_v32" and settings.benchmark_teacher_llm_base_url:
        return settings.benchmark_teacher_llm_base_url.rstrip("/")
    return settings.extraction_llm_base_url.rstrip("/")


def _resolve_api_key(
    profile: BenchmarkModelProfile,
    settings: Settings,
    api_key_env_name: Any,
) -> tuple[str | None, str]:
    env_name = _strip_or_none(api_key_env_name)
    if env_name:
        value = _strip_or_none(os.getenv(env_name))
        if not value:
            raise ValueError(f"api_key_env_missing:{env_name}")
        return value, env_name
    if profile.profile_id == "teacher_deepseek_v32" and settings.benchmark_teacher_llm_api_key:
        return settings.benchmark_teacher_llm_api_key, "benchmark_teacher_llm_api_key"
    if settings.extraction_llm_api_key:
        return settings.extraction_llm_api_key, "settings.extraction_llm_api_key"
    return None, "none"


def _strip_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
