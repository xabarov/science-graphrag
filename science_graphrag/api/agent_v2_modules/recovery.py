"""Recovery helpers for agent v2 stream lifecycle failures."""

from __future__ import annotations

import json
from typing import Any

from science_graphrag.agent.chat_envelope import collect_typed_payloads
from science_graphrag.agent.citation_enrichment import hydrate_citations_for_ui
from science_graphrag.agent.runtime import resolve_langgraph_answer_with_salvage
from science_graphrag.api.deps import StoreRegistry


def salvage_answer_from_state(
    *,
    latest_full_state: dict[str, Any] | None,
    stores: StoreRegistry,
) -> tuple[bool, str, list[dict[str, Any]]]:
    """Try to salvage final answer + hydrated citations from latest state."""
    if latest_full_state is None:
        return False, "", []
    state_answer, resolved_cites, _g, _q, _d = resolve_langgraph_answer_with_salvage(latest_full_state)
    if not (state_answer or "").strip():
        return False, "", []
    typed = collect_typed_payloads(latest_full_state)
    inventory = typed.get("inventory")
    specialist_results = latest_full_state.get("specialist_results")
    citations = hydrate_citations_for_ui(
        list(resolved_cites),
        quote_candidates=list(typed.get("quote_candidates") or []),
        chunk_store=stores.qdrant_chunks,
        inventory=inventory if isinstance(inventory, dict) else None,
        messages=list(latest_full_state.get("messages") or []),
        specialist_results=specialist_results if isinstance(specialist_results, dict) else None,
    )
    return True, str(state_answer).strip(), citations


def sse_error_event(payload: dict[str, Any]) -> dict[str, str]:
    """Serialize an SSE error event payload."""
    return {"data": json.dumps({"type": "error", **payload})}


def sse_warning_event(payload: dict[str, Any]) -> dict[str, str]:
    """Serialize an SSE warning event payload."""
    return {"data": json.dumps({"type": "warning", **payload})}
