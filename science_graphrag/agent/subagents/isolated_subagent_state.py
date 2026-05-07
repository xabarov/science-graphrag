"""Short-term memory isolation for forked subagent runs (Train T4 §11.4 B3).

Child runs must not inherit the parent LangGraph message transcript. Carry-back to the
parent is explicit (structured dict + HumanMessage markers), never an implicit merge
of child ``messages`` into the parent state.
"""

from __future__ import annotations

from typing import Any

from science_graphrag.agent.graph.state import build_initial_agent_state
from science_graphrag.config import Settings

# Bump when isolation semantics change (tests may assert on this).
SUBAGENT_MEMORY_ISOLATION_VERSION = "fork_child_v1"


def carry_back_contract_summary() -> str:
    """One-line contract for docstrings and agent prompts."""
    return (
        "Parent transcript is invisible; only explicit carry-back fields and session tools "
        "scoped by thread_id may persist durable state."
    )


def build_isolated_subagent_initial_state(
    *,
    instruction_blob: str,
    workspace_id: str | None,
    thread_id: str | None,
    max_tool_calls: int,
    agent_runtime: str,
    settings: Settings,
    classifier: str,
    short_term_memory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build child ``AgentState`` with empty ``messages`` and isolated scratch memory.

    ``instruction_blob`` is the full self-contained task text (never raw parent history).
    Optional ``short_term_memory`` seeds deterministic per-run scratch (tests); the subgraph
    may append notes without leaking to the parent unless explicitly merged via carry-back.
    """
    child = build_initial_agent_state(
        question=instruction_blob,
        workspace_id=workspace_id,
        max_tool_calls=max_tool_calls,
        agent_runtime=agent_runtime,
        thread_id=thread_id,
        history_digest=None,
        session_summary="",
        answer_class_hint=None,
        client_idle_ms=None,
        settings=settings,
    )
    meta = dict(child.get("metadata") or {})
    meta["subagent_memory_isolation"] = SUBAGENT_MEMORY_ISOLATION_VERSION
    meta["subagent_short_term_memory"] = dict(short_term_memory or {})
    meta["turn_policy"] = {"tool_policy": "allow_tools", "classifier": str(classifier)}
    child["metadata"] = meta
    child["messages"] = []
    return child


__all__ = [
    "SUBAGENT_MEMORY_ISOLATION_VERSION",
    "build_isolated_subagent_initial_state",
    "carry_back_contract_summary",
]
