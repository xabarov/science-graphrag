"""Immutable hook context + decision records (Train T3 §10.6 baseline)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

HookPhase = Literal["post_compact", "subagent_start", "subagent_stop"]


@dataclass(frozen=True, slots=True)
class HookDecision:
    """Outcome of a single hook step (no hidden side effects outside returned payload)."""

    ok: bool
    hook_id: str
    phase: HookPhase
    detail: dict[str, Any] = field(default_factory=dict)


def hook_chain_event_dict(
    *,
    hook_id: str,
    phase: HookPhase,
    ok: bool,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Stable debug_events / run_metadata shape for trace-review-v1."""
    return {
        "type": "hook_chain_event",
        "hook": str(hook_id),
        "phase": str(phase),
        "ok": bool(ok),
        "detail": dict(detail or {}),
    }
