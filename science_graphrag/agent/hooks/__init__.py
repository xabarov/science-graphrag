"""Hook layer baseline (Train T3 §10.6): immutable decisions + traceable hook_chain_event rows."""

from __future__ import annotations

from science_graphrag.agent.hooks.contracts import HookDecision, HookPhase, hook_chain_event_dict
from science_graphrag.agent.hooks.post_compact import run_post_compact_hooks
from science_graphrag.agent.hooks.subagent_hooks import (
    emit_subagent_start_hook,
    emit_subagent_stop_hook,
)

__all__ = [
    "HookDecision",
    "HookPhase",
    "emit_subagent_start_hook",
    "emit_subagent_stop_hook",
    "hook_chain_event_dict",
    "run_post_compact_hooks",
]
