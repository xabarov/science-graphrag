"""Canonical type sets for debug/SSE streaming (single source, avoids duplicate-code drift)."""

from __future__ import annotations

# Tool-result ``sse_hint["type"]`` values that may be forwarded as streamable client hints.
TOOL_SSE_HINT_STREAMABLE_TYPES: frozenset[str] = frozenset(
    {
        "web_fetched",
        "doi_resolved",
        "mcp_audit",
        "lsp_audit",
        "runtime_monitor",
        "research_plan_updated",
        "user_question_asked",
        "brief_recorded",
    }
)

# ``debug_events`` ``type`` values eligible for SSE mirroring (see stream_lifecycle).
STREAMABLE_DEBUG_EVENT_TYPES: frozenset[str] = TOOL_SSE_HINT_STREAMABLE_TYPES | frozenset(
    {
        "tool_search_result",
        "intent_classified",
        "tool_execution",
        "tool_permissions",
        "budget_stop_decision",
        "user_answered",
    }
)
