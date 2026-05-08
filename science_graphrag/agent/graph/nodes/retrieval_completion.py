"""Retrieval specialist completion_state annotation (Wave A structural seam)."""

from __future__ import annotations

from typing import Any

from science_graphrag.agent.coordination.question_features import extract_question_features
from science_graphrag.agent.coordination.route_planner import derive_retrieval_completion_state
from science_graphrag.agent.graph.state import AgentState
from science_graphrag.agent.graph.tracing import collect_tool_execution_steps
from science_graphrag.agent.subagents.specialist_results_v3 import annotate_completion_state


def annotate_retrieval_completion_state(
    *,
    sr3: dict[str, Any],
    messages: list[Any],
    question: str,
    state: AgentState,
    new_payloads: list[dict],
    specialist_results: dict[str, Any],
    specialist_name: str,
) -> dict[str, Any]:
    """Attach typed ``completion_state`` for planner post-retrieval handoff.

    Must never raise to callers — failures fall back to implicit v3 inference.
    """
    try:
        tool_counts: dict[str, int] = {}
        for step in collect_tool_execution_steps(messages):
            tname = str(step.get("tool") or "").strip()
            if tname:
                tool_counts[tname] = tool_counts.get(tname, 0) + 1
        features = extract_question_features(
            question=question,
            workspace_id=str(state.get("workspace_id") or "").strip() or None,
        )
        cs = derive_retrieval_completion_state(
            features=features,
            tool_counts=tool_counts,
            has_payloads=bool(new_payloads or specialist_results.get(specialist_name)),
        )
        return annotate_completion_state(sr3, completion_state=str(cs))
    except Exception:  # noqa: BLE001
        return sr3


__all__ = ["annotate_retrieval_completion_state"]
