"""Mutable state for Agent v2 SSE stream lifecycle (chunk loop + finalize inputs)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from science_graphrag.agent.subagents.runtime import RoutingSubagentLegLedger, SubagentRuntime
from science_graphrag.config import Settings


@dataclass
class StreamAgentLifecycleState:
    """Per-request mutable counters updated while consuming graph stream chunks."""

    step: int = 0
    final_answer: str = ""
    citations: list[dict[str, Any]] = field(default_factory=list)
    seen_messages: set[int] = field(default_factory=set)
    latest_full_state: dict[str, Any] | None = None
    salvaged_after_deadline: bool = False
    salvaged_after_recursion_limit: bool = False
    recursion_limit_value: int = 0
    prev_route_len: int = 0
    prev_debug_len: int = 0
    active_subagent_id: str | None = None
    seen_task_notification_markers: set[int] = field(default_factory=set)
    seen_claim_verification_markers: set[int] = field(default_factory=set)
    seen_corpus_explore_markers: set[int] = field(default_factory=set)
    seen_research_plan_markers: set[int] = field(default_factory=set)
    seen_spawned_terminal_rows: set[tuple[str, str, str]] = field(default_factory=set)
    last_progress_label_emit_fp: str | None = None
    last_progress_label_mono: float = 0.0
    note_counter: dict[str, int] = field(default_factory=lambda: {"emitted": 0})
    seen_first_tool_result_per_specialist: set[str] = field(default_factory=set)


@dataclass
class StreamLifecycleRequestContext:
    """Stable references for one ``stream_agent_events`` invocation."""

    settings: Settings
    question: str
    workspace_id: str | None
    max_tool_calls: int
    answer_class_hint: str | None
    thread_id: str | None
    history_digest_invalid: bool
    run_kind: str | None
    graph_id: str | None
    parent_turn_id_str: str
    routing_subagent_ledger: RoutingSubagentLegLedger
    spawn_subagent_runtime: SubagentRuntime
    hook_chain_events: list[dict[str, Any]]
    prompt_memory_audit_initial: dict[str, Any] | None
    post_compact_paper_sources_restored_initial: int | None
    request_turn_warnings: list[str] = field(default_factory=list)
    request_run_metadata_fragment: dict[str, Any] = field(default_factory=dict)


__all__ = ["StreamAgentLifecycleState", "StreamLifecycleRequestContext"]
