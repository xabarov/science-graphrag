"""Research chat response envelope (Wave A — CH1)."""

from __future__ import annotations

from typing import Any

from science_graphrag.agent.graph.state import AgentState
from science_graphrag.agent.trace import ToolCallTrace

ANSWER_CLASSES = frozenset(
    {
        "inventory",
        "fact_lookup",
        "grounded_explanation",
        "relation_tracing",
        "quote_extraction",
        "ideation",
        "bibliography_export",
        "synthesis",
    }
)


def _last_user_question(state: AgentState | dict[str, Any]) -> str:
    from langchain_core.messages import HumanMessage

    for msg in reversed(list(state.get("messages") or [])):
        if isinstance(msg, HumanMessage):
            return str(msg.content or "")
    return ""


def heuristic_answer_class(question: str, hint: str | None) -> str:
    if hint and hint in ANSWER_CLASSES:
        return hint
    q = (question or "").lower()
    if any(x in q for x in ("гост", "gost", "bibliograph", "список литературы", "literature list")):
        return "bibliography_export"
    if any(x in q for x in ("цитат", "quote", "passage", "snippet", "где написано")):
        return "quote_extraction"
    if any(
        x in q for x in ("how many", "сколько", "список стат", "papers in", "works in workspace")
    ):
        return "inventory"
    if any(x in q for x in ("связ", "path", "cites", "cypher", "graph", "entity")):
        return "relation_tracing"
    if any(x in q for x in ("who authored", "автор", "authors of")):
        return "fact_lookup"
    return "grounded_explanation"


def _merge_inventory(acc: dict[str, Any], fragment: dict[str, Any]) -> None:
    if not fragment:
        return
    for key, val in fragment.items():
        if val is None:
            continue
        if key not in acc:
            acc[key] = val
            continue
        if isinstance(acc[key], list) and isinstance(val, list):
            acc[key] = acc[key] + val
        elif isinstance(acc[key], dict) and isinstance(val, dict):
            acc[key].update(val)
        else:
            acc[key] = val


def collect_typed_payloads(state: AgentState | dict[str, Any]) -> dict[str, Any]:
    """Scan specialist tool JSON payloads for typed blocks."""
    inventory: dict[str, Any] = {}
    quote_candidates: list[dict[str, Any]] = []
    bibliography: dict[str, Any] | None = None
    specialist_results = state.get("specialist_results") or {}
    for _spec, payloads in specialist_results.items():
        for payload in payloads or []:
            if not isinstance(payload, dict):
                continue
            inv = payload.get("inventory")
            if isinstance(inv, dict):
                _merge_inventory(inventory, inv)
            qc = payload.get("quote_candidates")
            if isinstance(qc, list):
                quote_candidates.extend(qc)
            bib = payload.get("bibliography")
            if isinstance(bib, dict) and bib.get("entries"):
                bibliography = bib
    out: dict[str, Any] = {}
    if inventory:
        out["inventory"] = inventory
    if quote_candidates:
        out["quote_candidates"] = quote_candidates[:50]
    if bibliography:
        out["bibliography"] = bibliography
    return out


def infer_class_from_trace(tool_names: set[str]) -> str | None:
    if "format_bibliography_gost" in tool_names:
        return "bibliography_export"
    if "paper_quote_search" in tool_names:
        return "quote_extraction"
    if {"workspace_overview", "workspace_list_papers", "paper_counts"} & tool_names:
        return "inventory"
    if "paper_authors" in tool_names or "paper_metadata" in tool_names:
        return "fact_lookup"
    if {"entity_search", "edge_search", "cypher_query"} & tool_names:
        return "relation_tracing"
    return None


def build_chat_envelope(
    *,
    state: AgentState | dict[str, Any],
    answer: str,
    citations: list[dict[str, Any]],
    tool_trace: list[ToolCallTrace],
    answer_class_hint: str | None = None,
) -> dict[str, Any]:
    """Build optional envelope fields for API v2."""
    question = _last_user_question(state)
    names = {str(t.get("tool") or "") for t in tool_trace if isinstance(t, dict)}
    names.discard("")
    from_trace = infer_class_from_trace(names)
    answer_class = from_trace or heuristic_answer_class(question, answer_class_hint)
    typed = collect_typed_payloads(state)
    warnings: list[str] = []
    if not (state.get("workspace_id") or "").strip():
        warnings.append("no_workspace")
    evidence_parts: list[str] = []
    if citations:
        evidence_parts.append(f"{len(citations)} citation(s)")
    if tool_trace:
        evidence_parts.append(f"{len(tool_trace)} trace step(s)")
    evidence_summary = ", ".join(evidence_parts) if evidence_parts else None
    out = {
        "answer_class": answer_class,
        "evidence_summary": evidence_summary,
        "warnings": warnings,
    }
    out.update(typed)
    return out
