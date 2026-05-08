"""Strict-deferred tool activation filter and shortlist telemetry (Wave A seam)."""

from __future__ import annotations

import functools
from dataclasses import dataclass
from typing import Any

from langchain_core.tools import BaseTool

from science_graphrag.agent.tool_manifest import ToolManifestEntry, manifest_by_name
from science_graphrag.config import Settings


@functools.lru_cache(maxsize=1)
def _manifest_map() -> dict[str, ToolManifestEntry]:
    """Cached immutable manifest map for strict-deferred checks."""
    return manifest_by_name()


def strict_deferred_requires_discovery(name: str) -> bool:
    meta = _manifest_map().get(name)
    return bool(meta and meta.strict_deferred_requires_discovery)


def apply_strict_deferred_activation_filter(
    picked: list[BaseTool],
    *,
    rules_names: set[str],
    message_merged: set[str],
    carry_merged: set[str],
    retrieval_core_exempt: frozenset[str],
) -> tuple[list[BaseTool], list[str]]:
    """Drop strict-deferred tools that lack a discovery/rule/core baseline path."""
    allowed = rules_names | message_merged | carry_merged | retrieval_core_exempt
    removed: list[str] = []
    kept: list[BaseTool] = []
    for t in picked:
        nm = getattr(t, "name", "") or ""
        if strict_deferred_requires_discovery(nm) and nm not in allowed:
            removed.append(nm)
            continue
        kept.append(t)
    return kept, removed


@dataclass(frozen=True, slots=True)
class RulesShortlistMetaCtx:
    """Bundled knobs for ``tool_search_result`` metadata (rules path)."""

    settings: Settings
    top_score: float
    score_band: float
    specialist: str
    for_single_agent: bool
    carryover_merged: list[str]
    carryover_names: list[str]
    message_discovery_tools: list[str]
    message_discovery_merged: list[str]
    rules_matched_tools: list[str]
    skipped_optional_baseline: list[str]
    strict_removed_tools: list[str]
    activation_policy: str


def extend_rules_meta_strict_telemetry(
    meta_out: dict[str, Any],
    ctx: RulesShortlistMetaCtx,
    names: list[str],
) -> None:
    """Append Train T1 strict-deferred diagnostics and activation counters."""
    meta_out["activation_policy"] = ctx.activation_policy
    deferred_candidates = [n for n in names if strict_deferred_requires_discovery(n)]
    if deferred_candidates:
        meta_out["deferred_strict_candidates"] = deferred_candidates
    msg_set = set(ctx.message_discovery_merged)
    carry_set = set(ctx.carryover_merged)
    rules_set = set(ctx.rules_matched_tools)
    strict_in_picked = [n for n in names if strict_deferred_requires_discovery(n)]
    via_discovery = [
        n for n in strict_in_picked if (n in msg_set or n in carry_set) and n not in rules_set
    ]
    meta_out["deferred_strict_in_shortlist_count"] = len(strict_in_picked)
    meta_out["deferred_activated_via_message_or_carryover_count"] = len(via_discovery)
    miss = len(ctx.skipped_optional_baseline) + len(ctx.strict_removed_tools)
    meta_out["tool_search_miss_due_to_no_discovery"] = int(miss)
    if strict_in_picked:
        meta_out["deferred_tool_activation_rate"] = round(
            len(via_discovery) / max(1, len(strict_in_picked)), 4
        )
    else:
        meta_out["deferred_tool_activation_rate"] = None


__all__ = [
    "RulesShortlistMetaCtx",
    "apply_strict_deferred_activation_filter",
    "extend_rules_meta_strict_telemetry",
    "strict_deferred_requires_discovery",
]
