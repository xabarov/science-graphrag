"""Product-facing SSE progress codes for Agent API v2 (tool mapping + degraded_mode)."""

from __future__ import annotations

from typing import Any

# Meta tools: no product_step headline after tool_call.
META_TOOL_NAMES = frozenset(
    {"session_init", "route_to_specialist", "coordinator_gate", "final_answer"}
)

# Tools that intentionally remain on generic `using_tool` wording.
GENERIC_PRODUCT_STEP_TOOLS = frozenset(
    {"call_mcp_tool", "list_mcp_resources", "fetch_mcp_resource", "mcp_auth"}
)

DEGRADED_MODE_SCHEMA_VERSION = 1

_WARNING_TO_DEGRADED_REASON: tuple[tuple[str, str], ...] = (
    ("answer_salvaged_from_graph_tool", "graph_tool_salvage"),
    ("answer_salvaged_from_quote_candidates", "quote_candidate_salvage"),
    ("answer_salvaged_from_assistant_draft", "assistant_draft_salvage"),
    ("agent_turn_deadline_exceeded", "turn_deadline_exceeded"),
    ("partial_after_deadline", "partial_after_deadline"),
    ("agent_partial_graph_recursion_limit", "recursion_limit_partial"),
    ("partial_after_recursion_limit", "partial_after_recursion_limit"),
)


def degraded_mode_event_from_warnings(warnings: list[str]) -> dict[str, Any] | None:
    """Build optional SSE ``degraded_mode`` when the turn used a salvage / partial path."""
    wset = {str(x).strip() for x in (warnings or []) if str(x).strip()}
    reasons: list[str] = []
    for war, reason in _WARNING_TO_DEGRADED_REASON:
        if war in wset and reason not in reasons:
            reasons.append(reason)
    if not reasons:
        return None
    return {
        "type": "degraded_mode",
        "schema_version": DEGRADED_MODE_SCHEMA_VERSION,
        "reasons": reasons,
    }


def product_step_code_for_tool(tool_name: str) -> str | None:
    """Map normalized tool name to a short product_step code for SSE/UI."""
    mapping: dict[str, str] = {
        "idea_search": "searching_literature",
        "idea_browse": "browsing_ideas",
        "evidence_lookup": "gathering_evidence",
        "workspace_inspect": "summarizing_workspace",
        "workspace_graph_reltypes": "exploring_graph",
        "summarize_workspace": "summarizing_workspace",
        "entity_search": "searching_literature",
        "cypher_query": "exploring_graph",
        "edge_search": "exploring_graph",
        "find_works": "paper_lookup",
        "paper_profile": "paper_metadata",
        "paper_quote_search": "finding_quotes",
        "format_bibliography_gost": "formatting_bibliography",
        "final_answer": "composing_answer",
        "web_search": "searching_literature",
        "web_fetch": "gathering_evidence",
        "arxiv_search": "searching_literature",
        "arxiv_fetch": "gathering_evidence",
        "unpaywall_lookup": "gathering_evidence",
        "doi_resolver": "paper_metadata",
        "lsp_tool": "exploring_graph",
        "runtime_monitor_get": "summarizing_workspace",
        "research_plan_write": "interpreting_question",
        "ask_user_question": "interpreting_question",
        "brief": "composing_answer",
        "enter_worktree": "interpreting_question",
        "exit_worktree": "interpreting_question",
        "enter_plan_mode": "interpreting_question",
        "exit_plan_mode": "interpreting_question",
    }
    return mapping.get(tool_name)


def product_step_event_for_tool(tool_name: str) -> dict[str, Any]:
    """Build a product_step payload with explicit generic fallback semantics."""
    code = product_step_code_for_tool(tool_name)
    if code:
        return {"type": "product_step", "code": code, "tool": tool_name}
    generic_reason = (
        "intentionally_generic_tool"
        if tool_name in GENERIC_PRODUCT_STEP_TOOLS
        else "unmapped_tool_name"
    )
    return {
        "type": "product_step",
        "code": "using_tool",
        "tool": tool_name,
        "generic": True,
        "generic_reason": generic_reason,
    }


DELEGATING_TO_BY_SPECIALIST: dict[str, str] = {
    "retrieval_agent": "delegating_to_retrieval_agent",
    "graph_agent": "delegating_to_graph_agent",
    "writer_agent": "delegating_to_writer_agent",
    "single_agent_react": "delegating_to_single_agent_react",
    "supervisor": "delegating_to_supervisor",
}


def delegating_product_step_code(specialist_id: str) -> str:
    """Return a product_step code describing handoff to ``specialist_id``."""
    code = DELEGATING_TO_BY_SPECIALIST.get(str(specialist_id or "").strip())
    return code or "delegating_to_specialist"


__all__ = [
    "DELEGATING_TO_BY_SPECIALIST",
    "DEGRADED_MODE_SCHEMA_VERSION",
    "GENERIC_PRODUCT_STEP_TOOLS",
    "META_TOOL_NAMES",
    "delegating_product_step_code",
    "degraded_mode_event_from_warnings",
    "product_step_code_for_tool",
    "product_step_event_for_tool",
]
