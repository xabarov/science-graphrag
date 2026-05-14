"""SSE stream lifecycle for Agent API v2 (graph streaming + shortcut paths).

Orchestration delegates to ``stream_phase_*`` modules and
``stream_lifecycle_graph_stream``; product-step constants and helpers are
re-exported here for backward-compatible imports (e.g. tests).
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from time import perf_counter
from typing import Any

from science_graphrag.agent.context.post_turn import apply_turn_digest_to_thread
from science_graphrag.agent.context.session_store import get_session_for_thread
from science_graphrag.agent.graph.supervisor import build_retrieval_graph
from science_graphrag.agent.runtime import current_otel_trace_id_hex
from science_graphrag.api.agent_v2_modules.stream_lifecycle_graph_stream import (
    stream_agent_events,
)
from science_graphrag.api.agent_v2_modules.stream_phase_agent_notes import emit_agent_note
from science_graphrag.api.agent_v2_modules.stream_phase_finalize import (
    agent_chat_llm_run_metadata,
)
from science_graphrag.api.agent_v2_modules.stream_phase_product_steps import (
    GENERIC_PRODUCT_STEP_TOOLS,
    META_TOOL_NAMES,
    degraded_mode_event_from_warnings,
    product_step_code_for_tool,
    product_step_event_for_tool,
)
from science_graphrag.config import Settings
from science_graphrag.stores.registry import StoreRegistry

__all__ = [
    "GENERIC_PRODUCT_STEP_TOOLS",
    "META_TOOL_NAMES",
    "agent_chat_llm_run_metadata",
    "build_retrieval_graph",
    "degraded_mode_event_from_warnings",
    "emit_agent_note",
    "product_step_code_for_tool",
    "product_step_event_for_tool",
    "stream_agent_events",
    "stream_shortcut_answer_events",
]


async def stream_shortcut_answer_events(
    *,
    settings: Settings,
    question: str,
    answer: str,
    max_tool_calls: int,
    workspace_id: str | None,
    thread_id: str | None = None,
    reason: str,
) -> AsyncIterator[dict[str, str]]:
    """Emit a small SSE response for pre-agent clarifications."""
    started = perf_counter()
    yield {
        "data": json.dumps(
            {
                "type": "intent_classified",
                "answer_class": "synthesis",
                "source": reason,
            }
        )
    }
    yield {"data": json.dumps({"type": "product_step", "code": "interpreting_question"})}
    summary_excerpt: str | None = None
    if thread_id:
        new_sum = apply_turn_digest_to_thread(
            thread_id=thread_id,
            raw_user_question=question,
            answer=answer,
            answer_class="synthesis",
            tool_trace=[],
            workspace_id=workspace_id,
        )
        summary_excerpt = (new_sum or "")[:500] if str(new_sum or "").strip() else None
    duration_ms = int((perf_counter() - started) * 1000)
    yield {"data": json.dumps({"type": "product_step", "code": "composing_answer"})}
    yield {"data": json.dumps({"type": "answer_synthesis_started"})}
    yield {"data": json.dumps({"type": "answer_synthesis_finished"})}
    yield {
        "data": json.dumps(
            {
                "type": "final_answer",
                "answer": answer,
                "citations": [],
                "tool_trace": [],
                "duration_ms": duration_ms,
                "phoenix_trace_id": current_otel_trace_id_hex(),
                "thread_id": thread_id,
                "session_summary_excerpt": summary_excerpt,
                "run_metadata": {
                    "agent_runtime": settings.agent_runtime,
                    "agent_max_tool_calls": max_tool_calls,
                    **agent_chat_llm_run_metadata(settings),
                    "shortcut": reason,
                },
                "answer_class": "synthesis",
                "evidence_summary": "clarification requested before retrieval",
                "warnings": [],
                "inventory": None,
                "relation_trace": None,
                "quote_candidates": None,
                "idea_suggestions": None,
                "bibliography": None,
            }
        )
    }
