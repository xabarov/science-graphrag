"""Canonical benchmark launcher defaults (aligned with ui benchmarkLauncherConfig.js)."""

from __future__ import annotations

import re
from typing import Any, Final
from urllib.parse import urlparse

BENCHMARK_FAMILIES: Final[tuple[str, ...]] = ("layer1", "layer2", "graph")

_LAYER1_GOLD: Final[tuple[str, ...]] = ("curated_gold", "teacher_gold")
_LAYER1_THRESHOLD: Final[tuple[str, ...]] = ("from_gold", "student_mistral")


def default_benchmark_family_prefs(family: str) -> dict[str, Any]:
    """Return built-in defaults for one benchmark family (matches UI launcher)."""

    fam = (family or "layer1").strip().lower()
    if fam == "layer2":
        return {
            "model_profile": "env_default",
            "custom_model_id": "",
            "gold_source": "semantic_gold",
            "threshold_profile": "from_gold",
            "base_url_override": "",
            "api_key_env_name": "",
        }
    if fam == "graph":
        return {
            "model_profile": "env_default",
            "custom_model_id": "",
            "gold_source": "curated_gold",
            "threshold_profile": "from_gold",
            "base_url_override": "",
            "api_key_env_name": "",
        }
    return {
        "model_profile": "env_default",
        "custom_model_id": "",
        "gold_source": "curated_gold",
        "threshold_profile": "from_gold",
        "base_url_override": "",
        "api_key_env_name": "",
    }


def _clamp_str(value: Any, *, max_len: int) -> str:
    """Normalize optional string fields from JSON / API."""

    if value is None:
        return ""
    text = str(value).strip()
    if len(text) > max_len:
        return text[:max_len]
    return text


def normalize_benchmark_family_key(family: str) -> str:
    """Return a supported benchmark API family id or fall back to layer1."""

    fam = (family or "").strip().lower()
    return fam if fam in BENCHMARK_FAMILIES else "layer1"


def merge_persisted_benchmark_family(
    family: str, persisted: dict[str, Any] | None
) -> dict[str, Any]:
    """Merge persisted JSON slice with code defaults; return six canonical launcher fields."""
    defaults = default_benchmark_family_prefs(family)
    src = dict(persisted or {})
    gold = _clamp_str(src.get("gold_source"), max_len=64) or defaults["gold_source"]
    threshold = (
        _clamp_str(src.get("threshold_profile"), max_len=64) or defaults["threshold_profile"]
    )
    if family == "layer2":
        gold = "semantic_gold"
        threshold = "from_gold"
    out = {
        "model_profile": _clamp_str(src.get("model_profile"), max_len=256)
        or defaults["model_profile"],
        "custom_model_id": _clamp_str(src.get("custom_model_id"), max_len=256),
        "gold_source": gold,
        "threshold_profile": threshold,
        "base_url_override": _clamp_str(src.get("base_url_override"), max_len=512),
        "api_key_env_name": _clamp_str(src.get("api_key_env_name"), max_len=256),
    }
    if family == "layer1":
        if out["gold_source"] not in _LAYER1_GOLD:
            out["gold_source"] = defaults["gold_source"]
        if out["threshold_profile"] not in _LAYER1_THRESHOLD:
            out["threshold_profile"] = defaults["threshold_profile"]
    elif family == "graph":
        if out["gold_source"] not in _LAYER1_GOLD:
            out["gold_source"] = defaults["gold_source"]
        if out["threshold_profile"] != "from_gold":
            out["threshold_profile"] = "from_gold"
    return out


def validate_merged_benchmark_family_prefs(family: str, merged: dict[str, Any]) -> None:
    """Raise ValueError if effective prefs for a family are invalid."""
    fam = normalize_benchmark_family_key(family)
    mp = (merged.get("model_profile") or "").strip()
    if not mp:
        raise ValueError("model_profile must be non-empty")
    base_url = (merged.get("base_url_override") or "").strip()
    if base_url:
        parsed = urlparse(base_url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("base_url_override must be a valid http(s) URL")
    env_name = (merged.get("api_key_env_name") or "").strip()
    if env_name:
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", env_name):
            raise ValueError("api_key_env_name must look like an environment variable name")
    if mp == "custom" and not (merged.get("custom_model_id") or "").strip():
        raise ValueError("custom_model_id is required when model_profile is custom")
    # Re-validate gold/threshold for layer1 after merge
    gold = merged.get("gold_source")
    thr = merged.get("threshold_profile")
    if fam == "layer1":
        if gold not in _LAYER1_GOLD:
            raise ValueError("gold_source not supported for layer1")
        if thr not in _LAYER1_THRESHOLD:
            raise ValueError("threshold_profile not supported for layer1")
    elif fam == "graph":
        if gold not in _LAYER1_GOLD:
            raise ValueError("gold_source not supported for graph")
        if thr != "from_gold":
            raise ValueError("threshold_profile not supported for graph")


def build_benchmark_ui_snapshot(benchmark_cfg: dict[str, Any] | None) -> dict[str, Any]:
    """Shape returned in GET /v1/settings snapshot."""
    raw_cfg = dict(benchmark_cfg or {})
    meta = dict(raw_cfg.get("_meta") or {})
    by_persisted: dict[str, Any] = dict(raw_cfg.get("by_family") or {})
    by_effective: dict[str, Any] = {}
    for fam in BENCHMARK_FAMILIES:
        persisted_slice = dict(by_persisted.get(fam) or {})
        merged = merge_persisted_benchmark_family(fam, persisted_slice)
        by_effective[fam] = merged
    has_saved = bool(meta.get("last_updated_at"))
    return {
        "by_family": by_effective,
        "status": {
            "last_updated_at": meta.get("last_updated_at"),
            "last_updated_by": meta.get("last_updated_by"),
            "has_saved_defaults": has_saved,
        },
    }
